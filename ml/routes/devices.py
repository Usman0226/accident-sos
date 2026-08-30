"""Device registry query endpoints."""

from fastapi import APIRouter, HTTPException

import device_manager
import event_manager

router = APIRouter(prefix="/api", tags=["devices"])


@router.get("/devices")
async def list_devices():
    """List all registered devices with current status."""
    devices = device_manager.list_devices()
    return [d.model_dump() for d in devices]


@router.get("/devices/{device_id}")
async def get_device(device_id: str):
    """Get a specific device's registry info."""
    device = device_manager.get_device(device_id)
    if device is None:
        raise HTTPException(
            status_code=404, detail=f"Device {device_id} not found"
        )
    return device.model_dump()


@router.get("/devices/{device_id}/events")
async def get_device_events(device_id: str):
    """List all events for a specific device, newest first."""
    device = device_manager.get_device(device_id)
    if device is None:
        raise HTTPException(
            status_code=404, detail=f"Device {device_id} not found"
        )
    events = event_manager.get_device_events(device_id)
    return [e.model_dump() for e in events]
