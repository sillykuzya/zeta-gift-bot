import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
import db
from scheduler import scheduler
from handlers import user as user_handlers
from handlers import moderation as moderation_handlers
from handlers import admin as admin_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)


async def main():
    if config.BOT_TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise RuntimeError("Задай BOT_TOKEN через переменную окружения")

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    await db.create_pool(config.DB_DSN)
    await db.init_db()
    log.info("База данных готова")

    # Порядок важен: admin — самый специфичный (фильтр по ADMIN_IDS),
    # moderation — обрабатывает mod:*, user — всё остальное (/start, фото, check_subs)
    dp.include_router(admin_handlers.router)
    dp.include_router(moderation_handlers.router)
    dp.include_router(user_handlers.router)

    scheduler.start()
    log.info("Планировщик запущен")

    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Бот запущен, начинаю polling…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Остановлено")
