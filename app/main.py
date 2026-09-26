from fastapi import FastAPI, Request
import json
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Hermes Webhook Service")

@app.get("/")
async def root():
    return {"message": "Hermes Webhook Service is running"}

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Endpoint for Telegram to send updates.
    """
    try:
        data = await request.json()
        logger.info(f"Received Telegram payload: {json.dumps(data)}")
        
        # TODO: Parse message and user ID from data
        # TODO: Route to AI Engine
        # TODO: Send response back via Telegram API
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "detail": str(e)}

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Endpoint for WhatsApp Cloud API to send updates.
    """
    try:
        data = await request.json()
        logger.info(f"Received WhatsApp payload: {json.dumps(data)}")
        
        # TODO: Verify token on setup (GET request handler also needed for setup)
        # TODO: Parse message and user ID from data
        # TODO: Route to AI Engine
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "detail": str(e)}

@app.post("/webhook/discord")
async def discord_webhook(request: Request):
    """
    Endpoint for Discord Interactions Webhook.
    """
    try:
        # Note: Discord requires request signature verification using Ed25519
        data = await request.json()
        logger.info(f"Received Discord payload: {json.dumps(data)}")
        
        # TODO: Verify cryptographic signature using DISCORD_PUBLIC_KEY
        # TODO: Handle Discord Ping ('type': 1) required during webhook setup
        # TODO: Route user messages to AI Engine
        
        return {"type": 4, "data": {"content": "Message received by Hermes"}}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "detail": str(e)}
