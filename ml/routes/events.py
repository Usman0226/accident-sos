"""Event status management endpoints."""

from fastapi import APIRouter, HTTPException

import event_manager
from logger import get_logger
from models import EventAction, EventStatus

router = APIRouter(prefix="/api", tags=["events"])
_logger = get_logger("routes.events")

# Map user-facing action strings to target states.
# "cancel" on PENDING → CANCELLING; "cancel" on CANCELLING → CANCELLED.
_ACTION_MAP: dict[str, EventStatus] = {
    "cancel": EventStatus.CANCELLING,
    "confirm": EventStatus.CONFIRMED,
}


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """Fetch a single event by ID."""
    event = event_manager.get_event(event_id)
    if event is None:
        raise HTTPException(
            status_code=404, detail=f"Event {event_id} not found"
        )
    return event.model_dump()


@router.patch("/events/{event_id}")
async def update_event(event_id: str, body: EventAction):
    """
    Transition an event's status via the state machine.
    Edge case #5: PENDING → CANCELLING → CANCELLED | CONFIRMED.

    Actions:
      "cancel"  on PENDING    → CANCELLING
      "cancel"  on CANCELLING → CANCELLED
      "confirm" on PENDING    → CONFIRMED
      "confirm" on CANCELLING → CONFIRMED  (override — cancel arrived too late)

    Returns 409 on invalid transitions (e.g., cancelling a CONFIRMED event).
    """
    event = event_manager.get_event(event_id)
    if event is None:
        raise HTTPException(
            status_code=404, detail=f"Event {event_id} not found"
        )

    # Resolve the actual target status based on current state + action
    if body.action == "cancel" and event.status == EventStatus.CANCELLING:
        target = EventStatus.CANCELLED
    else:
        target = _ACTION_MAP.get(body.action)
        if target is None:
            raise HTTPException(
                status_code=400, detail=f"Unknown action: {body.action}"
            )

    success, message = event_manager.transition_event(event_id, target)
    if not success:
        raise HTTPException(status_code=409, detail=message)

    updated = event_manager.get_event(event_id)
    return {
        "event_id": event_id,
        "status": updated.status.value if updated else "unknown",
        "message": message,
    }
