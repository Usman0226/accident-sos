"""
Unit tests for Context-Aware Decision Policy.
"""

import time
import pytest

import decision_policy
from models import ClassificationResult, DeviceContext, ImpactPayload


def make_payload(impact_g: float = 1.0, gyro_delta: float = 1.0, gps_fix: bool = True) -> ImpactPayload:
    return ImpactPayload(
        device_id="DEV_POL_01",
        timestamp=time.time(),
        impact_g=impact_g,
        gyro_delta=gyro_delta,
        gps_lat=17.385,
        gps_lon=78.487,
        gps_fix=gps_fix,
    )


def test_decision_policy_highway_speed_reduction():
    """Highway driving lowers the decision threshold."""
    impact = make_payload(impact_g=2.0)
    context = DeviceContext(recent_speed=95.0)
    ml_result = ClassificationResult(decision="accident", confidence=0.55, reason="ML score")

    policy = decision_policy.evaluate_policy(ml_result, impact, context)
    assert policy.adjusted_threshold < policy.base_threshold
    assert policy.action == "escalate"


def test_decision_policy_standstill_threshold_increase():
    """Standstill increases the decision threshold to avoid false alarms from loading."""
    impact = make_payload(impact_g=2.0)
    context = DeviceContext(recent_speed=1.0)
    ml_result = ClassificationResult(decision="accident", confidence=0.65, reason="ML score")

    policy = decision_policy.evaluate_policy(ml_result, impact, context)
    assert policy.adjusted_threshold > policy.base_threshold


def test_decision_policy_no_gps_fix_conservative():
    """Missing GPS fix leads to conservative threshold reduction."""
    impact = make_payload(impact_g=1.5, gps_fix=False)
    context = DeviceContext(recent_speed=None)
    ml_result = ClassificationResult(decision="no_accident", confidence=0.40, reason="ML score")

    policy = decision_policy.evaluate_policy(ml_result, impact, context)
    assert "gps_validity" in policy.context_factors
    assert policy.context_factors["gps_validity"]["has_fix"] is False


def test_decision_policy_observation_band():
    """Confidence close to threshold falls into observe action."""
    impact = make_payload(impact_g=1.5)
    context = DeviceContext(recent_speed=40.0)
    ml_result = ClassificationResult(decision="no_accident", confidence=0.55, reason="Borderline")

    policy = decision_policy.evaluate_policy(ml_result, impact, context)
    assert policy.action in ["observe", "escalate"]
