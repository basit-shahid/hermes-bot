import asyncio
import logging
import os
import threading

import discord
from discord import app_commands
from fastapi import FastAPI

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Discord Gateway Bot
# ──────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True  # Requires "Message Content Intent" in Developer Portal

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


@bot.event
async def on_ready():
    """Called when the bot connects to the Gateway."""
    logger.info(f"✅ Hermes is online as {bot.user} (ID: {bot.user.id})")
    # Sync slash commands with Discord
    try:
        synced = await tree.sync()
        logger.info(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        logger.error(f"❌ Failed to sync commands: {e}")


@bot.event
async def on_message(message: discord.Message):
    """Respond to regular messages (mentions and DMs)."""
    # Don't reply to ourselves
    if message.author == bot.user:
        return

    # Respond to DMs
    is_dm = isinstance(message.channel, discord.DMChannel)
    # Respond to mentions
    is_mentioned = bot.user in message.mentions

    if is_dm or is_mentioned:
        # Strip the mention from the message text
        user_text = message.content
        if is_mentioned:
            user_text = user_text.replace(f"<@{bot.user.id}>", "").strip()

        if not user_text:
            user_text = "hello"

        response = (
            f"🏛️ **Hermes heard you!**\n\n"
            f"You said: *{user_text}*\n\n"
            f"⚙️ AI Engine is not connected yet (Phase 3). "
            f"But the pipeline is working end-to-end!\n\n"
            f"💡 Try my slash commands: `/ask`, `/schedule`, `/goal`, `/help`"
        )
        await message.reply(response)


# ──────────────────────────────────────────────
# Slash Commands
# ──────────────────────────────────────────────
@tree.command(name="ask", description="Ask Hermes anything about your schedule, studies, or goals")
@app_commands.describe(question="Your question for Hermes")
async def ask_command(interaction: discord.Interaction, question: str):
    response = (
        f"🏛️ **Hermes heard you!**\n\n"
        f"You asked: *{question}*\n\n"
        f"⚙️ AI Engine is not connected yet (Phase 3). "
        f"But the pipeline is working end-to-end!"
    )
    await interaction.response.send_message(response)


@tree.command(name="schedule", description="View or manage your university schedule")
async def schedule_command(interaction: discord.Interaction):
    response = (
        "📅 **Schedule Service**\n\n"
        "This will show your university lectures and deadlines.\n"
        "🔧 Coming in Phase 2!"
    )
    await interaction.response.send_message(response)


@tree.command(name="goal", description="Check your competitive exam preparation progress")
async def goal_command(interaction: discord.Interaction):
    response = (
        "🎯 **Goal Tracker**\n\n"
        "This will track your competitive exam preparation progress.\n"
        "🔧 Coming in Phase 2!"
    )
    await interaction.response.send_message(response)


@tree.command(name="help", description="See what Hermes can do for you")
async def help_command(interaction: discord.Interaction):
    response = (
        "🏛️ **Hermes — Your Personal AI Assistant**\n\n"
        "Available commands:\n"
        "• `/ask <question>` — Ask me anything about your studies\n"
        "• `/schedule` — View your university schedule\n"
        "• `/goal` — Check your exam preparation progress\n"
        "• `/help` — Show this message\n\n"
        "💬 You can also **mention me** or **DM me** directly!\n\n"
        "More features coming soon! 🚀"
    )
    await interaction.response.send_message(response)


# ──────────────────────────────────────────────
# FastAPI Health Check (keeps Render happy)
# ──────────────────────────────────────────────
app = FastAPI(title="Hermes Webhook Service")


@app.get("/")
async def root():
    bot_status = "connected" if bot.is_ready() else "connecting"
    return {
        "message": "Hermes Webhook Service is running",
        "bot_status": bot_status,
        "version": "2.0.0-gateway"
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "bot_ready": bot.is_ready()}


# ──────────────────────────────────────────────
# Start Discord bot alongside FastAPI
# ──────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Start the Discord bot when FastAPI starts."""
    if not BOT_TOKEN:
        logger.error("❌ DISCORD_BOT_TOKEN not set! Bot will not start.")
        return
    # Run discord bot in the background
    asyncio.create_task(bot.start(BOT_TOKEN))
    logger.info("🚀 Discord bot starting in background...")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanly close the Discord bot."""
    if bot.is_ready():
        await bot.close()
        logger.info("🛑 Discord bot disconnected.")
