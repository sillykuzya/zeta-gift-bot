# Ryzen — бот розыгрыша NFT-подарков

## Структура

```
config.py           настройки (токен, БД, ID группы модерации, менеджер)
db.py                вся работа с PostgreSQL
states.py             FSM-состояния админ-панели
keyboards.py         инлайн-клавиатуры
logic.py             бизнес-логика воронки и модерации
scheduler.py         таймеры (APScheduler)
handlers/user.py     /start, приём скриншотов, проверка подписок
handlers/moderation.py  кнопки Одобрить/Отклонить
handlers/admin.py    админ-панель /admin
main.py              точка входа
```

## Установка (Termux)

```bash
pkg install postgresql python
cd ryzen_bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

При каждом новом запуске сессии Termux активируй venv заново:

```bash
cd ryzen_bot
source venv/bin/activate
python main.py
```

Выйти из venv: `deactivate`.

## Переменные окружения

Скопируй `.env.example` в `.env` и заполни:

```bash
cp .env.example .env
```

```bash
BOT_TOKEN=123456789:AAExampleTokenReplaceMe
DB_DSN=postgresql://ryzen_user:ryzen_password@localhost:5432/ryzen
MODERATION_GROUP_ID=-1001234567890
ADMIN_IDS=111111111,222222222
MANAGER_USERNAME=your_manager
```

`config.py` подхватывает `.env` автоматически через `python-dotenv`. Можно и без файла — просто экспортировать эти переменные в оболочке.

`MODERATION_GROUP_ID` — ID группового чата модераторов. Бот должен быть в этой группе с правами удаления сообщений. Модераторов добавляй через `/admin → Модераторы` (их ID, не обязательно членство в группе даёт права — права проверяются по таблице `moderators`).

Для каждого спонсорского канала `chat_ref` (в разделе Спонсоры) должен быть `@username` или числовой ID канала, и бот обязан быть администратором этого канала — иначе `get_chat_member` не сработает.

## Запуск

```bash
python main.py
```

## Что не покрыто ТЗ и решено по умолчанию

- Ровно 10 скриншотов на шаге 2: бот принимает первые 10 присланных фото, автоматически отправляет на модерацию по достижении десятого.
- Первый список текстов (шаг 1) сделан таким же редактируемым через `/admin → Тексты заданий`, как и второй список — ТЗ явно требовало это только для шага 2, но иметь единый интерфейс проще, чем хардкодить один список.
- Если спонсоров не добавлено, шаг 3 пропускается автоматически.
