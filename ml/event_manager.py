"""
Event lifecycle manager with debounce and state machine.

Handles:
  - Edge case #4: Impact debouncing per device (~30s window)
  - Edge case #5: Event state machine with CANCELLING intermediate state
      PENDING → CONFIRMED
      PENDING → CANCELLING
      CANCELLING → CANCELLED
      CANCELLING → CONFIRMED  (cancel override)
"""

from __future__ import annotations

import time
import uuid
from typing import Optional

import config
from logger import get_logger, log_event
from models import (
    AccidentEvent,
    ClassificationResult,
    EventStatus,
    GPSCoord,
    ImpactPayload,
    VALID_TRANSITIONS,
)

_logger = get_logger("event_manager")

# ── Internal State ───────────────────────────────────────────────────────────
_events: dict[str, AccidentEvent] = {}
_device_events: dict[str, list[str]] = {}
_last_impact_time: dict[str, float] = {}
_last_event_id: dict[str, str] = {}


def reset() -> None:
    """Clear all state. Used by tests between runs."""
    _events.clear()
    _device_events.clear()
    _last_impact_time.clear()
    _last_event_id.clear()


# ── Debounce ─────────────────────────────────────────────────────────────────

def is_debounced(device_id: str) -> tuple[bool, Optional[str]]:
    """
    Check if a new impact from device_id should be suppressed.
    Edge case #4: ignore repeated impacts within DEBOUNCE_WINDOW_S.

    Returns:
        (is_debounced, existing_event_id_or_None)
    """
    last_time = _last_impact_time.get(device_id)
    if last_time is not None:
        elapsed = time.time() - last_time
        if elapsed < config.DEBOUNCE_WINDOW_S:
            return True, _last_event_id.get(device_id)
    return False, None


# ── Event Creation ───────────────────────────────────────────────────────────

def create_event(
    impact: ImpactPayload,
    result: ClassificationResult,
    gps: GPSCoord,
) -> AccidentEvent:
    """
    Create a new accident event in PENDING state.
    Records debounce timestamp for the device.
    """
    event_id = f"evt_{uuid.uuid4().hex[:8]}"
    now = time.time()

    event = AccidentEvent(
        event_id=event_id,
        device_id=impact.device_id,
        decision=result.decision,
        confidence=result.confidence,
        reason=result.reason,
        gps=gps,
        status=EventStatus.PENDING,
        created_at=now,
        impact_snapshot=impact,
    )

    _events[event_id] = event
    _device_events.setdefault(impact.device_id, []).append(event_id)
    _last_impact_time[impact.device_id] = now
    _last_event_id[impact.device_id] = event_id

    log_event(
        _logger,
        action="event_created",
        resource_id=event_id,
        actor=impact.device_id,
        decision=result.decision,
        confidence=result.confidence,
    )
    return event


# ── State Machine ────────────────────────────────────────────────────────────

def transition_event(
    event_id: str, target_status: EventStatus
) -> tuple[bool, str]:
    """
    Attempt a state transition on an event.
    Edge case #5: enforces valid transitions only.

    Returns:
        (success, human-readable message)
    """
    event = _events.get(event_id)
    if event is None:
        return False, f"Event {event_id} not found"

    current = event.status
    allowed = VALID_TRANSITIONS.get(current)

    if allowed is None or target_status not in allowed:
        allowed_str = (
            ", ".join(s.value for s in allowed)
            if allowed
            else "none (terminal state)"
        )
        return False, (
            f"Invalid transition: {current.value} → {target_status.value}. "
            f"Allowed from {current.value}: {allowed_str}"
        )

    event.status = target_status
    log_event(
        _logger,
        action="event_transition",
        resource_id=event_id,
        actor="api",
        from_status=current.value,
        to_status=target_status.value,
    )
    return True, f"Transitioned {current.value} → {target_status.value}"


# ── Lookups ──────────────────────────────────────────────────────────────────

def get_event(event_id: str) -> Optional[AccidentEvent]:
    """Fetch a single event by ID."""
    return _events.get(event_id)


def get_device_events(device_id: str) -> list[AccidentEvent]:
    """Fetch all events for a device, newest first."""
    event_ids = _device_events.get(device_id, [])
    events = [_events[eid] for eid in event_ids if eid in _events]
    events.sort(key=lambda e: e.created_at, reverse=True)
    return events


def list_all_events() -> list[AccidentEvent]:
    """Return all events, newest first."""
    events = list(_events.values())
    events.sort(key=lambda e: e.created_at, reverse=True)
    return events
