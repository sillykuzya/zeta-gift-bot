from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery

import config
import db
import logic
import keyboards

router = Router(name="user")


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    if await db.is_banned(user_id):
        await message.answer("🚫 Ты заблокирован и не можешь участвовать в розыгрыше.")
        return

    await db.create_user_if_not_exists(user_id, username)

    if await db.is_locked(user_id):
        await message.answer(
            "⏳ Доступ временно заблокирован из-за превышения лимита попыток. Попробуй позже."
        )
        return

    user = await db.get_user(user_id)
    status = user["status"]

    if status == config.STATUS_NEW:
        await message.answer(
            "👋 Добро пожаловать в розыгрыш NFT-подарков!\n\n"
            "Чтобы получить шанс выиграть подарок, пройди 3 простых шага. "
            "Начинаем с первого 👇"
        )
        await logic.issue_step1_task(message.bot, user_id)
    elif status in (config.STATUS_STEP1_TASK, config.STATUS_STEP2_TASK):
        await message.answer(
            f"У тебя уже есть активное задание:\n\n«{user['task_text']}»\n\n"
            "Пришли скриншот, когда выполнишь его 📸"
        )
    elif status in (config.STATUS_STEP1_REVIEW, config.STATUS_STEP2_REVIEW):
        await message.answer("⏳ Твой предыдущий скриншот ещё проверяется модераторами, подожди.")
    elif status == config.STATUS_STEP3_SPONSORS:
        sponsors = await db.list_sponsors(active_only=True)
        await message.answer(
            "📢 Подпишись на каналы ниже и нажми «Проверить подписки»:",
            reply_markup=keyboards.sponsors_kb(sponsors),
        )
    elif status == config.STATUS_DONE:
        await message.answer(
            f"🎉 Ты уже прошёл розыгрыш! Для получения подарка обратись к "
            f"@{config.MANAGER_USERNAME}."
        )
    elif status == config.STATUS_LOCKED:
        await message.answer("⏳ Доступ временно заблокирован. Попробуй позже.")


@router.message(F.chat.type == "private", F.content_type == "photo")
async def handle_photo(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    user = await db.get_user(user_id)
    if user is None:
        return
    file_id = message.photo[-1].file_id

    if user["status"] == config.STATUS_STEP1_TASK:
        await logic.submit_step1_photo(message.bot, user_id, username, file_id)
    elif user["status"] == config.STATUS_STEP2_TASK:
        if message.media_group_id:
            # часть альбома — считаем молча, сводку пришлём одним сообщением после
            await logic.append_step2_photo(message.bot, user_id, username, file_id, notify_progress=False)
            logic.schedule_album_summary(message.bot, user_id)
        else:
            await logic.append_step2_photo(message.bot, user_id, username, file_id)
    else:
        await message.answer("Сейчас скриншот не требуется 🙂")


@router.callback_query(F.data == "check_subs")
async def cb_check_subs(callback: CallbackQuery):
    user_id = callback.from_user.id
    not_subscribed = await logic.check_subscriptions(callback.bot, user_id)
    if not_subscribed:
        names = "\n".join(f"• {n}" for n in not_subscribed)
        await callback.answer("Подпишись на все каналы!", show_alert=True)
        await callback.message.answer(f"❗ Ты ещё не подписан на:\n{names}")
        return

    await callback.answer("Все подписки на месте! 🎉")
    try:
        await callback.message.delete()
    except Exception:
        pass
    await logic.finish_sponsors_step(callback.bot, user_id, callback.message.chat.id)
