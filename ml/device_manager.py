"""
In-memory device registry with heartbeat buffering, GPS caching,
and staleness detection.

Handles:
  - Edge case #3: GPS no-fix fallback via per-device GPS cache
  - Edge case #6: Heartbeat staleness → mark device "unreachable"
  - Edge case #7: Unknown device auto-registration

Thread-safety note: FastAPI runs on a single-threaded asyncio loop,
so dict mutations are safe without locks. For multi-worker deployments,
swap to Redis or equivalent.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Optional

import config
from logger import get_logger, log_event
from models import (
    DeviceContext,
    DeviceInfo,
    GPSCoord,
    HeartbeatPayload,
    ImpactPayload,
)

_logger = get_logger("device_manager")

# ── Internal State ───────────────────────────────────────────────────────────
_devices: dict[str, DeviceInfo] = {}
_heartbeat_buffers: dict[str, deque[HeartbeatPayload]] = {}
_gps_cache: dict[str, GPSCoord] = {}


def reset() -> None:
    """Clear all state. Used by tests between runs."""
    _devices.clear()
    _heartbeat_buffers.clear()
    _gps_cache.clear()


# ── Device Registration ─────────────────────────────────────────────────────

def register_or_get(device_id: str) -> DeviceInfo:
    """
    Return the DeviceInfo for device_id, auto-registering if unknown.
    Edge case #7: unknown device → create entry, continue processing.
    """
    if device_id not in _devices:
        info = DeviceInfo(
            device_id=device_id,
            registered_at=time.time(),
            status="new",
        )
        _devices[device_id] = info
        _heartbeat_buffers[device_id] = deque(
            maxlen=config.HEARTBEAT_BUFFER_SIZE
        )
        log_event(
            _logger,
            action="device_registered",
            resource_id=device_id,
            actor="system",
            source="auto",
        )
    return _devices[device_id]


# ── Heartbeat Ingestion ─────────────────────────────────────────────────────

def record_heartbeat(payload: HeartbeatPayload) -> DeviceInfo:
    """
    Ingest a heartbeat: update device status to active,
    buffer the reading, cache GPS if fix is valid.
    """
    device = register_or_get(payload.device_id)
    device.last_heartbeat_at = time.time()
    device.status = "active"

    _heartbeat_buffers[payload.device_id].append(payload)

    if payload.gps_fix:
        gps = GPSCoord(lat=payload.gps_lat, lon=payload.gps_lon)
        _gps_cache[payload.device_id] = gps
        device.last_known_gps = gps

    log_event(
        _logger,
        action="heartbeat_recorded",
        resource_id=payload.device_id,
        speed=payload.speed_kmph,
        battery=payload.battery_pct,
        gps_fix=payload.gps_fix,
    )
    return device


# ── Context Queries ──────────────────────────────────────────────────────────

def get_recent_speed(device_id: str) -> Optional[float]:
    """
    Most recent speed_kmph from heartbeat buffer, or None.
    Edge case #2: near-zero speed check uses this.
    """
    buf = _heartbeat_buffers.get(device_id)
    if not buf:
        return None
    return buf[-1].speed_kmph


def get_last_known_gps(device_id: str) -> Optional[GPSCoord]:
    """
    Cached GPS from last heartbeat/impact with gps_fix=true.
    Edge case #3: GPS no-fix fallback uses this.
    """
    return _gps_cache.get(device_id)


def cache_gps_from_impact(impact: ImpactPayload) -> None:
    """Cache GPS from an impact event if it has a valid fix."""
    if impact.gps_fix:
        gps = GPSCoord(lat=impact.gps_lat, lon=impact.gps_lon)
        _gps_cache[impact.device_id] = gps
        device = _devices.get(impact.device_id)
        if device is not None:
            device.last_known_gps = gps


def build_context(device_id: str) -> DeviceContext:
    """Assemble full device context for the classifier."""
    device = _devices.get(device_id)
    return DeviceContext(
        recent_speed=get_recent_speed(device_id),
        device_status=device.status if device else "unknown",
        last_known_gps=get_last_known_gps(device_id),
    )


# ── Staleness Detection ─────────────────────────────────────────────────────

def check_staleness() -> list[str]:
    """
    Scan all devices; mark any with no heartbeat in >HEARTBEAT_STALE_S
    as 'unreachable'. Edge case #6.

    Returns list of device_ids that became unreachable this sweep.
    """
    now = time.time()
    newly_stale: list[str] = []
    for device_id, info in _devices.items():
        if info.status == "unreachable":
            continue
        if info.last_heartbeat_at is None:
            # Registered but never sent heartbeat — leave as "new"
            continue
        if now - info.last_heartbeat_at > config.HEARTBEAT_STALE_S:
            info.status = "unreachable"
            newly_stale.append(device_id)
            log_event(
                _logger,
                action="device_unreachable",
                resource_id=device_id,
                elapsed_s=round(now - info.last_heartbeat_at, 1),
            )
    return newly_stale


# ── Lookups ──────────────────────────────────────────────────────────────────

def get_device(device_id: str) -> Optional[DeviceInfo]:
    """Return device info or None."""
    return _devices.get(device_id)


def list_devices() -> list[DeviceInfo]:
    """Return all registered devices."""
    return list(_devices.values())
