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
    public_key = os.getenv("DISCORD_PUBLIC_KEY")
    if not public_key:
        raise HTTPException(status_code=500, detail="Missing DISCORD_PUBLIC_KEY setup")
        
    try:
        verify_key = VerifyKey(bytes.fromhex(public_key))
        signature = request.headers.get("X-Signature-Ed25519")
        timestamp = request.headers.get("X-Signature-Timestamp")
        
        body = await request.body()
        verify_key.verify(f"{timestamp}".encode() + body, bytes.fromhex(signature))
    except (BadSignatureError, Exception) as e:
        logger.error(f"Verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid request signature")
        
    try:
        data = await request.json()
        logger.info(f"Received Discord payload: {json.dumps(data)}")
        
        # Handle Discord Ping required to save the URL
        if data.get("type") == 1:
            return {"type": 1}
            
        return {"type": 4, "data": {"content": "Message received by Hermes!"}}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "detail": str(e)}
