import asyncio
import json
import logging

from aiogram import Bot
from aiogram.types import InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest

import config
import db
import keyboards
import scheduler

log = logging.getLogger(__name__)


def user_mention(user_id: int, username: str | None) -> str:
    return f"@{username}" if username else f"<a href='tg://user?id={user_id}'>{user_id}</a>"


# ---------------- ВЫДАЧА ЗАДАНИЙ ----------------

async def issue_step1_task(bot: Bot, user_id: int):
    text = await db.random_task_text(1)
    await db.set_task(user_id, config.STATUS_STEP1_TASK, text)
    await bot.send_message(
        user_id,
        "🎬 <b>Шаг 1 из 3</b>\n\n"
        f"В течение <b>5 минут</b> напиши этот текст в ответ на чужой комментарий "
        f"под видео в TikTok, с которого ты перешёл:\n\n"
        f"«<b>{text}</b>»\n\n"
        "Сделай скриншот своего комментария и пришли его сюда 📸",
    )
    scheduler.schedule_once(f"task:{user_id}", config.STEP1_TIMEOUT, handle_task_timeout, bot, user_id, 1)


async def issue_step2_task(bot: Bot, user_id: int):
    text = await db.random_task_text(2)
    await db.set_task(user_id, config.STATUS_STEP2_TASK, text)
    await bot.send_message(
        user_id,
        "🎬 <b>Шаг 2 из 3</b>\n\n"
        f"В течение <b>20 минут</b> напиши этот текст под <b>10 разными видео</b> в TikTok:\n\n"
        f"«<b>{text}</b>»\n\n"
        "Присылай скриншоты сюда по одному — как только наберётся 10, я отправлю их на проверку 📸",
    )
    scheduler.schedule_once(f"task:{user_id}", config.STEP2_TIMEOUT, handle_task_timeout, bot, user_id, 2)


async def issue_sponsors_step(bot: Bot, user_id: int):
    await db.set_status(user_id, config.STATUS_STEP3_SPONSORS)
    sponsors = await db.list_sponsors(active_only=True)
    if not sponsors:
        # Спонсоров нет — пропускаем шаг
        await finish_sponsors_step(bot, user_id, user_id)
        return
    await bot.send_message(
        user_id,
        "📢 <b>Шаг 3 из 3</b>\n\nПодпишись на все каналы ниже, затем нажми «Проверить подписки»:",
        reply_markup=keyboards.sponsors_kb(sponsors),
    )


# ---------------- ПРИЁМ СКРИНШОТОВ ----------------

async def submit_step1_photo(bot: Bot, user_id: int, username: str | None, file_id: str):
    user = await db.get_user(user_id)
    scheduler.cancel_job(f"task:{user_id}")
    await db.set_status(user_id, config.STATUS_STEP1_REVIEW)
    item_id = await db.create_moderation_item(user_id, 1, user["task_text"], [file_id])
    caption = (
        f"🆕 Проверка — шаг 1\n"
        f"Пользователь: {user_mention(user_id, username)}\n"
        f"Требуемый текст:\n«{user['task_text']}»"
    )
    try:
        msg = await bot.send_photo(
            config.MODERATION_GROUP_ID, file_id, caption=caption,
            reply_markup=keyboards.moderation_kb(item_id), parse_mode="HTML",
        )
    except Exception:
        log.exception("Не удалось отправить скриншот модераторам (шаг 1, user %s)", user_id)
        await db.set_moderation_status(item_id, "error", None)
        await revert_to_task(bot, user_id, 1, user["task_text"])
        return
    await db.set_moderation_messages(item_id, [msg.message_id], msg.message_id)
    scheduler.schedule_once(f"mod:{item_id}", config.MODERATION_TIMEOUT, handle_moderation_timeout, bot, item_id)
    await bot.send_message(user_id, "⏳ Скриншот отправлен на проверку модераторам, подожди немного.")


async def revert_to_task(bot: Bot, user_id: int, step: int, task_text: str):
    """Откатывает пользователя обратно к заданию, если отправка модераторам не удалась
    (например, неверный MODERATION_GROUP_ID) — иначе он навсегда застрянет в 'на проверке'."""
    timeout = config.STEP1_TIMEOUT if step == 1 else config.STEP2_TIMEOUT
    await db.set_task(user_id, config.STATUS_STEP1_TASK if step == 1 else config.STATUS_STEP2_TASK, task_text)
    scheduler.schedule_once(f"task:{user_id}", timeout, handle_task_timeout, bot, user_id, step)
    await bot.send_message(
        user_id,
        "⚠️ Не получилось отправить скриншот на проверку — техническая проблема на нашей стороне. "
        "Пришли его ещё раз, пожалуйста.",
    )


_album_tasks: dict[int, asyncio.Task] = {}


def schedule_album_summary(bot: Bot, user_id: int, delay: float = 4.0):
    """Альбом присылает фото несколькими апдейтами подряд — ждём delay сек после
    последнего и, если задание ещё не набрало 10 фото, шлём одно сводное сообщение."""
    old = _album_tasks.get(user_id)
    if old and not old.done():
        old.cancel()
    _album_tasks[user_id] = asyncio.create_task(_album_summary_worker(bot, user_id, delay))


async def _album_summary_worker(bot: Bot, user_id: int, delay: float):
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        return
    _album_tasks.pop(user_id, None)
    user = await db.get_user(user_id)
    if user and user["status"] == config.STATUS_STEP2_TASK:
        count = len(await db.get_task_photos(user_id))
        await bot.send_message(user_id, f"📸 Альбом получен: {count}/{config.STEP2_REQUIRED_SCREENSHOTS}")


async def append_step2_photo(bot: Bot, user_id: int, username: str | None, file_id: str, notify_progress: bool = True):
    user = await db.get_user(user_id)
    if user is None or user["status"] != config.STATUS_STEP2_TASK:
        return  # задание уже сдано/сброшено — лишние фото из альбома игнорируем

    count = await db.append_task_photo(user_id, file_id)
    if count < config.STEP2_REQUIRED_SCREENSHOTS:
        if notify_progress:
            await bot.send_message(user_id, f"📸 Принято {count}/{config.STEP2_REQUIRED_SCREENSHOTS}")
        return

    scheduler.cancel_job(f"task:{user_id}")
    user = await db.get_user(user_id)
    photos = await db.get_task_photos(user_id)
    photos = photos[: config.STEP2_REQUIRED_SCREENSHOTS]
    await db.set_status(user_id, config.STATUS_STEP2_REVIEW)
    item_id = await db.create_moderation_item(user_id, 2, user["task_text"], photos)

    media = [InputMediaPhoto(media=p) for p in photos]
    caption = (
        f"🆕 Проверка — шаг 2 ({len(photos)} скриншотов)\n"
        f"Пользователь: {user_mention(user_id, username)}\n"
        f"Требуемый текст:\n«{user['task_text']}»"
    )
    try:
        sent = await bot.send_media_group(config.MODERATION_GROUP_ID, media)
        control = await bot.send_message(
            config.MODERATION_GROUP_ID, caption,
            reply_markup=keyboards.moderation_kb(item_id), parse_mode="HTML",
        )
    except Exception:
        log.exception("Не удалось отправить скриншоты модераторам (шаг 2, user %s)", user_id)
        await db.set_moderation_status(item_id, "error", None)
        await revert_to_task(bot, user_id, 2, user["task_text"])
        return
    group_ids = [m.message_id for m in sent] + [control.message_id]
    await db.set_moderation_messages(item_id, group_ids, control.message_id)
    scheduler.schedule_once(f"mod:{item_id}", config.MODERATION_TIMEOUT, handle_moderation_timeout, bot, item_id)
    await bot.send_message(user_id, "⏳ Скриншоты отправлены на проверку модераторам, подожди немного.")


# ---------------- РЕШЕНИЕ МОДЕРАЦИИ ----------------

async def process_moderation_decision(bot: Bot, item_id: int, approved: bool, moderator_id: int | None):
    item = await db.get_moderation_item(item_id)
    if item is None or item["status"] != "pending":
        return  # уже обработано (модератор нажал раньше таймера или наоборот)

    scheduler.cancel_job(f"mod:{item_id}")
    await db.set_moderation_status(item_id, "approved" if approved else "rejected", moderator_id)

    group_ids = json.loads(item["group_message_ids"]) if item["group_message_ids"] else []
    for mid in group_ids:
        try:
            await bot.delete_message(config.MODERATION_GROUP_ID, mid)
        except TelegramBadRequest:
            pass
    if item["control_message_id"]:
        try:
            await bot.delete_message(config.MODERATION_GROUP_ID, item["control_message_id"])
        except TelegramBadRequest:
            pass

    user_id = item["user_id"]
    step = item["step"]

    if approved:
        await db.reset_attempts(user_id, step)
        if step == 1:
            await bot.send_message(user_id, "✅ Первое задание принято! Переходим дальше.")
            await issue_step2_task(bot, user_id)
        else:
            await bot.send_message(user_id, "✅ Второе задание принято! Остался последний шаг.")
            await issue_sponsors_step(bot, user_id)
    else:
        attempts = await db.bump_attempts(user_id, step)
        if attempts >= config.MAX_ATTEMPTS:
            await db.lock_user(user_id, config.LOCKOUT_HOURS)
            await bot.send_message(
                user_id,
                f"❌ Задание отклонено. Превышен лимит попыток ({config.MAX_ATTEMPTS}).\n"
                f"Доступ заблокирован на {config.LOCKOUT_HOURS} часов.",
            )
        else:
            left = config.MAX_ATTEMPTS - attempts
            await bot.send_message(
                user_id, f"❌ Задание отклонено. Осталось попыток: {left}. Начнём заново:"
            )
            if step == 1:
                await issue_step1_task(bot, user_id)
            else:
                await issue_step2_task(bot, user_id)


# ---------------- ТАЙМАУТЫ ----------------

async def handle_task_timeout(bot: Bot, user_id: int, step: int):
    user = await db.get_user(user_id)
    if user is None:
        return
    expected = config.STATUS_STEP1_TASK if step == 1 else config.STATUS_STEP2_TASK
    if user["status"] != expected:
        return  # уже сдал или продвинулся дальше
    await bot.send_message(user_id, "⏰ Время вышло! Задание аннулировано, вот новое:")
    if step == 1:
        await issue_step1_task(bot, user_id)
    else:
        await issue_step2_task(bot, user_id)


async def handle_moderation_timeout(bot: Bot, item_id: int):
    await process_moderation_decision(bot, item_id, approved=True, moderator_id=None)


# ---------------- СПОНСОРЫ / РУЛЕТКА ----------------

async def check_subscriptions(bot: Bot, user_id: int) -> list[str]:
    """Возвращает список названий каналов, на которые пользователь НЕ подписан."""
    sponsors = await db.list_sponsors(active_only=True)
    not_subscribed = []
    for s in sponsors:
        try:
            member = await bot.get_chat_member(s["chat_ref"], user_id)
            if member.status not in ("member", "administrator", "creator"):
                not_subscribed.append(s["name"])
        except TelegramBadRequest:
            not_subscribed.append(s["name"])
    return not_subscribed


async def finish_sponsors_step(bot: Bot, user_id: int, chat_id: int):
    await db.set_status(user_id, config.STATUS_DONE)
    await bot.send_message(chat_id, "🎉 Все проверки пройдены! Крутим рулетку удачи…")
    await run_roulette(bot, user_id, chat_id)


async def run_roulette(bot: Bot, user_id: int, chat_id: int):
    dice_msg = await bot.send_dice(chat_id, emoji="🎲")
    await asyncio.sleep(4)
    value = dice_msg.dice.value
    await db.set_nft_number(user_id, value)
    nft = await db.get_nft(value)
    if nft:
        text = f"🎁 Тебе выпал подарок:\n\n<b>{nft['name']}</b>\n{nft['description']}"
        if nft["image_url"]:
            try:
                await bot.send_photo(chat_id, nft["image_url"], caption=text, parse_mode="HTML")
            except TelegramBadRequest:
                await bot.send_message(chat_id, text, parse_mode="HTML")
        else:
            await bot.send_message(chat_id, text, parse_mode="HTML")
    else:
        await bot.send_message(chat_id, f"🎁 Тебе выпало число {value}!")

    await bot.send_message(
        chat_id,
        "Чтобы получить подарок, напиши менеджеру "
        f"@{config.MANAGER_USERNAME}, укажи выпавший номер и переведи "
        f"<b>{config.GIFT_PRICE_STARS} Stars</b> ⭐",
        parse_mode="HTML",
    )
