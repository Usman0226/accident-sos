"""Heartbeat ingestion endpoint."""

from fastapi import APIRouter, HTTPException

import device_manager
from logger import get_logger, log_event
from models import HeartbeatPayload

router = APIRouter(prefix="/api", tags=["heartbeat"])
_logger = get_logger("routes.heartbeat")


@router.post("/heartbeat")
async def receive_heartbeat(payload: HeartbeatPayload):
    """
    Ingest a device heartbeat. Updates speed, GPS cache, and device status.
    Auto-registers unknown devices (edge case #7).
    """
    try:
        device = device_manager.record_heartbeat(payload)
        return {
            "status": "ok",
            "device_status": device.status,
        }
    except Exception as exc:
        log_event(
            _logger,
            action="heartbeat_error",
            resource_id=payload.device_id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=500, detail="Failed to process heartbeat"
        ) from exc
