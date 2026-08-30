"""
Edge case test suite for the Accident Detection Engine.

Covers all 7 required edge cases with mocked payloads:
  1. Pothole / hard brake        → false positive suppression
  2. Impact at near-zero speed   → confidence penalty
  3. GPS no-fix                  → fallback to cached GPS
  4. Duplicate/repeated impacts  → debounce within 30s
  5. Cancel mid-send             → PENDING→CANCELLING→CANCELLED state machine
  6. Heartbeat stops             → device marked unreachable
  7. Unknown device              → auto-register + classify

Run from ml/:
    pytest tests/test_edge_cases.py -v
"""

import time

from fastapi.testclient import TestClient

import device_manager
import event_manager
from app import app

client = TestClient(app)


def _reset_state() -> None:
    """Reset all in-memory stores between tests."""
    device_manager.reset()
    event_manager.reset()


def _send_heartbeat(
    device_id: str = "VEH_001",
    speed: float = 45.0,
    gps_fix: bool = True,
    lat: float = 17.385,
    lon: float = 78.4867,
    battery: float = 90.0,
):
    """Helper: send a heartbeat payload."""
    return client.post(
        "/api/heartbeat",
        json={
            "device_id": device_id,
            "timestamp": time.time(),
            "speed_kmph": speed,
            "battery_pct": battery,
            "gps_lat": lat,
            "gps_lon": lon,
            "gps_fix": gps_fix,
        },
    )


def _send_impact(
    device_id: str = "VEH_001",
    impact_g: float = 3.8,
    gyro_delta: float = 5.0,
    gps_fix: bool = True,
    lat: float = 17.385,
    lon: float = 78.4867,
):
    """Helper: send an impact payload."""
    return client.post(
        "/api/impact",
        json={
            "device_id": device_id,
            "type": "impact",
            "timestamp": time.time(),
            "impact_g": impact_g,
            "gyro_delta": gyro_delta,
            "gps_lat": lat,
            "gps_lon": lon,
            "gps_fix": gps_fix,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Baseline: Clear Accident
# ─────────────────────────────────────────────────────────────────────────────

class TestClearAccident:
    """Both thresholds exceeded + high speed → accident with high confidence."""

    def setup_method(self):
        _reset_state()

    def test_high_impact_and_gyro_with_speed(self):
        _send_heartbeat(speed=50.0)
        resp = _send_impact(impact_g=3.8, gyro_delta=5.0)
        data = resp.json()

        assert resp.status_code == 200
        assert data["decision"] == "accident"
        assert data["confidence"] >= 0.55
        assert data["status"] == "PENDING"
        assert "impact_g" in data["reason"]
        assert "gyro_delta" in data["reason"]


# ─────────────────────────────────────────────────────────────────────────────
# Edge Case #1: Pothole / Hard Brake
# ─────────────────────────────────────────────────────────────────────────────

class TestPotholeFalsePositive:
    """High g-force but low rotation → likely pothole, NOT accident."""

    def setup_method(self):
        _reset_state()

    def test_high_impact_low_gyro(self):
        _send_heartbeat(speed=40.0)
        resp = _send_impact(impact_g=3.5, gyro_delta=0.5)
        data = resp.json()

        assert resp.status_code == 200
        assert data["decision"] == "no_accident"
        assert data["confidence"] < 0.3


# ─────────────────────────────────────────────────────────────────────────────
# Edge Case #2: Near-Zero Speed
# ─────────────────────────────────────────────────────────────────────────────

class TestNearZeroSpeed:
    """Standstill bump (e.g. door slam) → low confidence & no accident."""

    def setup_method(self):
        _reset_state()

    def test_impact_at_standstill(self):
        _send_heartbeat(speed=1.0)
        resp = _send_impact(impact_g=3.8, gyro_delta=0.5)
        data = resp.json()

        assert resp.status_code == 200
        assert data["confidence"] < 0.4
        assert data["decision"] == "no_accident"
        assert "standstill" in data["reason"].lower() or "speed_regime" in data["reason"].lower() or "policy" in data["reason"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# Edge Case #3: GPS No-Fix Fallback
# ─────────────────────────────────────────────────────────────────────────────

class TestGPSNoFix:
    """Impact with gps_fix=false → use last known GPS, flag approximate."""

    def setup_method(self):
        _reset_state()

    def test_fallback_to_cached_gps(self):
        # Establish GPS cache via heartbeat
        _send_heartbeat(speed=50.0, lat=17.400, lon=78.500, gps_fix=True)

        # Impact with no GPS fix and junk coords
        resp = _send_impact(
            impact_g=3.8, gyro_delta=5.0, gps_fix=False, lat=0.0, lon=0.0
        )
        data = resp.json()

        assert resp.status_code == 200
        assert data["gps"]["is_approximate"] is True
        assert data["gps"]["lat"] == 17.400
        assert data["gps"]["lon"] == 78.500

    def test_no_cached_gps_uses_payload(self):
        # Brand new device, no heartbeat → no cache
        resp = _send_impact(
            device_id="NO_CACHE_DEV",
            impact_g=3.8,
            gyro_delta=5.0,
            gps_fix=False,
            lat=17.111,
            lon=78.222,
        )
        data = resp.json()

        assert resp.status_code == 200
        assert data["gps"]["is_approximate"] is True
        assert data["gps"]["lat"] == 17.111


# ─────────────────────────────────────────────────────────────────────────────
# Edge Case #4: Duplicate / Repeated Impacts (Debounce)
# ─────────────────────────────────────────────────────────────────────────────

class TestDebounce:
    """Two impacts from same device within 30s → second is debounced."""

    def setup_method(self):
        _reset_state()

    def test_second_impact_within_window(self):
        _send_heartbeat(speed=50.0)
        first = _send_impact(impact_g=3.8, gyro_delta=5.0)
        first_data = first.json()

        second = _send_impact(impact_g=4.0, gyro_delta=5.5)
        second_data = second.json()

        assert second_data["debounced"] is True
        assert second_data["event_id"] == first_data["event_id"]

    def test_different_devices_not_debounced(self):
        """Debounce is per-device — different device_ids process independently."""
        _send_heartbeat(device_id="VEH_A", speed=50.0)
        _send_heartbeat(device_id="VEH_B", speed=60.0)

        first = _send_impact(device_id="VEH_A", impact_g=3.8, gyro_delta=5.0)
        second = _send_impact(device_id="VEH_B", impact_g=4.0, gyro_delta=5.5)

        assert "debounced" not in second.json() or second.json().get("debounced") is not True
        assert first.json()["event_id"] != second.json()["event_id"]


# ─────────────────────────────────────────────────────────────────────────────
# Edge Case #5: Cancel Mid-Send (State Machine)
# ─────────────────────────────────────────────────────────────────────────────

class TestEventStateMachine:
    """
    State machine: PENDING → CANCELLING → CANCELLED | CONFIRMED.
    CONFIRMED and CANCELLED are terminal.
    """

    def setup_method(self):
        _reset_state()

    def _create_event(self) -> str:
        _send_heartbeat(speed=50.0)
        resp = _send_impact(impact_g=3.8, gyro_delta=5.0)
        return resp.json()["event_id"]

    def test_pending_to_cancelling_to_cancelled(self):
        """Full cancel flow: PENDING → CANCELLING → CANCELLED."""
        event_id = self._create_event()

        r1 = client.patch(f"/api/events/{event_id}", json={"action": "cancel"})
        assert r1.status_code == 200
        assert r1.json()["status"] == "CANCELLING"

        r2 = client.patch(f"/api/events/{event_id}", json={"action": "cancel"})
        assert r2.status_code == 200
        assert r2.json()["status"] == "CANCELLED"

    def test_pending_to_confirmed(self):
        """Direct confirm: PENDING → CONFIRMED."""
        event_id = self._create_event()

        resp = client.patch(f"/api/events/{event_id}", json={"action": "confirm"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "CONFIRMED"

    def test_cancelling_to_confirmed_override(self):
        """Override cancel: PENDING → CANCELLING → CONFIRMED."""
        event_id = self._create_event()

        client.patch(f"/api/events/{event_id}", json={"action": "cancel"})
        resp = client.patch(f"/api/events/{event_id}", json={"action": "confirm"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "CONFIRMED"

    def test_confirmed_is_terminal(self):
        """Cannot cancel an already-confirmed event → 409."""
        event_id = self._create_event()

        client.patch(f"/api/events/{event_id}", json={"action": "confirm"})
        resp = client.patch(f"/api/events/{event_id}", json={"action": "cancel"})
        assert resp.status_code == 409

    def test_cancelled_is_terminal(self):
        """Cannot confirm a fully-cancelled event → 409."""
        event_id = self._create_event()

        client.patch(f"/api/events/{event_id}", json={"action": "cancel"})
        client.patch(f"/api/events/{event_id}", json={"action": "cancel"})
        resp = client.patch(f"/api/events/{event_id}", json={"action": "confirm"})
        assert resp.status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# Edge Case #6: Heartbeat Stops (Staleness)
# ─────────────────────────────────────────────────────────────────────────────

class TestHeartbeatStaleness:
    """No heartbeat for >30s → device marked unreachable."""

    def setup_method(self):
        _reset_state()

    def test_device_becomes_unreachable(self):
        _send_heartbeat(device_id="VEH_STALE", speed=30.0)

        # Verify active
        resp = client.get("/api/devices/VEH_STALE")
        assert resp.json()["status"] == "active"

        # Simulate time passing: set last_heartbeat_at to 31s ago
        device = device_manager.get_device("VEH_STALE")
        device.last_heartbeat_at = time.time() - 31

        device_manager.check_staleness()

        resp = client.get("/api/devices/VEH_STALE")
        assert resp.json()["status"] == "unreachable"

    def test_heartbeat_revives_device(self):
        """A new heartbeat should bring an unreachable device back to active."""
        _send_heartbeat(device_id="VEH_REVIVE", speed=30.0)

        device = device_manager.get_device("VEH_REVIVE")
        device.last_heartbeat_at = time.time() - 31
        device_manager.check_staleness()

        resp = client.get("/api/devices/VEH_REVIVE")
        assert resp.json()["status"] == "unreachable"

        # New heartbeat revives it
        _send_heartbeat(device_id="VEH_REVIVE", speed=25.0)
        resp = client.get("/api/devices/VEH_REVIVE")
        assert resp.json()["status"] == "active"


# ─────────────────────────────────────────────────────────────────────────────
# Edge Case #7: Unknown Device
# ─────────────────────────────────────────────────────────────────────────────

class TestUnknownDevice:
    """Impact/heartbeat from never-seen device → auto-register + process."""

    def setup_method(self):
        _reset_state()

    def test_impact_from_unknown_device(self):
        resp = _send_impact(
            device_id="MYSTERY_VEH_999",
            impact_g=3.8,
            gyro_delta=5.0,
        )
        data = resp.json()

        assert resp.status_code == 200
        assert data["device_id"] == "MYSTERY_VEH_999"
        assert data["decision"] in ("accident", "no_accident")
        assert "event_id" in data

        # Verify device was registered
        dev_resp = client.get("/api/devices/MYSTERY_VEH_999")
        assert dev_resp.status_code == 200

    def test_heartbeat_from_unknown_device(self):
        resp = _send_heartbeat(device_id="NEW_VEH_X")
        assert resp.status_code == 200
        assert resp.json()["device_status"] == "active"

        dev_resp = client.get("/api/devices/NEW_VEH_X")
        assert dev_resp.status_code == 200
