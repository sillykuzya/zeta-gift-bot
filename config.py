import os

# --- Обязательные переменные окружения (задать в .env или экспортом в Termux) ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")
DB_DSN = os.getenv("DB_DSN", "postgresql://user:password@localhost:5432/ryzen")

# ID группового чата модераторов (бот должен быть добавлен туда и иметь права отправки/удаления сообщений)
MODERATION_GROUP_ID = int(os.getenv("MODERATION_GROUP_ID", "-1000000000000"))

# ID администраторов бота, через запятую: ADMIN_IDS=123456,789012
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}

# Юзернейм менеджера, который выдаёт подарки (без @)
MANAGER_USERNAME = os.getenv("MANAGER_USERNAME", "manager_username")

# --- Тайминги (секунды) ---
STEP1_TIMEOUT = 5 * 60
STEP2_TIMEOUT = 20 * 60
MODERATION_TIMEOUT = 60

# --- Прочие константы ---
STEP2_REQUIRED_SCREENSHOTS = 10
MAX_ATTEMPTS = 3
LOCKOUT_HOURS = 24
GIFT_PRICE_STARS = 50

# Статусы пользователя (хранятся в users.status)
STATUS_NEW = "new"
STATUS_STEP1_TASK = "step1_pending_task"
STATUS_STEP1_REVIEW = "step1_pending_review"
STATUS_STEP2_TASK = "step2_pending_task"
STATUS_STEP2_REVIEW = "step2_pending_review"
STATUS_STEP3_SPONSORS = "step3_sponsors"
STATUS_DONE = "done"
STATUS_LOCKED = "locked"
