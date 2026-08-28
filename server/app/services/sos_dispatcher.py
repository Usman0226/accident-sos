import asyncio
import httpx
import logging
from app.core.config import settings
from app.models.domain import EventLog, DeviceState
from app.db.session import SessionLocal
import json

logger = logging.getLogger(__name__)

async def _send_mock_sms(device_id: str, payload: dict):
    logger.info(f"MOCK SMS: Sending SOS for {device_id}. Payload: {payload}")
    await asyncio.sleep(1)
    return True

async def _send_telegram_alert(device_id: str, payload: dict):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False
        
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    text = f"SOS ALERT for Device {device_id}\n\nDetails: {json.dumps(payload, indent=2)}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": text})
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Telegram alert failed: {e}")
            return False

async def dispatch_sos_task(device_id: str, payload: dict):
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        success = False
        delivery_method = "none"
        
        if settings.TELEGRAM_BOT_TOKEN:
            success = await _send_telegram_alert(device_id, payload)
            if success:
                delivery_method = "telegram"
        
        if not success:
            success = await _send_mock_sms(device_id, payload)
            if success:
                delivery_method = "sms_mock"
                
        if success:
            logger.info(f"SOS for {device_id} dispatched successfully via {delivery_method}")
            with SessionLocal() as db:
                device = db.query(DeviceState).filter(DeviceState.device_id == device_id).first()
                if device:
                    device.status = "sos_confirmed"
                
                log_entry = EventLog(
                    device_id=device_id,
                    timestamp=payload.get("timestamp", 0),
                    event_type="sos_dispatch",
                    payload=json.dumps({"success": True, "method": delivery_method, "attempt": attempt + 1})
                )
                db.add(log_entry)
                db.commit()
            return
            
        logger.warning(f"SOS dispatch attempt {attempt + 1} failed. Retrying in {base_delay ** attempt}s...")
        await asyncio.sleep(base_delay ** attempt)
        
    logger.error(f"SOS dispatch for {device_id} completely failed after {max_retries} attempts.")
    with SessionLocal() as db:
        log_entry = EventLog(
            device_id=device_id,
            timestamp=payload.get("timestamp", 0),
            event_type="sos_dispatch_failed",
            payload=json.dumps({"success": False, "attempts": max_retries})
        )
        db.add(log_entry)
        db.commit()
