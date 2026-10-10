"""
db.py — PostgreSQL database initializer for Hermes using asyncpg.
Uses a connection pool for efficient async access across all modules.
"""
import logging
import os

import asyncpg

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Global connection pool (initialized once on startup)
_pool: asyncpg.Pool | None = None


async def init_db():
    """Create connection pool and initialize all tables."""
    global _pool

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is not set!")

    logger.info("Connecting to PostgreSQL database...")
    _pool = await asyncpg.create_pool(
        dsn=DATABASE_URL,
        min_size=1,
        max_size=5,
        command_timeout=30,
    )
    logger.info("✅ PostgreSQL connection pool created.")

    async with _pool.acquire() as conn:
        await conn.execute("""
            -- ─────────────────────────────────────────────
            -- Users: unified identity (WhatsApp + Discord)
            -- ─────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS users (
                id              TEXT PRIMARY KEY,
                name            TEXT DEFAULT 'User',
                timezone        TEXT DEFAULT 'Asia/Karachi',
                whatsapp_number TEXT UNIQUE,
                discord_id      TEXT UNIQUE,
                created_at      TIMESTAMPTZ DEFAULT NOW()
            );

            -- ─────────────────────────────────────────────
            -- Schedule Items: lectures, tasks, gym, etc.
            -- ─────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS schedule_items (
                id          SERIAL PRIMARY KEY,
                user_id     TEXT NOT NULL REFERENCES users(id),
                title       TEXT NOT NULL,
                category    TEXT DEFAULT 'task',
                date        TEXT NOT NULL,
                start_time  TEXT,
                end_time    TEXT,
                location    TEXT,
                notes       TEXT,
                status      TEXT DEFAULT 'pending',
                created_at  TIMESTAMPTZ DEFAULT NOW()
            );

            -- ─────────────────────────────────────────────
            -- User Facts: long-term semantic memory
            -- ─────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS user_facts (
                id         SERIAL PRIMARY KEY,
                user_id    TEXT NOT NULL REFERENCES users(id),
                fact       TEXT NOT NULL,
                category   TEXT DEFAULT 'general',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            -- ─────────────────────────────────────────────
            -- Conversation History: short-term memory buffer
            -- ─────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS conversations (
                id         SERIAL PRIMARY KEY,
                user_id    TEXT NOT NULL REFERENCES users(id),
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        logger.info("✅ All database tables verified/created.")


async def get_pool() -> asyncpg.Pool:
    """Return the active connection pool. Must call init_db() first."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Call init_db() first.")
    return _pool
