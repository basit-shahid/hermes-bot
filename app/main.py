"""
main.py — Hermes Bot: FastAPI application entry point.

Architecture:
- FastAPI serves two roles:
  1. Discord bot running as a background gateway task
  2. WhatsApp Cloud API webhook receiver
- Persistent memory backed by SQLite (aiosqlite)
- Agentic tool-calling loop for schedule and memory management
"""
import asyncio
import logging
import os

import discord
from discord import app_commands
from fastapi import FastAPI

from app.agent import hermes_agent_process
from app.db import init_db
from app.whatsapp import router as whatsapp_router
from app import memory

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Discord Gateway Bot
# ──────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True  # Requires "Message Content Intent" in Developer Portal

bot  = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


@bot.event
async def on_ready():
    logger.info(f"✅ Hermes is online as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await tree.sync()
        logger.info(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        logger.error(f"❌ Failed to sync commands: {e}")


@bot.event
async def on_message(message: discord.Message):
    """Respond to DMs and @mentions with full agent + memory."""
    if message.author == bot.user:
        return

    is_dm       = isinstance(message.channel, discord.DMChannel)
    is_mentioned = bot.user in message.mentions

    if not (is_dm or is_mentioned):
        return

    user_text = message.content
    if is_mentioned:
        user_text = (
            user_text
            .replace(f"<@{bot.user.id}>", "")
            .replace(f"<@!{bot.user.id}>", "")
            .strip()
        )

    if not user_text:
        user_text = "hello"

    user_id   = f"dc:{message.author.id}"
    user_name = message.author.display_name

    async with message.channel.typing():
        reply = await hermes_agent_process(
            user_id=user_id,
            user_name=user_name,
            user_message=user_text,
        )

    # Discord has a 2000-char message limit — chunk if needed
    chunks = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
    for i, chunk in enumerate(chunks):
        if i == 0:
            await message.reply(chunk)
        else:
            await message.channel.send(chunk)


# ──────────────────────────────────────────────
# Slash Commands
# ──────────────────────────────────────────────

@tree.command(name="ask", description="Ask Hermes anything about your schedule, studies, or goals")
@app_commands.describe(question="Your question for Hermes")
async def ask_command(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)
    user_id = f"dc:{interaction.user.id}"
    reply   = await hermes_agent_process(
        user_id=user_id,
        user_name=interaction.user.display_name,
        user_message=question,
    )
    # Prefix the question for context in the channel
    full   = f"**You asked:** {question}\n\n{reply}"
    chunks = [full[i:i+1900] for i in range(0, len(full), 1900)]
    await interaction.followup.send(chunks[0])
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk)


@tree.command(name="schedule", description="View your schedule for today")
async def schedule_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    user_id = f"dc:{interaction.user.id}"
    reply   = await hermes_agent_process(
        user_id=user_id,
        user_name=interaction.user.display_name,
        user_message="Show me my schedule for today.",
    )
    await interaction.followup.send(reply)


@tree.command(name="add", description="Add an event to your schedule")
@app_commands.describe(event="Describe the event, e.g. 'AI lab tomorrow 2pm to 4pm'")
async def add_command(interaction: discord.Interaction, event: str):
    await interaction.response.defer(thinking=True)
    user_id = f"dc:{interaction.user.id}"
    reply   = await hermes_agent_process(
        user_id=user_id,
        user_name=interaction.user.display_name,
        user_message=f"Add this to my schedule: {event}",
    )
    await interaction.followup.send(reply)


@tree.command(name="memory", description="See what Hermes remembers about you")
async def memory_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    user_id = f"dc:{interaction.user.id}"
    facts   = await memory.get_all_facts(user_id)
    if facts:
        facts_text = "\n".join(f"• {f}" for f in facts)
        reply = f"🧠 **What I remember about you:**\n{facts_text}"
    else:
        reply = "🧠 I haven't saved any facts about you yet. Tell me about your goals, habits, or schedule!"
    await interaction.followup.send(reply)


@tree.command(name="reset", description="Clear Hermes' conversation history (fresh start)")
async def reset_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    user_id = f"dc:{interaction.user.id}"
    await memory.clear_history(user_id)
    await interaction.followup.send("🔄 Conversation history cleared! Let's start fresh.")


@tree.command(name="goal", description="Check your competitive exam preparation progress")
async def goal_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    user_id = f"dc:{interaction.user.id}"
    reply   = await hermes_agent_process(
        user_id=user_id,
        user_name=interaction.user.display_name,
        user_message="What are my current goals and upcoming exam preparation status?",
    )
    await interaction.followup.send(reply)


@tree.command(name="help", description="See what Hermes can do for you")
async def help_command(interaction: discord.Interaction):
    response = (
        "🏛️ **Hermes — Your Personal AI Assistant**\n\n"
        "**Slash Commands:**\n"
        "• `/ask <question>` — Ask me anything (studies, advice, plans)\n"
        "• `/add <event>` — Add a lecture, study block, or task to your schedule\n"
        "• `/schedule` — View today's full schedule\n"
        "• `/goal` — Check your exam preparation goals\n"
        "• `/memory` — See what I remember about you\n"
        "• `/reset` — Clear conversation history\n"
        "• `/help` — Show this message\n\n"
        "💬 You can also **mention me** or **DM me** directly in natural language!\n\n"
        "📱 **WhatsApp:** Contact me on WhatsApp to manage your schedule on the go!\n"
        "🧠 **Persistent Memory:** I remember your schedule, goals, and habits across sessions."
    )
    await interaction.response.send_message(response)


# ──────────────────────────────────────────────
# FastAPI Application
# ──────────────────────────────────────────────
app = FastAPI(title="Hermes — Personal AI Assistant", version="3.0.0")

# Mount WhatsApp webhook routes
app.include_router(whatsapp_router)


@app.get("/")
async def root():
    bot_status = "connected" if bot.is_ready() else "connecting"
    return {
        "message": "Hermes Personal AI Assistant",
        "bot_status": bot_status,
        "version": "3.0.0",
        "features": ["discord", "whatsapp", "persistent_memory", "schedule_tracking"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "bot_ready": bot.is_ready()}


# ──────────────────────────────────────────────
# Startup / Shutdown
# ──────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Initialize database and start Discord bot."""
    # Initialize SQLite tables
    await init_db()

    # Start Discord bot
    if not BOT_TOKEN:
        logger.error("❌ DISCORD_BOT_TOKEN not set! Discord bot will not start.")
        return
    asyncio.create_task(bot.start(BOT_TOKEN))
    logger.info("🚀 Discord bot starting in background...")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanly close the Discord bot."""
    if bot.is_ready():
        await bot.close()
        logger.info("🛑 Discord bot disconnected.")
