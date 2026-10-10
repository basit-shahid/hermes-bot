"""
tools.py — Tool definitions and executor for Hermes function calling.

The AI model (via OpenRouter) can call these tools to read/write
schedule data and memory. Each tool has a JSON Schema definition
(sent to the model) and a matching Python executor function.
"""
import json
import logging
from datetime import date
from typing import Any

from app import memory

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Tool Schemas (sent to the LLM as tools=[...])
# ─────────────────────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_schedule",
            "description": (
                "Retrieve the schedule for a specific date. "
                "Use 'today' to get today's schedule or a date like '2026-10-15'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date to get the schedule for. Use 'today' or 'YYYY-MM-DD' format.",
                    }
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_schedule",
            "description": "Get all upcoming schedule items for the next few days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look ahead (default 7).",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_schedule_event",
            "description": (
                "Add a new event, class, study session, gym session, or task to the schedule. "
                "Always confirm the date, start time, and title before calling this."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title":      {"type": "string", "description": "Event name, e.g. 'AI Lab', 'Gym Session'"},
                    "date":       {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "category":   {"type": "string", "description": "One of: lecture, study, exam, gym, task, personal"},
                    "start_time": {"type": "string", "description": "Start time in HH:MM (24-hour), e.g. '14:00'"},
                    "end_time":   {"type": "string", "description": "End time in HH:MM (24-hour), e.g. '16:00'"},
                    "location":   {"type": "string", "description": "Optional room or online platform"},
                    "notes":      {"type": "string", "description": "Optional extra notes"},
                },
                "required": ["title", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_schedule_item",
            "description": "Mark a schedule item as completed using its ID number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "The ID of the schedule item (shown in brackets when listing schedule).",
                    }
                },
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_schedule_item",
            "description": "Delete/remove a schedule item using its ID number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "The ID of the schedule item to delete.",
                    }
                },
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_user_fact",
            "description": (
                "Save an important fact about the user to long-term memory. "
                "Use this for goals, preferences, exam dates, and personal context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "The fact to remember, e.g. 'User has GRE exam in December 2026'",
                    },
                    "category": {
                        "type": "string",
                        "description": "Category: goal, habit, preference, academic, personal",
                    },
                },
                "required": ["fact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_conversation",
            "description": "Clear conversation history to start fresh. Use only when user explicitly asks to reset or start over.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


# ─────────────────────────────────────────────────────────────
# Tool Executor
# ─────────────────────────────────────────────────────────────

async def execute_tool(user_id: str, tool_name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool call from the LLM and return a result string."""
    logger.info(f"🔧 Tool call: {tool_name}({arguments}) for user {user_id}")

    try:
        if tool_name == "get_schedule":
            raw_date = arguments.get("date", "today")
            target_date = date.today().isoformat() if raw_date == "today" else raw_date
            items = await memory.get_schedule_for_date(user_id, target_date)
            if not items:
                return f"No schedule items found for {target_date}."
            lines = []
            for s in items:
                time_str = s["start_time"] or "Anytime"
                if s.get("end_time"):
                    time_str += f"–{s['end_time']}"
                status_icon = "✅" if s["status"] == "completed" else "⏳"
                lines.append(f"{status_icon} [{s['id']}] {time_str} — {s['title']} ({s['category']})")
            return f"Schedule for {target_date}:\n" + "\n".join(lines)

        elif tool_name == "get_upcoming_schedule":
            days  = int(arguments.get("days", 7))
            items = await memory.get_upcoming_schedule(user_id, days)
            if not items:
                return f"No upcoming events in the next {days} days."
            lines = []
            for s in items:
                time_str = s["start_time"] or "Anytime"
                if s.get("end_time"):
                    time_str += f"–{s['end_time']}"
                status_icon = "✅" if s["status"] == "completed" else "⏳"
                lines.append(f"{status_icon} [{s['id']}] {s['date']} {time_str} — {s['title']} ({s['category']})")
            return f"Upcoming schedule ({days} days):\n" + "\n".join(lines)

        elif tool_name == "add_schedule_event":
            item_id = await memory.add_schedule_event(
                user_id=user_id,
                title=arguments["title"],
                event_date=arguments["date"],
                category=arguments.get("category", "task"),
                start_time=arguments.get("start_time"),
                end_time=arguments.get("end_time"),
                location=arguments.get("location"),
                notes=arguments.get("notes"),
            )
            return f"✅ Event added with ID [{item_id}]: '{arguments['title']}' on {arguments['date']}."

        elif tool_name == "complete_schedule_item":
            ok = await memory.complete_schedule_item(user_id, int(arguments["item_id"]))
            return "✅ Marked as completed!" if ok else "❌ Event not found."

        elif tool_name == "delete_schedule_item":
            ok = await memory.delete_schedule_item(user_id, int(arguments["item_id"]))
            return "🗑️ Event deleted." if ok else "❌ Event not found."

        elif tool_name == "save_user_fact":
            await memory.save_fact(user_id, arguments["fact"], arguments.get("category", "general"))
            return f"✅ Remembered: \"{arguments['fact']}\""

        elif tool_name == "clear_conversation":
            await memory.clear_history(user_id)
            return "🔄 Conversation history cleared."

        else:
            return f"Unknown tool: {tool_name}"

    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)
        return f"Tool error: {str(e)}"


# ─────────────────────────────────────────────────────────────
# Agentic Loop Runner
# ─────────────────────────────────────────────────────────────

async def run_tool_calls(ai_client, user_id: str, messages: list[dict], model: str) -> str:
    """
    Run a multi-step agentic loop:
    1. Send messages to LLM with tool definitions.
    2. If LLM requests tool calls, execute them and feed results back.
    3. Repeat until LLM returns a final text response (max 5 iterations).
    """
    current_messages = list(messages)

    for iteration in range(5):  # Safety limit on tool call loops
        response = await ai_client.chat.completions.create(
            model=model,
            messages=current_messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            timeout=20.0,
        )

        choice = response.choices[0]

        # If the model returned a direct text response, we are done
        if choice.finish_reason == "stop" or not choice.message.tool_calls:
            return choice.message.content or "I'm sorry, I couldn't generate a response."

        # Process all tool calls in this round
        tool_calls = choice.message.tool_calls
        current_messages.append(choice.message)  # Add assistant turn with tool calls

        for tc in tool_calls:
            args = json.loads(tc.function.arguments)
            result = await execute_tool(user_id, tc.function.name, args)
            logger.info(f"Tool result for {tc.function.name}: {result[:100]}")

            current_messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    # If we hit the loop limit, get a final answer without tools
    response = await ai_client.chat.completions.create(
        model=model,
        messages=current_messages,
        timeout=20.0,
    )
    return response.choices[0].message.content or "I ran into an issue. Please try again."
