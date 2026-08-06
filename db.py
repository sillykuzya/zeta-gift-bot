import json
from datetime import datetime, timedelta, timezone

import asyncpg

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    task_text TEXT,
    task_photos JSONB NOT NULL DEFAULT '[]',
    task_started_at TIMESTAMPTZ,
    attempts_step1 INT NOT NULL DEFAULT 0,
    attempts_step2 INT NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    nft_number INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sponsors (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    chat_ref TEXT NOT NULL,   -- @username или ID канала, используется для get_chat_member
    url TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS nft_gifts (
    number INT PRIMARY KEY CHECK (number BETWEEN 1 AND 6),
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    image_url TEXT
);

CREATE TABLE IF NOT EXISTS moderators (
    user_id BIGINT PRIMARY KEY,
    added_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bans (
    user_id BIGINT PRIMARY KEY,
    reason TEXT,
    banned_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS moderation_queue (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    step INT NOT NULL,
    required_text TEXT NOT NULL,
    photos JSONB NOT NULL,
    group_message_ids JSONB NOT NULL DEFAULT '[]',
    control_message_id BIGINT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_by BIGINT,
    decided_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS task_texts (
    id SERIAL PRIMARY KEY,
    step INT NOT NULL,
    text TEXT NOT NULL
);
"""

DEFAULT_STEP1_TEXTS = [
    "Это просто огонь 🔥",
    "Вау, невероятно!",
    "Класс, беру на заметку",
]
DEFAULT_STEP2_TEXTS = [
    "Топ контент 🔥",
    "Очень круто!",
    "Подписался, жду ещё",
]

pool: asyncpg.Pool | None = None


async def create_pool(dsn: str) -> asyncpg.Pool:
    global pool
    pool = await asyncpg.create_pool(dsn=dsn, statement_cache_size=0)
    return pool


async def init_db():
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA)
        count = await conn.fetchval("SELECT count(*) FROM task_texts")
        if count == 0:
            for t in DEFAULT_STEP1_TEXTS:
                await conn.execute("INSERT INTO task_texts (step, text) VALUES (1, $1)", t)
            for t in DEFAULT_STEP2_TEXTS:
                await conn.execute("INSERT INTO task_texts (step, text) VALUES (2, $1)", t)


# ---------------- USERS ----------------

async def get_user(user_id: int):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)


async def create_user_if_not_exists(user_id: int, username: str | None):
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO users (user_id, username) VALUES ($1, $2)
               ON CONFLICT (user_id) DO UPDATE SET username=$2""",
            user_id, username,
        )


async def set_status(user_id: int, status: str):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET status=$1 WHERE user_id=$2", status, user_id)


async def set_task(user_id: int, status: str, task_text: str):
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE users SET status=$1, task_text=$2, task_photos='[]',
               task_started_at=now() WHERE user_id=$3""",
            status, task_text, user_id,
        )


async def append_task_photo(user_id: int, file_id: str) -> int:
    """Добавляет file_id в task_photos, возвращает новое количество фото."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT task_photos FROM users WHERE user_id=$1", user_id)
        photos = json.loads(row["task_photos"]) if row["task_photos"] else []
        photos.append(file_id)
        await conn.execute(
            "UPDATE users SET task_photos=$1 WHERE user_id=$2",
            json.dumps(photos), user_id,
        )
        return len(photos)


async def get_task_photos(user_id: int) -> list[str]:
    async with pool.acquire() as conn:
        val = await conn.fetchval("SELECT task_photos FROM users WHERE user_id=$1", user_id)
        return json.loads(val) if val else []


async def clear_task_photos(user_id: int):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET task_photos='[]' WHERE user_id=$1", user_id)


async def bump_attempts(user_id: int, step: int) -> int:
    col = "attempts_step1" if step == 1 else "attempts_step2"
    async with pool.acquire() as conn:
        return await conn.fetchval(
            f"UPDATE users SET {col} = {col} + 1 WHERE user_id=$1 RETURNING {col}", user_id
        )


async def reset_attempts(user_id: int, step: int):
    col = "attempts_step1" if step == 1 else "attempts_step2"
    async with pool.acquire() as conn:
        await conn.execute(f"UPDATE users SET {col}=0 WHERE user_id=$1", user_id)


async def lock_user(user_id: int, hours: int):
    until = datetime.now(timezone.utc) + timedelta(hours=hours)
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET status='locked', locked_until=$1 WHERE user_id=$2", until, user_id
        )


async def is_locked(user_id: int) -> bool:
    async with pool.acquire() as conn:
        until = await conn.fetchval("SELECT locked_until FROM users WHERE user_id=$1", user_id)
        if until and until > datetime.now(timezone.utc):
            return True
        return False


async def set_nft_number(user_id: int, number: int):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET nft_number=$1 WHERE user_id=$2", number, user_id)


# ---------------- BANS ----------------

async def ban_user(user_id: int, reason: str | None):
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO bans (user_id, reason) VALUES ($1, $2)
               ON CONFLICT (user_id) DO UPDATE SET reason=$2, banned_at=now()""",
            user_id, reason,
        )


async def unban_user(user_id: int):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM bans WHERE user_id=$1", user_id)


async def is_banned(user_id: int) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT 1 FROM bans WHERE user_id=$1", user_id)
        return row is not None


async def list_bans():
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM bans ORDER BY banned_at DESC")


# ---------------- SPONSORS ----------------

async def add_sponsor(name: str, chat_ref: str, url: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO sponsors (name, chat_ref, url) VALUES ($1, $2, $3)", name, chat_ref, url
        )


async def remove_sponsor(sponsor_id: int):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM sponsors WHERE id=$1", sponsor_id)


async def list_sponsors(active_only: bool = True):
    async with pool.acquire() as conn:
        if active_only:
            return await conn.fetch("SELECT * FROM sponsors WHERE active=TRUE ORDER BY id")
        return await conn.fetch("SELECT * FROM sponsors ORDER BY id")


# ---------------- NFT ----------------

async def upsert_nft(number: int, name: str, description: str, image_url: str | None):
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO nft_gifts (number, name, description, image_url)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (number) DO UPDATE SET name=$2, description=$3, image_url=$4""",
            number, name, description, image_url,
        )


async def remove_nft(number: int):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM nft_gifts WHERE number=$1", number)


async def get_nft(number: int):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM nft_gifts WHERE number=$1", number)


async def list_nft():
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM nft_gifts ORDER BY number")


# ---------------- MODERATORS ----------------

async def add_moderator(user_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO moderators (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id
        )


async def remove_moderator(user_id: int):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM moderators WHERE user_id=$1", user_id)


async def list_moderators():
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM moderators ORDER BY added_at")


async def is_moderator(user_id: int) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT 1 FROM moderators WHERE user_id=$1", user_id)
        return row is not None


# ---------------- MODERATION QUEUE ----------------

async def create_moderation_item(user_id: int, step: int, required_text: str, photos: list[str]) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """INSERT INTO moderation_queue (user_id, step, required_text, photos)
               VALUES ($1, $2, $3, $4) RETURNING id""",
            user_id, step, required_text, json.dumps(photos),
        )


async def set_moderation_messages(item_id: int, group_message_ids: list[int], control_message_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE moderation_queue SET group_message_ids=$1, control_message_id=$2 WHERE id=$3",
            json.dumps(group_message_ids), control_message_id, item_id,
        )


async def get_moderation_item(item_id: int):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM moderation_queue WHERE id=$1", item_id)


async def set_moderation_status(item_id: int, status: str, decided_by: int | None):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE moderation_queue SET status=$1, decided_by=$2, decided_at=now() WHERE id=$3",
            status, decided_by, item_id,
        )


async def get_pending_moderation_older_than(seconds: int):
    async with pool.acquire() as conn:
        return await conn.fetch(
            """SELECT * FROM moderation_queue
               WHERE status='pending' AND created_at < now() - ($1 || ' seconds')::interval""",
            str(seconds),
        )


# ---------------- TASK TEXTS ----------------

async def add_task_text(step: int, text: str):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO task_texts (step, text) VALUES ($1, $2)", step, text)


async def remove_task_text(text_id: int):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM task_texts WHERE id=$1", text_id)


async def list_task_texts(step: int):
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM task_texts WHERE step=$1 ORDER BY id", step)


async def random_task_text(step: int) -> str:
    async with pool.acquire() as conn:
        val = await conn.fetchval(
            "SELECT text FROM task_texts WHERE step=$1 ORDER BY random() LIMIT 1", step
        )
        return val or "Круто!"


# ---------------- STATS ----------------

async def get_stats():
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT count(*) FROM users")
        by_status = await conn.fetch(
            "SELECT status, count(*) AS cnt FROM users GROUP BY status ORDER BY cnt DESC"
        )
        approved = await conn.fetchval(
            "SELECT count(*) FROM moderation_queue WHERE status='approved'"
        )
        rejected = await conn.fetchval(
            "SELECT count(*) FROM moderation_queue WHERE status='rejected'"
        )
        top = await conn.fetch(
            """SELECT user_id, username,
                      (attempts_step1 + attempts_step2) AS attempts,
                      status
               FROM users
               ORDER BY (CASE status
                   WHEN 'gift_given' THEN 6
                   WHEN 'awaiting_manager' THEN 5
                   WHEN 'step3_sponsors' THEN 4
                   WHEN 'step2_pending_review' THEN 3
                   WHEN 'step2_pending_task' THEN 2
                   ELSE 1 END) DESC
               LIMIT 10"""
        )
        return {
            "total": total,
            "by_status": by_status,
            "approved": approved,
            "rejected": rejected,
            "top": top,
        }


async def all_user_ids(filter_status: str | None = None):
    async with pool.acquire() as conn:
        if filter_status:
            rows = await conn.fetch("SELECT user_id FROM users WHERE status=$1", filter_status)
        else:
            rows = await conn.fetch("SELECT user_id FROM users")
        return [r["user_id"] for r in rows]
