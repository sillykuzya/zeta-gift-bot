from aiogram.fsm.state import State, StatesGroup


class SponsorStates(StatesGroup):
    waiting_name = State()
    waiting_chat_ref = State()
    waiting_url = State()


class NFTStates(StatesGroup):
    waiting_number = State()
    waiting_name = State()
    waiting_description = State()
    waiting_image = State()


class ModeratorStates(StatesGroup):
    waiting_id = State()


class BroadcastStates(StatesGroup):
    waiting_text = State()
    waiting_confirm = State()


class BanStates(StatesGroup):
    waiting_id = State()
    waiting_reason = State()


class UnbanStates(StatesGroup):
    waiting_id = State()


class TaskTextStates(StatesGroup):
    waiting_text = State()
