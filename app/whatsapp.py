"""
whatsapp.py — WhatsApp Cloud API integration for Hermes.
Handles webhook verification, incoming message routing, and outbound messages.
"""
import logging
import os

import httpx
from fastapi import APIRouter, Query, Request, Response

from app.agent import hermes_agent_process

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["WhatsApp"])

# ── Environment Variables ──────────────────────────────────────
WHATSAPP_ACCESS_TOKEN   = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN   = os.getenv("WHATSAPP_VERIFY_TOKEN", "hermes_secret_token")


# ─────────────────────────────────────────────────────────────
# Webhook Verification (GET — one-time setup step with Meta)
# ─────────────────────────────────────────────────────────────

@router.get("/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode:         str = Query(None, alias="hub.mode"),
    hub_challenge:    str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    Meta calls this endpoint once with a challenge string.
    We must echo it back to prove we own the server.
    """
    logger.info(f"WA Webhook verification: mode={hub_mode}")
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("✅ WhatsApp Webhook verified successfully.")
        return Response(content=hub_challenge, media_type="text/plain")
    logger.warning("❌ WhatsApp Webhook verification failed — token mismatch.")
    return Response(content="Forbidden", status_code=403)


# ─────────────────────────────────────────────────────────────
# Incoming Message Handler (POST — every WhatsApp message)
# ─────────────────────────────────────────────────────────────

@router.post("/whatsapp")
async def handle_whatsapp_incoming(request: Request):
    """
    Receives and processes every incoming WhatsApp message from Meta.
    Runs Hermes agent and sends the AI reply back to the user.
    """
    payload = await request.json()
    logger.debug(f"WhatsApp payload: {payload}")

    try:
        entry = payload.get("entry", [])
        if not entry:
            return {"status": "no_entry"}

        changes = entry[0].get("changes", [])
        if not changes:
            return {"status": "no_changes"}

        value    = changes[0].get("value", {})
        messages = value.get("messages")

        if not messages:
            # Could be a read receipt or delivery update — ignore silently
            return {"status": "ok_no_message"}

        message     = messages[0]
        from_number = message.get("from")
        msg_type    = message.get("type", "")
        contact     = value.get("contacts", [{}])[0]
        user_name   = contact.get("profile", {}).get("name", "User")

        # ── Only handle text messages for now ──
        if msg_type != "text":
            await send_whatsapp_message(
                from_number,
                "Hey! I can only read text messages right now. Please send me a text 😊"
            )
            return {"status": "unsupported_type"}

        user_text = message.get("text", {}).get("body", "").strip()
        if not user_text:
            return {"status": "empty_text"}

        user_id = f"wa:{from_number}"
        logger.info(f"📩 WhatsApp message from {user_id} ({user_name}): {user_text[:80]}")

        # ── Run Hermes Agent ──
        reply = await hermes_agent_process(
            user_id=user_id,
            user_name=user_name,
            user_message=user_text,
        )

        await send_whatsapp_message(from_number, reply)

    except Exception as e:
        logger.error(f"Error handling WhatsApp message: {e}", exc_info=True)

    # Meta requires always returning 200 OK promptly
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────
# Outbound Message Sender
# ─────────────────────────────────────────────────────────────

async def send_whatsapp_message(to_number: str, text: str):
    """Send a text reply back to a WhatsApp user via Meta Graph API."""
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials not configured — cannot send message.")
        return

    # WhatsApp has a 4096-character text limit per message
    # Split long replies into chunks
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]

    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        for chunk in chunks:
            data = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {"body": chunk},
            }
            resp = await client.post(url, json=data, headers=headers)
            if resp.status_code != 200:
                logger.error(f"WhatsApp API error {resp.status_code}: {resp.text}")
            else:
                logger.info(f"✅ Sent WhatsApp reply to {to_number}")
