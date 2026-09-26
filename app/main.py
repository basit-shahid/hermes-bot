from fastapi import FastAPI, Request, HTTPException
import json
import logging
import os
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Hermes Webhook Service")

# ──────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "Hermes Webhook Service is running"}

# ──────────────────────────────────────────────
# Telegram Webhook
# ──────────────────────────────────────────────
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Received Telegram payload: {json.dumps(data)}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "detail": str(e)}

# ──────────────────────────────────────────────
# WhatsApp Webhook
# ──────────────────────────────────────────────
@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Received WhatsApp payload: {json.dumps(data)}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "detail": str(e)}

# ──────────────────────────────────────────────
# Discord Webhook (Interactions Endpoint)
# ──────────────────────────────────────────────
@app.post("/webhook/discord")
async def discord_webhook(request: Request):
    # --- Step 1: Verify Discord's cryptographic signature ---
    public_key = os.getenv("DISCORD_PUBLIC_KEY")
    if not public_key:
        raise HTTPException(status_code=500, detail="Missing DISCORD_PUBLIC_KEY")

    try:
        verify_key = VerifyKey(bytes.fromhex(public_key))
        signature = request.headers.get("X-Signature-Ed25519")
        timestamp = request.headers.get("X-Signature-Timestamp")
        body = await request.body()
        verify_key.verify(f"{timestamp}".encode() + body, bytes.fromhex(signature))
    except (BadSignatureError, Exception) as e:
        logger.error(f"Verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid request signature")

    # --- Step 2: Parse the interaction ---
    data = json.loads(body)
    interaction_type = data.get("type")

    # Type 1: Discord Ping (required for saving the Interactions URL)
    if interaction_type == 1:
        return {"type": 1}

    # Type 2: Application Command (Slash Commands)
    if interaction_type == 2:
        command_name = data.get("data", {}).get("name", "")
        options = data.get("data", {}).get("options", [])

        response_text = handle_command(command_name, options)
        return {
            "type": 4,
            "data": {"content": response_text}
        }

    return {"type": 4, "data": {"content": "I didn't understand that interaction."}}


def handle_command(command_name: str, options: list) -> str:
    """
    Routes slash commands to their handlers.
    This is where the AI Engine will plug in during Phase 3.
    """
    if command_name == "ask":
        question = options[0]["value"] if options else "nothing"
        return (
            f"🏛️ **Hermes heard you!**\n\n"
            f"You asked: *{question}*\n\n"
            f"⚙️ AI Engine is not connected yet (Phase 3). "
            f"But the pipeline is working end-to-end!"
        )

    elif command_name == "schedule":
        return (
            "📅 **Schedule Service**\n\n"
            "This will show your university lectures and deadlines.\n"
            "🔧 Coming in Phase 2!"
        )

    elif command_name == "goal":
        return (
            "🎯 **Goal Tracker**\n\n"
            "This will track your competitive exam preparation progress.\n"
            "🔧 Coming in Phase 2!"
        )

    elif command_name == "help":
        return (
            "🏛️ **Hermes — Your Personal AI Assistant**\n\n"
            "Available commands:\n"
            "• `/ask <question>` — Ask me anything about your studies\n"
            "• `/schedule` — View your university schedule\n"
            "• `/goal` — Check your exam preparation progress\n"
            "• `/help` — Show this message\n\n"
            "More features coming soon! 🚀"
        )

    return f"Unknown command: {command_name}"
