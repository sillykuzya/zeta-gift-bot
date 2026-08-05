import asyncio

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import config
import db
import keyboards
from states import SponsorStates, NFTStates, ModeratorStates, BroadcastStates, BanStates, TaskTextStates

router = Router(name="admin")
# Весь роутер доступен только администраторам из config.ADMIN_IDS
router.message.filter(lambda message: message.from_user.id in config.ADMIN_IDS)
router.callback_query.filter(lambda c: c.from_user.id in config.ADMIN_IDS)


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("⚙️ <b>Админ-панель</b>", reply_markup=keyboards.admin_main_kb())


@router.callback_query(F.data == "adm:main")
async def cb_admin_main(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.clear()
    await callback.message.edit_text("⚙️ <b>Админ-панель</b>", reply_markup=keyboards.admin_main_kb())
    await callback.answer()


# ==================== СПОНСОРЫ ====================

@router.callback_query(F.data == "adm:sponsors")
async def cb_sponsors_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await callback.message.edit_text("📢 <b>Спонсоры</b>", reply_markup=keyboards.sponsors_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "adm:sponsors:list")
async def cb_sponsors_list(callback: CallbackQuery):
    sponsors = await db.list_sponsors(active_only=False)
    if not sponsors:
        text = "Список спонсоров пуст."
    else:
        text = "\n".join(f"• {s['name']} — {s['url']} (chat_ref: {s['chat_ref']})" for s in sponsors)
    await callback.message.edit_text(text, reply_markup=keyboards.back_kb("adm:sponsors"))
    await callback.answer()


@router.callback_query(F.data == "adm:sponsors:add")
async def cb_sponsors_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SponsorStates.waiting_name)
    await callback.message.edit_text("Введи название канала-спонсора:")
    await callback.answer()


@router.message(SponsorStates.waiting_name)
async def sponsor_name_input(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(SponsorStates.waiting_chat_ref)
    await message.answer(
        "Введи chat_ref для проверки подписки — @username канала или его числовой ID "
        "(бот должен быть администратором этого канала):"
    )


@router.message(SponsorStates.waiting_chat_ref)
async def sponsor_chatref_input(message: Message, state: FSMContext):
    await state.update_data(chat_ref=message.text.strip())
    await state.set_state(SponsorStates.waiting_url)
    await message.answer("Введи ссылку на канал для кнопки-приглашения:")


@router.message(SponsorStates.waiting_url)
async def sponsor_url_input(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_sponsor(data["name"], data["chat_ref"], message.text.strip())
    await state.clear()
    await message.answer("✅ Спонсор добавлен.", reply_markup=keyboards.sponsors_menu_kb())


@router.callback_query(F.data == "adm:sponsors:del")
async def cb_sponsors_del_menu(callback: CallbackQuery):
    sponsors = await db.list_sponsors(active_only=False)
    if not sponsors:
        await callback.answer("Список пуст.", show_alert=True)
        return
    await callback.message.edit_text("Выбери спонсора для удаления:", reply_markup=keyboards.sponsors_delete_kb(sponsors))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:sponsors:del:"))
async def cb_sponsors_del_confirm(callback: CallbackQuery):
    sponsor_id = int(callback.data.split(":")[-1])
    await db.remove_sponsor(sponsor_id)
    await callback.answer("Удалено.")
    sponsors = await db.list_sponsors(active_only=False)
    if sponsors:
        await callback.message.edit_text("Выбери спонсора для удаления:", reply_markup=keyboards.sponsors_delete_kb(sponsors))
    else:
        await callback.message.edit_text("📢 <b>Спонсоры</b>", reply_markup=keyboards.sponsors_menu_kb())


# ==================== NFT ====================

@router.callback_query(F.data == "adm:nft")
async def cb_nft_menu(callback: CallbackQuery):
    await callback.message.edit_text("🎁 <b>NFT-подарки</b>", reply_markup=keyboards.nft_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "adm:nft:list")
async def cb_nft_list(callback: CallbackQuery):
    items = await db.list_nft()
    if not items:
        text = "NFT ещё не добавлены."
    else:
        text = "\n".join(f"{n['number']}. {n['name']} — {n['description']}" for n in items)
    await callback.message.edit_text(text, reply_markup=keyboards.back_kb("adm:nft"))
    await callback.answer()


@router.callback_query(F.data == "adm:nft:add")
async def cb_nft_add(callback: CallbackQuery):
    await callback.message.edit_text("Выбери номер (1–6), которому назначить подарок:", reply_markup=keyboards.nft_numbers_kb("adm:nft:setnum"))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:nft:setnum:"))
async def cb_nft_setnum(callback: CallbackQuery, state: FSMContext):
    number = int(callback.data.split(":")[-1])
    await state.update_data(number=number)
    await state.set_state(NFTStates.waiting_name)
    await callback.message.edit_text(f"Номер {number}. Введи название подарка:")
    await callback.answer()


@router.message(NFTStates.waiting_name)
async def nft_name_input(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(NFTStates.waiting_description)
    await message.answer("Введи описание подарка:")


@router.message(NFTStates.waiting_description)
async def nft_description_input(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(NFTStates.waiting_image)
    await message.answer("Пришли ссылку на картинку подарка (или отправь «-», если без картинки):")


@router.message(NFTStates.waiting_image)
async def nft_image_input(message: Message, state: FSMContext):
    data = await state.get_data()
    image_url = None if message.text.strip() == "-" else message.text.strip()
    await db.upsert_nft(data["number"], data["name"], data["description"], image_url)
    await state.clear()
    await message.answer("✅ NFT сохранён.", reply_markup=keyboards.nft_menu_kb())


@router.callback_query(F.data == "adm:nft:del")
async def cb_nft_del_menu(callback: CallbackQuery):
    await callback.message.edit_text("Выбери номер для удаления:", reply_markup=keyboards.nft_numbers_kb("adm:nft:delnum"))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:nft:delnum:"))
async def cb_nft_delnum(callback: CallbackQuery):
    number = int(callback.data.split(":")[-1])
    await db.remove_nft(number)
    await callback.answer("Удалено.")
    await callback.message.edit_text("🎁 <b>NFT-подарки</b>", reply_markup=keyboards.nft_menu_kb())


# ==================== МОДЕРАТОРЫ ====================

@router.callback_query(F.data == "adm:mods")
async def cb_mods_menu(callback: CallbackQuery):
    await callback.message.edit_text("👮 <b>Модераторы</b>", reply_markup=keyboards.mods_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "adm:mods:list")
async def cb_mods_list(callback: CallbackQuery):
    mods = await db.list_moderators()
    text = "\n".join(f"• {m['user_id']}" for m in mods) if mods else "Модераторов нет."
    await callback.message.edit_text(text, reply_markup=keyboards.back_kb("adm:mods"))
    await callback.answer()


@router.callback_query(F.data == "adm:mods:add")
async def cb_mods_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ModeratorStates.waiting_id)
    await callback.message.edit_text("Пришли Telegram ID пользователя, которого сделать модератором:")
    await callback.answer()


@router.message(ModeratorStates.waiting_id)
async def mods_id_input(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно число (ID пользователя). Попробуй ещё раз:")
        return
    await db.add_moderator(uid)
    await state.clear()
    await message.answer("✅ Модератор добавлен.", reply_markup=keyboards.mods_menu_kb())


@router.callback_query(F.data == "adm:mods:del")
async def cb_mods_del_menu(callback: CallbackQuery):
    mods = await db.list_moderators()
    if not mods:
        await callback.answer("Список пуст.", show_alert=True)
        return
    await callback.message.edit_text("Выбери модератора для удаления:", reply_markup=keyboards.mods_delete_kb(mods))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:mods:del:"))
async def cb_mods_del_confirm(callback: CallbackQuery):
    uid = int(callback.data.split(":")[-1])
    await db.remove_moderator(uid)
    await callback.answer("Удалено.")
    await callback.message.edit_text("👮 <b>Модераторы</b>", reply_markup=keyboards.mods_menu_kb())


# ==================== СТАТИСТИКА ====================

@router.callback_query(F.data == "adm:stats")
async def cb_stats(callback: CallbackQuery):
    s = await db.get_stats()
    lines = [f"👥 Всего пользователей: <b>{s['total']}</b>", "", "По этапам:"]
    for row in s["by_status"]:
        lines.append(f"• {row['status']}: {row['cnt']}")
    lines.append("")
    lines.append(f"✅ Одобрено модерацией: {s['approved']}")
    lines.append(f"❌ Отклонено модерацией: {s['rejected']}")
    lines.append("")
    lines.append("🏆 Топ активных:")
    for u in s["top"]:
        uname = f"@{u['username']}" if u["username"] else str(u["user_id"])
        lines.append(f"• {uname} — {u['status']}")
    await callback.message.edit_text("\n".join(lines), reply_markup=keyboards.back_kb("adm:main"), parse_mode="HTML")
    await callback.answer()


# ==================== РАССЫЛКА ====================

@router.callback_query(F.data == "adm:broadcast")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastStates.waiting_text)
    await callback.message.edit_text("Введи текст рассылки (поддерживается HTML-форматирование):")
    await callback.answer()


@router.message(BroadcastStates.waiting_text)
async def broadcast_text_input(message: Message, state: FSMContext):
    await state.update_data(text=message.html_text)
    await state.set_state(BroadcastStates.waiting_confirm)
    await message.answer("Кому отправить?", reply_markup=keyboards.broadcast_filter_kb())


@router.callback_query(F.data.startswith("adm:broadcast:filter:"), BroadcastStates.waiting_confirm)
async def broadcast_send(callback: CallbackQuery, state: FSMContext):
    filter_value = callback.data.split(":")[-1]
    data = await state.get_data()
    text = data["text"]
    await state.clear()

    status_filter = None if filter_value == "all" else filter_value
    user_ids = await db.all_user_ids(status_filter)
    await callback.message.edit_text(f"🚀 Рассылка запущена, получателей: {len(user_ids)}")
    await callback.answer()

    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await callback.bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # анти-флуд
    await callback.message.answer(f"✅ Рассылка завершена. Успешно: {sent}, ошибок: {failed}")


# ==================== БАН-ЛИСТ ====================

@router.callback_query(F.data == "adm:bans")
async def cb_bans_menu(callback: CallbackQuery):
    await callback.message.edit_text("🚫 <b>Бан-лист</b>", reply_markup=keyboards.bans_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "adm:bans:list")
async def cb_bans_list(callback: CallbackQuery):
    bans = await db.list_bans()
    text = "\n".join(f"• {b['user_id']} — {b['reason'] or 'без причины'}" for b in bans) if bans else "Бан-лист пуст."
    await callback.message.edit_text(text, reply_markup=keyboards.back_kb("adm:bans"))
    await callback.answer()


@router.callback_query(F.data == "adm:bans:add")
async def cb_bans_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BanStates.waiting_id)
    await callback.message.edit_text("Пришли Telegram ID пользователя для блокировки:")
    await callback.answer()


@router.message(BanStates.waiting_id)
async def ban_id_input(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно число (ID пользователя). Попробуй ещё раз:")
        return
    await state.update_data(uid=uid)
    await state.set_state(BanStates.waiting_reason)
    await message.answer("Причина блокировки (или «-» если без причины):")


@router.message(BanStates.waiting_reason)
async def ban_reason_input(message: Message, state: FSMContext):
    data = await state.get_data()
    reason = None if message.text.strip() == "-" else message.text.strip()
    await db.ban_user(data["uid"], reason)
    await state.clear()
    await message.answer("✅ Пользователь заблокирован.", reply_markup=keyboards.bans_menu_kb())


@router.callback_query(F.data == "adm:bans:del")
async def cb_bans_unban_menu(callback: CallbackQuery):
    bans = await db.list_bans()
    if not bans:
        await callback.answer("Список пуст.", show_alert=True)
        return
    await callback.message.edit_text("Выбери, кого разблокировать:", reply_markup=keyboards.bans_unban_kb(bans))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:bans:del:"))
async def cb_bans_unban_confirm(callback: CallbackQuery):
    uid = int(callback.data.split(":")[-1])
    await db.unban_user(uid)
    await callback.answer("Разблокирован.")
    await callback.message.edit_text("🚫 <b>Бан-лист</b>", reply_markup=keyboards.bans_menu_kb())


# ==================== ТЕКСТЫ ЗАДАНИЙ ====================

@router.callback_query(F.data == "adm:texts")
async def cb_texts_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "📝 <b>Тексты заданий</b>\nВыбери шаг, чтобы посмотреть/изменить список фраз:",
        reply_markup=keyboards.texts_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:texts:step:"))
async def cb_texts_step(callback: CallbackQuery):
    step = int(callback.data.split(":")[-1])
    texts = await db.list_task_texts(step)
    await callback.message.edit_text(
        f"Фразы для шага {step} (нажми, чтобы удалить):",
        reply_markup=keyboards.texts_list_kb(step, texts),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:texts:add:"))
async def cb_texts_add(callback: CallbackQuery, state: FSMContext):
    step = int(callback.data.split(":")[-1])
    await state.update_data(step=step)
    await state.set_state(TaskTextStates.waiting_text)
    await callback.message.edit_text(f"Введи новую фразу для шага {step}:")
    await callback.answer()


@router.message(TaskTextStates.waiting_text)
async def texts_add_input(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_task_text(data["step"], message.text)
    await state.clear()
    texts = await db.list_task_texts(data["step"])
    await message.answer(
        f"✅ Добавлено. Фразы для шага {data['step']}:",
        reply_markup=keyboards.texts_list_kb(data["step"], texts),
    )


@router.callback_query(F.data.startswith("adm:texts:del:"))
async def cb_texts_del(callback: CallbackQuery):
    _, _, _, text_id, step = callback.data.split(":")
    await db.remove_task_text(int(text_id))
    await callback.answer("Удалено.")
    texts = await db.list_task_texts(int(step))
    await callback.message.edit_text(
        f"Фразы для шага {step} (нажми, чтобы удалить):",
        reply_markup=keyboards.texts_list_kb(int(step), texts),
    )
