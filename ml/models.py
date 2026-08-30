"""
Pydantic data models for the Accident SOS detection engine.

Covers: heartbeat ingestion, impact events, GPS resolution,
classification output, event lifecycle, and device registry.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Event State Machine ──────────────────────────────────────────────────────
# Transitions:
#   PENDING   → CONFIRMED
#   PENDING   → CANCELLING
#   CANCELLING → CANCELLED
#   CANCELLING → CONFIRMED  (override — cancel arrived too late)
# CONFIRMED and CANCELLED are terminal.

class EventStatus(str, Enum):
    PENDING = "PENDING"
    CANCELLING = "CANCELLING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


VALID_TRANSITIONS: dict[EventStatus, set[EventStatus]] = {
    EventStatus.PENDING: {EventStatus.CONFIRMED, EventStatus.CANCELLING},
    EventStatus.CANCELLING: {EventStatus.CANCELLED, EventStatus.CONFIRMED},
    # CONFIRMED and CANCELLED intentionally absent — terminal states.
}


# ── Payloads ─────────────────────────────────────────────────────────────────

class HeartbeatPayload(BaseModel):
    """Telemetry heartbeat from an IoT vehicle device."""
    device_id: str = Field(..., min_length=1)
    timestamp: float
    speed_kmph: float = Field(..., ge=0)
    battery_pct: float = Field(..., ge=0, le=100)
    gps_lat: float = Field(..., ge=-90, le=90)
    gps_lon: float = Field(..., ge=-180, le=180)
    gps_fix: bool


class ImpactPayload(BaseModel):
    """Impact event from an IoT vehicle device's crash sensor."""
    device_id: str = Field(..., min_length=1)
    type: str = Field(default="impact")
    timestamp: float
    impact_g: float = Field(..., ge=0)
    gyro_delta: float = Field(..., ge=0)
    gps_lat: float = Field(..., ge=-90, le=90)
    gps_lon: float = Field(..., ge=-180, le=180)
    gps_fix: bool


# ── Internal Types ───────────────────────────────────────────────────────────

class GPSCoord(BaseModel):
    """Resolved GPS position, optionally flagged as approximate."""
    lat: float
    lon: float
    is_approximate: bool = False


class ClassificationResult(BaseModel):
    """Output of the rule-based classifier."""
    decision: str  # "accident" | "no_accident"
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str


class AccidentEvent(BaseModel):
    """Full event record stored by EventManager."""
    event_id: str
    device_id: str
    decision: str
    confidence: float
    reason: str
    gps: GPSCoord
    status: EventStatus
    created_at: float
    impact_snapshot: ImpactPayload


class DeviceInfo(BaseModel):
    """Device registry entry."""
    device_id: str
    registered_at: float
    last_heartbeat_at: Optional[float] = None
    status: str = "new"  # "new" | "active" | "unreachable"
    last_known_gps: Optional[GPSCoord] = None


class DeviceContext(BaseModel):
    """Contextual data about a device, assembled for the classifier."""
    recent_speed: Optional[float] = None
    device_status: str = "new"
    last_known_gps: Optional[GPSCoord] = None


class EventAction(BaseModel):
    """Request body for PATCH /api/events/{event_id}."""
    action: str = Field(..., pattern=r"^(cancel|confirm)$")
