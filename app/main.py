import asyncio
import logging
import os
import threading

import discord
from discord import app_commands
from fastapi import FastAPI
from openai import AsyncOpenAI

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
ROUTEME_API_KEY = os.getenv("ROUTEME_API_KEY")

# Initialize RoutesMe Client
# We use the AsyncOpenAI client since discord.py is fully async
ai_client = AsyncOpenAI(
    base_url="https://routesme.online/v1",
    api_key=ROUTEME_API_KEY,
)
# Free RoutesMe GLM model
AI_MODEL = "GLM5.3-flash" 

SYSTEM_PROMPT = "You are Hermes, a helpful, intelligent, and friendly AI assistant for a university student. You help with schedules, goals, and general knowledge. Keep responses concise and use Discord markdown where appropriate."

async def generate_response(user_input: str) -> str:
    """Helper function to call RoutesMe AI."""
    if not ROUTEME_API_KEY:
        return "⚠️ Hermes AI Engine is not configured yet. (Missing ROUTEME_API_KEY in Render dashboard)"
    
    try:
        completion = await ai_client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"AI Generation Error: {e}")
        return "⚠️ Sorry, my AI brain encountered an error answering that."



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

        # Show typing indicator while generating
        async with message.channel.typing():
            ai_response = await generate_response(user_text)
            
        await message.reply(ai_response)


# ──────────────────────────────────────────────
# Slash Commands
# ──────────────────────────────────────────────
@tree.command(name="ask", description="Ask Hermes anything about your schedule, studies, or goals")
@app_commands.describe(question="Your question for Hermes")
async def ask_command(interaction: discord.Interaction, question: str):
    # Acknowledge the command immediately to prevent Discord's 3-second timeout
    await interaction.response.defer(thinking=True)
    
    ai_response = await generate_response(question)
    
    await interaction.followup.send(f"**You asked:** {question}\n\n{ai_response}")


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
