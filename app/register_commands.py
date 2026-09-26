"""
Run this script ONCE to register slash commands with Discord.
Usage: python -m app.register_commands
"""
import os
import httpx

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_APP_ID = os.getenv("DISCORD_APP_ID")

COMMANDS = [
    {
        "name": "ask",
        "description": "Ask Hermes anything about your schedule, studies, or goals",
        "type": 1,
        "options": [
            {
                "name": "question",
                "description": "Your question for Hermes",
                "type": 3,  # STRING type
                "required": True
            }
        ]
    },
    {
        "name": "schedule",
        "description": "View or manage your university schedule",
        "type": 1,
    },
    {
        "name": "goal",
        "description": "Check your competitive exam preparation progress",
        "type": 1,
    },
    {
        "name": "help",
        "description": "See what Hermes can do for you",
        "type": 1,
    }
]

def register():
    if not DISCORD_BOT_TOKEN or not DISCORD_APP_ID:
        print("ERROR: Set DISCORD_BOT_TOKEN and DISCORD_APP_ID environment variables first!")
        return

    url = f"https://discord.com/api/v10/applications/{DISCORD_APP_ID}/commands"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    for cmd in COMMANDS:
        response = httpx.put(url, json=COMMANDS, headers=headers)
        if response.status_code == 200:
            print(f"Successfully registered all commands!")
            break
        else:
            print(f"Failed: {response.status_code} - {response.text}")
            break

if __name__ == "__main__":
    register()
