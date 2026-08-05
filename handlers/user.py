import asyncio

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery

import config
import db
import logic
import keyboards
import replies

router = Router(name="user")

_user_locks: dict[int, asyncio.Lock] = {}
_last_step1_album_warned: dict[int, str] = {}


def _lock_for(user_id: int) -> asyncio.Lock:
    """Одна блокировка на пользователя — не даёт двум почти одновременным фото
    (например, если случайно отправить два скрина подряд на шаге 1) обогнать
    друг друга и оба проскочить проверку статуса до того, как первое обновит БД."""
    return _user_locks.setdefault(user_id, asyncio.Lock())


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    if await db.is_banned(user_id):
        await message.answer(replies.BANNED)
        return

    await db.create_user_if_not_exists(user_id, username)

    if await db.is_locked(user_id):
        await message.answer(replies.LOCKED_ON_START)
        return

    user = await db.get_user(user_id)
    status = user["status"]

    if status == config.STATUS_NEW:
        await message.answer(replies.WELCOME)
        await logic.issue_step1_task(message.bot, user_id)
    elif status in (config.STATUS_STEP1_TASK, config.STATUS_STEP2_TASK):
        await message.answer(replies.active_task_reminder(user["task_text"]))
    elif status in (config.STATUS_STEP1_REVIEW, config.STATUS_STEP2_REVIEW):
        await message.answer(replies.REVIEW_WAIT)
    elif status == config.STATUS_STEP3_SPONSORS:
        sponsors = await db.list_sponsors(active_only=True)
        await message.answer(replies.SPONSORS_REMINDER, reply_markup=keyboards.sponsors_kb(sponsors))
    elif status == config.STATUS_DONE:
        await message.answer(replies.already_done(config.MANAGER_USERNAME))
    elif status == config.STATUS_LOCKED:
        await message.answer(replies.LOCKED_STATUS)


@router.message(F.chat.type == "private", F.content_type == "photo")
async def handle_photo(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    file_id = message.photo[-1].file_id

    async with _lock_for(user_id):
        user = await db.get_user(user_id)
        if user is None:
            return

        if user["status"] == config.STATUS_STEP1_TASK:
            if message.media_group_id:
                # на шаге 1 нужен ровно один скриншот — альбом целиком отклоняем,
                # предупреждаем один раз на альбом, а не на каждое фото в нём
                if _last_step1_album_warned.get(user_id) != message.media_group_id:
                    _last_step1_album_warned[user_id] = message.media_group_id
                    await message.answer(replies.STEP1_ALBUM_REJECTED)
                return
            await logic.submit_step1_photo(message.bot, user_id, username, file_id)
        elif user["status"] == config.STATUS_STEP2_TASK:
            if message.media_group_id:
                # часть альбома — считаем молча, сводку пришлём одним сообщением после
                await logic.append_step2_photo(message.bot, user_id, username, file_id, notify_progress=False)
                logic.schedule_album_summary(message.bot, user_id)
            else:
                await logic.append_step2_photo(message.bot, user_id, username, file_id)
        elif user["status"] in (config.STATUS_STEP1_REVIEW, config.STATUS_STEP2_REVIEW):
            await message.answer(replies.ALREADY_IN_REVIEW)
        else:
            await message.answer(replies.PHOTO_NOT_NEEDED)


@router.callback_query(F.data == "check_subs")
async def cb_check_subs(callback: CallbackQuery):
    user_id = callback.from_user.id
    not_subscribed = await logic.check_subscriptions(callback.bot, user_id)
    if not_subscribed:
        await callback.answer(replies.SUBSCRIBE_ALERT, show_alert=True)
        await callback.message.answer(replies.not_subscribed_list(not_subscribed))
        return

    await callback.answer(replies.ALL_SUBSCRIBED_ALERT)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await logic.finish_sponsors_step(callback.bot, user_id, callback.message.chat.id)
