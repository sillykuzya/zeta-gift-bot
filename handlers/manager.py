from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import config
import db
import keyboards
import logic
import replies
from states import ManagerStates

router = Router(name="manager")
# Доступно администраторам и отдельно назначенным менеджерам (MANAGER_IDS в .env)
router.message.filter(
    lambda m: m.from_user.id in config.ADMIN_IDS or m.from_user.id in config.MANAGER_IDS
)
router.callback_query.filter(
    lambda c: c.from_user.id in config.ADMIN_IDS or c.from_user.id in config.MANAGER_IDS
)


@router.callback_query(F.data.startswith("given:"))
async def cb_given(callback: CallbackQuery):
    """Кнопка «✅ Выдано» под уведомлением о новом получателе — основной способ отметки."""
    user_id = int(callback.data.split(":")[1])
    ok, text = await logic.mark_gift_given(callback.bot, user_id)
    await callback.answer("Отмечено ✅" if ok else "Не вышло", show_alert=not ok)
    try:
        await callback.message.edit_text(text, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, parse_mode="HTML")


@router.message(Command("given"))
async def cmd_given(message: Message, state: FSMContext):
    """/given <id или @username> — отметить выдачу вручную (резервный способ, если
    уведомление с кнопкой потерялось)."""
    parts = message.text.split(maxsplit=1)
    if len(parts) == 2:
        await _handle_identifier(message, parts[1])
        return
    await state.set_state(ManagerStates.waiting_identifier)
    await message.answer(replies.GIVEN_USAGE)


@router.message(ManagerStates.waiting_identifier)
async def given_identifier_input(message: Message, state: FSMContext):
    await state.clear()
    await _handle_identifier(message, message.text)


async def _handle_identifier(message: Message, identifier: str):
    user_id = await db.resolve_user_id(identifier)
    if user_id is None:
        await message.answer(replies.GIVEN_NOT_FOUND)
        return
    ok, text = await logic.mark_gift_given(message.bot, user_id)
    await message.answer(text, parse_mode="HTML")


@router.message(Command("waiting"))
async def cmd_waiting(message: Message):
    """Список тех, кто сейчас на этапе «ждёт менеджера», с кнопкой «Выдано» у каждого."""
    users = await db.users_with_status(config.STATUS_AWAITING_MANAGER)
    if not users:
        await message.answer(replies.WAITING_LIST_EMPTY)
        return
    for u in users:
        mention = logic.user_mention(u["user_id"], u["username"])
        await message.answer(
            replies.manager_notify(mention, u["nft_number"]),
            parse_mode="HTML",
            reply_markup=keyboards.given_kb(u["user_id"]),
        )
