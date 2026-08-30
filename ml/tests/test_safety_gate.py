"""
Unit tests for Safety Gate invariants and deterministic overrides.
"""

import time
import pytest

from models import ClassificationResult, DeviceContext, ImpactPayload
from safety_gate import SafetyGate, SafetyGateResult


@pytest.fixture
def gate():
    return SafetyGate(
        severe_impact_g=4.5,
        impact_threshold=1.2,
        speed_high=30.0,
        confidence_floor=0.3,
        max_suppression_rate=0.05,
    )


def make_payload(impact_g: float = 1.0, gyro_delta: float = 1.0) -> ImpactPayload:
    return ImpactPayload(
        device_id="DEV_SAFE_01",
        timestamp=time.time(),
        impact_g=impact_g,
        gyro_delta=gyro_delta,
        gps_lat=17.385,
        gps_lon=78.487,
        gps_fix=True,
    )


def test_safety_gate_manual_sos(gate):
    """Rule 1: Manual SOS must NEVER be suppressed, regardless of ML output."""
    impact = make_payload(impact_g=0.2, gyro_delta=0.1)
    context = DeviceContext(recent_speed=0.0)
    ml_result = ClassificationResult(
        decision="no_accident", confidence=0.05, reason="Low ML confidence"
    )

    res = gate.evaluate(ml_result, impact, context, is_manual_sos=True)
    assert res.final_decision == "accident"
    assert res.was_overridden is True
    assert res.confidence >= 0.95


def test_safety_gate_severe_impact_override(gate):
    """Rule 2: Severe impact (>4.5g) must override any no_accident decision."""
    impact = make_payload(impact_g=5.5, gyro_delta=0.5)
    context = DeviceContext(recent_speed=20.0)
    ml_result = ClassificationResult(
        decision="no_accident", confidence=0.10, reason="Low rotation"
    )

    res = gate.evaluate(ml_result, impact, context)
    assert res.final_decision == "accident"
    assert res.was_overridden is True
    assert "severe_impact_override" in res.override_reason


def test_safety_gate_high_speed_moderate_impact_override(gate):
    """Rule 3: High speed (>30 km/h) + moderate impact (>1.2g) with rotational signature cannot be suppressed."""
    impact = make_payload(impact_g=1.8, gyro_delta=2.5)
    context = DeviceContext(recent_speed=60.0)
    ml_result = ClassificationResult(
        decision="no_accident", confidence=0.20, reason="Borderline"
    )

    res = gate.evaluate(ml_result, impact, context)
    assert res.final_decision == "accident"
    assert res.was_overridden is True
    assert "high_speed_impact_override" in res.override_reason


def test_safety_gate_confidence_floor_escalation(gate):
    """Rule 4: Uncertain rejection with sensor energy above threshold must escalate."""
    impact = make_payload(impact_g=1.5, gyro_delta=3.5)
    context = DeviceContext(recent_speed=15.0)
    ml_result = ClassificationResult(
        decision="no_accident", confidence=0.25, reason="Low confidence"
    )

    res = gate.evaluate(ml_result, impact, context)
    assert res.final_decision == "accident"
    assert res.was_overridden is True
    assert "low_confidence_escalation" in res.override_reason


def test_safety_gate_passthrough_clean_event(gate):
    """Normal driving with zero crash characteristics passes through as no_accident."""
    impact = make_payload(impact_g=0.3, gyro_delta=0.5)
    context = DeviceContext(recent_speed=25.0)
    ml_result = ClassificationResult(
        decision="no_accident", confidence=0.01, reason="Normal"
    )

    res = gate.evaluate(ml_result, impact, context)
    assert res.final_decision == "no_accident"
    assert res.was_overridden is False
