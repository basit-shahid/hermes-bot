"""
memory.py — Memory Engine for Hermes.
Handles conversation history, user facts, and schedule CRUD operations.
"""
import logging
from datetime import date, datetime
from typing import Optional

from app.db import get_db

logger = logging.getLogger(__name__)

# Max messages to keep in short-term conversation buffer
SHORT_TERM_LIMIT = 15


# ─────────────────────────────────────────────────────────────
# User / Identity Management
# ─────────────────────────────────────────────────────────────

async def get_or_create_user(user_id: str, name: str = "User") -> dict:
    """Returns user record, creating it if it does not yet exist."""
    db = await get_db()
    async with db:
        cur = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cur.fetchone()
        if row:
            return dict(row)

        # Determine which field to set from the prefix  (wa: or dc:)
        whatsapp_number = user_id.replace("wa:", "") if user_id.startswith("wa:") else None
        discord_id      = user_id.replace("dc:", "") if user_id.startswith("dc:") else None

        await db.execute(
            "INSERT INTO users (id, name, whatsapp_number, discord_id) VALUES (?, ?, ?, ?)",
            (user_id, name, whatsapp_number, discord_id),
        )
        await db.commit()
        logger.info(f"Created new user: {user_id}")
        return {"id": user_id, "name": name}


async def set_user_name(user_id: str, name: str):
    """Update the display name for a user."""
    db = await get_db()
    async with db:
        await db.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
        await db.commit()


# ─────────────────────────────────────────────────────────────
# Short-Term Conversation Memory
# ─────────────────────────────────────────────────────────────

async def save_message(user_id: str, role: str, content: str):
    """Persist one message turn to the conversation history table."""
    db = await get_db()
    async with db:
        await db.execute(
            "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )
        await db.commit()


async def get_recent_history(user_id: str) -> list[dict]:
    """Return the last SHORT_TERM_LIMIT messages for the given user."""
    db = await get_db()
    async with db:
        cur = await db.execute(
            """
            SELECT role, content FROM (
                SELECT role, content, created_at
                FROM conversations
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ) ORDER BY created_at ASC
            """,
            (user_id, SHORT_TERM_LIMIT),
        )
        rows = await cur.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]


async def clear_history(user_id: str):
    """Wipe all conversation history for a user (fresh start)."""
    db = await get_db()
    async with db:
        await db.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        await db.commit()


# ─────────────────────────────────────────────────────────────
# Long-Term Fact Memory
# ─────────────────────────────────────────────────────────────

async def save_fact(user_id: str, fact: str, category: str = "general"):
    """Persist a semantic fact about the user."""
    db = await get_db()
    async with db:
        await db.execute(
            "INSERT INTO user_facts (user_id, fact, category) VALUES (?, ?, ?)",
            (user_id, fact, category),
        )
        await db.commit()
    logger.info(f"Saved fact for {user_id}: {fact}")


async def get_all_facts(user_id: str) -> list[str]:
    """Retrieve all saved facts for a user to inject into system prompt."""
    db = await get_db()
    async with db:
        cur = await db.execute(
            "SELECT fact FROM user_facts WHERE user_id = ? ORDER BY created_at DESC LIMIT 30",
            (user_id,),
        )
        rows = await cur.fetchall()
        return [r["fact"] for r in rows]


async def delete_fact(user_id: str, fact_id: int):
    """Remove a specific fact by its ID."""
    db = await get_db()
    async with db:
        await db.execute("DELETE FROM user_facts WHERE id = ? AND user_id = ?", (fact_id, user_id))
        await db.commit()


# ─────────────────────────────────────────────────────────────
# Schedule / Task CRUD
# ─────────────────────────────────────────────────────────────

async def add_schedule_event(
    user_id: str,
    title: str,
    event_date: str,
    category: str = "task",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    """Insert a new schedule item. Returns the new row ID."""
    db = await get_db()
    async with db:
        cur = await db.execute(
            """
            INSERT INTO schedule_items
                (user_id, title, category, date, start_time, end_time, location, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, title, category, event_date, start_time, end_time, location, notes),
        )
        await db.commit()
        return cur.lastrowid


async def get_schedule_for_date(user_id: str, event_date: str) -> list[dict]:
    """Return all schedule items for a specific date, sorted by start time."""
    db = await get_db()
    async with db:
        cur = await db.execute(
            """
            SELECT id, title, category, date, start_time, end_time, location, notes, status
            FROM schedule_items
            WHERE user_id = ? AND date = ?
            ORDER BY start_time ASC NULLS LAST
            """,
            (user_id, event_date),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_upcoming_schedule(user_id: str, days: int = 7) -> list[dict]:
    """Return schedule items for the next N days."""
    from datetime import timedelta
    today = date.today().isoformat()
    end   = (date.today() + timedelta(days=days)).isoformat()
    db = await get_db()
    async with db:
        cur = await db.execute(
            """
            SELECT id, title, category, date, start_time, end_time, status
            FROM schedule_items
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC, start_time ASC NULLS LAST
            """,
            (user_id, today, end),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def complete_schedule_item(user_id: str, item_id: int) -> bool:
    """Mark a schedule item as completed. Returns True if a row was affected."""
    db = await get_db()
    async with db:
        cur = await db.execute(
            "UPDATE schedule_items SET status = 'completed' WHERE id = ? AND user_id = ?",
            (item_id, user_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_schedule_item(user_id: str, item_id: int) -> bool:
    """Delete a schedule item. Returns True if a row was affected."""
    db = await get_db()
    async with db:
        cur = await db.execute(
            "DELETE FROM schedule_items WHERE id = ? AND user_id = ?",
            (item_id, user_id),
        )
        await db.commit()
        return cur.rowcount > 0


# ─────────────────────────────────────────────────────────────
# Memory Context Builder (used inside system prompt)
# ─────────────────────────────────────────────────────────────

async def build_memory_context(user_id: str) -> str:
    """Build a rich context string from user facts + today's schedule."""
    today = date.today().isoformat()
    facts    = await get_all_facts(user_id)
    schedule = await get_schedule_for_date(user_id, today)

    context_parts = []

    if facts:
        facts_block = "\n".join(f"- {f}" for f in facts)
        context_parts.append(f"## About The User (Long-Term Memory)\n{facts_block}")

    if schedule:
        lines = []
        for s in schedule:
            time_str = f"{s['start_time']}" if s["start_time"] else "anytime"
            if s.get("end_time"):
                time_str += f"–{s['end_time']}"
            status_icon = "✅" if s["status"] == "completed" else "⏳"
            lines.append(f"  {status_icon} [{s['id']}] {time_str} — {s['title']} ({s['category']})")
        schedule_block = "\n".join(lines)
        context_parts.append(f"## Today's Schedule ({today})\n{schedule_block}")
    else:
        context_parts.append(f"## Today's Schedule ({today})\n  - No events scheduled yet.")

    return "\n\n".join(context_parts)
