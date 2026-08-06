from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def start_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Начать", callback_data="start_game")
    return kb.as_markup()


def continue_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔥 Поехали", callback_data="begin_tasks")
    return kb.as_markup()


def manager_kb(link: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✉️ Написать менеджеру", url=link)
    return kb.as_markup()


def given_kb(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Выдано", callback_data=f"given:{user_id}")
    return kb.as_markup()


def moderation_kb(item_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Одобрить", callback_data=f"mod:approve:{item_id}")
    kb.button(text="❌ Отклонить", callback_data=f"mod:reject:{item_id}")
    kb.adjust(2)
    return kb.as_markup()


def sponsors_kb(sponsors) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in sponsors:
        kb.button(text=f"📢 {s['name']}", url=s["url"])
    kb.button(text="✅ Проверить подписки", callback_data="check_subs")
    kb.adjust(1)
    return kb.as_markup()


def admin_main_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Спонсоры", callback_data="adm:sponsors")
    kb.button(text="🎁 NFT-подарки", callback_data="adm:nft")
    kb.button(text="👮 Модераторы", callback_data="adm:mods")
    kb.button(text="📊 Статистика", callback_data="adm:stats")
    kb.button(text="✉️ Рассылка", callback_data="adm:broadcast")
    kb.button(text="🚫 Бан-лист", callback_data="adm:bans")
    kb.button(text="📝 Тексты заданий", callback_data="adm:texts")
    kb.adjust(2)
    return kb.as_markup()


def back_kb(target: str = "adm:main") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data=target)
    return kb.as_markup()


def sponsors_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить", callback_data="adm:sponsors:add")
    kb.button(text="➖ Удалить", callback_data="adm:sponsors:del")
    kb.button(text="📋 Список", callback_data="adm:sponsors:list")
    kb.button(text="⬅️ Назад", callback_data="adm:main")
    kb.adjust(2, 1)
    return kb.as_markup()


def sponsors_delete_kb(sponsors) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in sponsors:
        kb.button(text=f"❌ {s['name']}", callback_data=f"adm:sponsors:del:{s['id']}")
    kb.button(text="⬅️ Назад", callback_data="adm:sponsors")
    kb.adjust(1)
    return kb.as_markup()


def nft_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить/изменить", callback_data="adm:nft:add")
    kb.button(text="➖ Удалить", callback_data="adm:nft:del")
    kb.button(text="📋 Список", callback_data="adm:nft:list")
    kb.button(text="⬅️ Назад", callback_data="adm:main")
    kb.adjust(2, 1)
    return kb.as_markup()


def nft_numbers_kb(prefix: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for n in range(1, 7):
        kb.button(text=str(n), callback_data=f"{prefix}:{n}")
    kb.button(text="⬅️ Назад", callback_data="adm:nft")
    kb.adjust(6, 1)
    return kb.as_markup()


def mods_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить", callback_data="adm:mods:add")
    kb.button(text="➖ Удалить", callback_data="adm:mods:del")
    kb.button(text="📋 Список", callback_data="adm:mods:list")
    kb.button(text="⬅️ Назад", callback_data="adm:main")
    kb.adjust(2, 1)
    return kb.as_markup()


def mods_delete_kb(mods) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for m in mods:
        kb.button(text=f"❌ {m['user_id']}", callback_data=f"adm:mods:del:{m['user_id']}")
    kb.button(text="⬅️ Назад", callback_data="adm:mods")
    kb.adjust(1)
    return kb.as_markup()


def bans_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚫 Заблокировать", callback_data="adm:bans:add")
    kb.button(text="✅ Разблокировать", callback_data="adm:bans:del")
    kb.button(text="📋 Список", callback_data="adm:bans:list")
    kb.button(text="⬅️ Назад", callback_data="adm:main")
    kb.adjust(2, 1)
    return kb.as_markup()


def bans_unban_kb(bans) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for b in bans:
        kb.button(text=f"✅ {b['user_id']}", callback_data=f"adm:bans:del:{b['user_id']}")
    kb.button(text="⬅️ Назад", callback_data="adm:bans")
    kb.adjust(1)
    return kb.as_markup()


def broadcast_filter_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Всем", callback_data="adm:broadcast:filter:all")
    kb.button(text="На step1", callback_data="adm:broadcast:filter:step1_pending_task")
    kb.button(text="На step2", callback_data="adm:broadcast:filter:step2_pending_task")
    kb.button(text="Ждут менеджера", callback_data="adm:broadcast:filter:awaiting_manager")
    kb.button(text="Получили подарок", callback_data="adm:broadcast:filter:gift_given")
    kb.button(text="⬅️ Отмена", callback_data="adm:main")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def texts_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Шаг 1", callback_data="adm:texts:step:1")
    kb.button(text="Шаг 2", callback_data="adm:texts:step:2")
    kb.button(text="⬅️ Назад", callback_data="adm:main")
    kb.adjust(2, 1)
    return kb.as_markup()


def texts_list_kb(step: int, texts) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in texts:
        label = t["text"][:20] + ("…" if len(t["text"]) > 20 else "")
        kb.button(text=f"❌ {label}", callback_data=f"adm:texts:del:{t['id']}:{step}")
    kb.button(text="➕ Добавить", callback_data=f"adm:texts:add:{step}")
    kb.button(text="⬅️ Назад", callback_data="adm:texts")
    kb.adjust(1)
    return kb.as_markup()
