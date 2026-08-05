from aiogram import Router, F
from aiogram.types import CallbackQuery

import db
import logic

router = Router(name="moderation")


@router.callback_query(F.data.startswith("mod:"))
async def cb_moderation_decision(callback: CallbackQuery):
    moderator_id = callback.from_user.id
    if not await db.is_moderator(moderator_id):
        await callback.answer("Ты не модератор.", show_alert=True)
        return

    _, action, item_id_str = callback.data.split(":")
    item_id = int(item_id_str)
    approved = action == "approve"

    item = await db.get_moderation_item(item_id)
    if item is None or item["status"] != "pending":
        await callback.answer("Уже обработано другим модератором.", show_alert=True)
        return

    await callback.answer("Принято ✅" if approved else "Отклонено ❌")
    await logic.process_moderation_decision(callback.bot, item_id, approved, moderator_id)
