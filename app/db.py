"""
db.py — SQLite database initializer for Hermes.
Creates all necessary tables on startup using aiosqlite.
"""
import aiosqlite
import logging
import os

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("HERMES_DB_PATH", "/data/hermes.db")


async def get_db() -> aiosqlite.Connection:
    """Open and return an async SQLite connection with row_factory set."""
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db():
    """Create all tables if they do not exist."""
    logger.info(f"Initializing Hermes database at: {DB_PATH}")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            -- ─────────────────────────────────────────────
            -- Users: unified identity (WhatsApp + Discord)
            -- ─────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS users (
                id              TEXT PRIMARY KEY,
                name            TEXT DEFAULT 'User',
                timezone        TEXT DEFAULT 'Asia/Karachi',
                whatsapp_number TEXT UNIQUE,
                discord_id      TEXT UNIQUE,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- ─────────────────────────────────────────────
            -- Schedule Items: lectures, tasks, gym, etc.
            -- ─────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS schedule_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                title       TEXT NOT NULL,
                category    TEXT DEFAULT 'task',
                date        TEXT NOT NULL,
                start_time  TEXT,
                end_time    TEXT,
                location    TEXT,
                notes       TEXT,
                status      TEXT DEFAULT 'pending',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            -- ─────────────────────────────────────────────
            -- User Facts: long-term memory profile
            -- ─────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS user_facts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL,
                fact       TEXT NOT NULL,
                category   TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            -- ─────────────────────────────────────────────
            -- Conversation History: short-term memory buffer
            -- ─────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS conversations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        """)
        await db.commit()
        logger.info("✅ Database tables initialized.")
