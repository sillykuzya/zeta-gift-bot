# zeta-gift-bot

Telegram-бот для розыгрыша NFT-подарков с воронкой заданий (TikTok-комментарии → модерация → подписка на спонсоров → рулетка → выдача подарка через менеджера).

## Структура

```
config.py              настройки (токен, БД, ID группы модерации, менеджер)
db.py                   вся работа с PostgreSQL
states.py               FSM-состояния админ-панели
keyboards.py            инлайн-клавиатуры
replies.py              все текстовые реплики бота (пользователям и модераторам)
logic.py                бизнес-логика воронки и модерации
scheduler.py            таймеры (APScheduler)
handlers/user.py        /start, приём скриншотов, проверка подписок
handlers/moderation.py  кнопки Одобрить/Отклонить
handlers/admin.py       админ-панель /admin
main.py                 точка входа
```

## Установка

```bash
git clone https://github.com/sillykuzya/zeta-gift-bot.git
cd zeta-gift-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

При каждом новом запуске сессии активируй venv заново:

```bash
cd zeta-gift-bot
source venv/bin/activate
python main.py
```

Выйти из venv: `deactivate`.

Если `pip install` падает на сборке `pydantic-core` из исходников (частый случай на Termux с новым Python) — собери проект в Ubuntu через `proot-distro` или используй Python 3.12/3.13, там для aiogram есть готовые wheel-пакеты.

## Переменные окружения

Скопируй `.env.example` в `.env` и заполни:

```bash
cp .env.example .env
```

```bash
BOT_TOKEN=123456789:AAExampleTokenReplaceMe
DB_DSN=postgresql://zeta_user:zeta_password@localhost:5432/zeta
MODERATION_GROUP_ID=-1001234567890
ADMIN_IDS=111111111,222222222
MANAGER_USERNAME=your_manager
```

`config.py` подхватывает `.env` автоматически через `python-dotenv`. Можно и без файла — просто экспортировать эти переменные в оболочке.

`MODERATION_GROUP_ID` — ID группового чата модераторов. Бот должен быть в этой группе с правами удаления сообщений. Модераторов добавляй через `/admin → Модераторы` (их ID, членство в группе для этого не обязательно — права проверяются по таблице `moderators`).

Для каждого спонсорского канала `chat_ref` (в разделе Спонсоры) должен быть `@username` или числовой ID канала, и бот обязан быть администратором этого канала — иначе `get_chat_member` не сработает.

## Запуск

```bash
python main.py
```

## .gitignore

В репозиторий не должны попадать `venv/`, `.env` и `__pycache__/` — они уже перечислены в `.gitignore`.
