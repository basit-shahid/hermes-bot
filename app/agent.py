"""
agent.py — Core Hermes Agent Processing Engine.
Builds context-rich system prompts from persistent memory and
runs the agentic tool-calling loop for both Discord and WhatsApp.
"""
import logging
import os
from datetime import date

from openai import AsyncOpenAI

from app import memory
from app.tools import run_tool_calls, TOOL_SCHEMAS

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

ai_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://render.com",
        "X-Title": "Hermes Bot",
    },
)

# Models tried in order until one succeeds
AI_MODELS = [
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "openrouter/auto",
]

BASE_SYSTEM_PROMPT = """\
You are Hermes, a highly intelligent and organized personal AI assistant for a university student.

## Your Core Capabilities:
- 📅 **Schedule Management**: Add, view, update, and complete schedule items (lectures, exams, study sessions, gym, tasks).
- 🧠 **Persistent Memory**: You remember the user's goals, habits, and preferences across conversations.
- 🎯 **Daily Planning**: Help the user plan their day, prioritize tasks, and stay on track.
- 📚 **Academic Support**: Answer questions about studies, explain concepts, and help with exam prep.
- 💬 **Natural Conversation**: Be warm, friendly, and concise. Use bullet points for clarity.

## Important Rules:
1. When a user adds or mentions a schedule item, ALWAYS use the `add_schedule_event` tool to save it — never just acknowledge without saving.
2. When answering "what's my schedule today?" or similar, ALWAYS call `get_schedule` first.
3. When the user shares a new fact about themselves (goal, preference, habit), use `save_user_fact` to remember it.
4. Dates should be converted to YYYY-MM-DD format. When user says "tomorrow", compute from today's date.
5. Time should always be in HH:MM 24-hour format when saving.
6. Keep responses concise and well-formatted. Use Discord/WhatsApp markdown where it helps.
7. Never make up schedule data — always query the database tools.

Today's date is: {today}
"""


async def build_system_prompt(user_id: str, user_name: str) -> str:
    """Build a personalized system prompt with live memory context."""
    today = date.today().isoformat()
    base = BASE_SYSTEM_PROMPT.format(today=today)

    memory_context = await memory.build_memory_context(user_id)
    if memory_context:
        return f"{base}\n\n## Live Memory Context\n{memory_context}"
    return base


async def hermes_agent_process(user_id: str, user_message: str, user_name: str = "User") -> str:
    """
    Main entry point for processing any user message (Discord or WhatsApp).
    1. Ensures user exists in the database.
    2. Loads conversation history (short-term memory).
    3. Builds a personalized system prompt (with long-term memory + today's schedule).
    4. Runs the agentic tool-calling loop.
    5. Saves both the user message and AI response to conversation history.
    """
    if not OPENROUTER_API_KEY:
        return "⚠️ Hermes AI Engine is not configured. (Missing OPENROUTER_API_KEY)"

    # 1. Ensure user profile exists
    await memory.get_or_create_user(user_id, name=user_name)

    # 2. Load conversation history (short-term memory)
    history = await memory.get_recent_history(user_id)

    # 3. Build context-rich system prompt
    system_prompt = await build_system_prompt(user_id, user_name)

    # 4. Assemble full message list for the LLM
    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message},
    ]

    # 5. Try each model with agentic tool loop
    last_error = None
    for model in AI_MODELS:
        try:
            logger.info(f"Running Hermes agent with model: {model}")
            response_text = await run_tool_calls(ai_client, user_id, messages, model)

            # 6. Persist both turns to conversation history
            await memory.save_message(user_id, "user", user_message)
            await memory.save_message(user_id, "assistant", response_text)

            return response_text

        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            last_error = e

    logger.error(f"All AI models failed. Last error: {last_error}")
    return f"⚠️ Sorry, my AI brain encountered an error.\n*Details: {last_error}*"
