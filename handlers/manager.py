from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import config
import db
import replies

router = Router(name="manager")
# Доступно администраторам и отдельно назначенным менеджерам (MANAGER_IDS в .env)
router.message.filter(
    lambda m: m.from_user.id in config.ADMIN_IDS or m.from_user.id in config.MANAGER_IDS
)


@router.message(Command("given"))
async def cmd_given(message: Message):
    """/given <user_id> — отмечает, что менеджер выдал подарок этому пользователю."""
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Использование: /given <user_id>")
        return

    user_id = int(parts[1])
    user = await db.get_user(user_id)
    if user is None:
        await message.answer("Такого пользователя нет в базе. Проверь ID.")
        return

    if user["status"] != config.STATUS_AWAITING_MANAGER:
        await message.answer(
            f"У пользователя {user_id} статус «{user['status']}», а не «ждёт менеджера». "
            "Возможно, ID перепутан, или подарок уже отмечен."
        )
        return

    await db.set_status(user_id, config.STATUS_GIFT_GIVEN)
    await message.answer(f"✅ Отмечено: пользователь {user_id} получил подарок.")
    try:
        await message.bot.send_message(user_id, replies.GIFT_GIVEN_CONFIRMED)
    except Exception:
        pass
