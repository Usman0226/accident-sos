"""
Context-Aware Decision Policy.

Adjusts the ML confidence threshold based on situational context
rather than using a flat cutoff. Per README §33: move from a simple
threshold to a "context-aware policy."

Context factors:
  - Speed regime: standstill → raise threshold, highway → lower it
  - GPS validity: no fix → conservative (lower threshold)
  - Device health: recently reconnected → lower threshold
  - Impact magnitude: higher impact → lower threshold
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

import config
from logger import get_logger, log_event
from models import ClassificationResult, DeviceContext, ImpactPayload

_logger = get_logger("decision_policy")


class PolicyDecision(BaseModel):
    """Output of the context-aware decision policy."""

    action: str  # "escalate" | "observe" | "reject"
    adjusted_threshold: float
    base_threshold: float
    context_factors: dict
    ml_confidence: float
    reason: str


def evaluate_policy(
    ml_result: ClassificationResult,
    impact: ImpactPayload,
    context: DeviceContext,
) -> PolicyDecision:
    """
    Evaluate the ML result through the context-aware decision policy.

    Returns a PolicyDecision with the adjusted threshold and final action.
    """
    base_threshold = config.ACCIDENT_CONFIDENCE_CUTOFF
    threshold = base_threshold
    factors: dict[str, object] = {}

    # ── Factor 1: Speed regime ───────────────────────────────────────────
    speed = context.recent_speed
    if speed is not None:
        if speed < config.SPEED_LOW_THRESHOLD:
            # Near-standstill: impacts more likely to be loading/bumps
            increase = config.POLICY_STANDSTILL_THRESHOLD_INCREASE
            threshold += increase
            factors["speed_regime"] = {
                "type": "standstill",
                "speed_kmh": speed,
                "threshold_adjustment": f"+{increase}",
            }
        elif speed > config.POLICY_HIGHWAY_SPEED:
            # Highway: any real impact at this speed is more likely serious
            reduction = config.POLICY_HIGHWAY_THRESHOLD_REDUCTION
            threshold -= reduction
            factors["speed_regime"] = {
                "type": "highway",
                "speed_kmh": speed,
                "threshold_adjustment": f"-{reduction}",
            }
        else:
            factors["speed_regime"] = {
                "type": "normal",
                "speed_kmh": speed,
                "threshold_adjustment": "0",
            }
    else:
        factors["speed_regime"] = {
            "type": "unknown",
            "threshold_adjustment": "0",
        }

    # ── Factor 2: GPS validity ───────────────────────────────────────────
    if not impact.gps_fix:
        # No GPS fix: cannot verify speed, err on caution
        threshold -= 0.05
        factors["gps_validity"] = {
            "has_fix": False,
            "threshold_adjustment": "-0.05",
        }
    else:
        factors["gps_validity"] = {
            "has_fix": True,
            "threshold_adjustment": "0",
        }

    # ── Factor 3: Device health ──────────────────────────────────────────
    if context.device_status == "unreachable":
        # Device was recently unreachable — may have missed events
        threshold -= 0.05
        factors["device_health"] = {
            "status": "unreachable",
            "threshold_adjustment": "-0.05",
        }
    elif context.device_status == "new":
        # Newly registered device — no baseline yet
        factors["device_health"] = {
            "status": "new",
            "threshold_adjustment": "0",
        }
    else:
        factors["device_health"] = {
            "status": context.device_status,
            "threshold_adjustment": "0",
        }

    # ── Factor 4: Impact magnitude scaling ───────────────────────────────
    if impact.impact_g > config.SEVERE_IMPACT_G:
        # Extremely high impact — lower threshold further
        threshold -= 0.10
        factors["impact_magnitude"] = {
            "impact_g": impact.impact_g,
            "level": "severe",
            "threshold_adjustment": "-0.10",
        }
    elif impact.impact_g > config.IMPACT_G_THRESHOLD:
        # Above baseline threshold
        factors["impact_magnitude"] = {
            "impact_g": impact.impact_g,
            "level": "moderate",
            "threshold_adjustment": "0",
        }
    else:
        factors["impact_magnitude"] = {
            "impact_g": impact.impact_g,
            "level": "low",
            "threshold_adjustment": "0",
        }

    # ── Clamp threshold to valid range ───────────────────────────────────
    threshold = max(0.10, min(0.90, threshold))

    # ── Make decision ────────────────────────────────────────────────────
    confidence = ml_result.confidence

    if confidence >= threshold:
        action = "escalate"
        reason = (
            f"ML confidence {confidence:.2f} >= adjusted threshold {threshold:.2f}"
        )
    elif confidence >= threshold - 0.10:
        action = "observe"
        reason = (
            f"ML confidence {confidence:.2f} is within observation band "
            f"({threshold - 0.10:.2f}–{threshold:.2f})"
        )
    else:
        action = "reject"
        reason = (
            f"ML confidence {confidence:.2f} < adjusted threshold {threshold:.2f}"
        )

    decision = PolicyDecision(
        action=action,
        adjusted_threshold=round(threshold, 4),
        base_threshold=base_threshold,
        context_factors=factors,
        ml_confidence=confidence,
        reason=reason,
    )

    log_event(
        _logger,
        action="policy_decision",
        resource_id=impact.device_id,
        actor="decision_policy",
        policy_action=action,
        adjusted_threshold=threshold,
        base_threshold=base_threshold,
        ml_confidence=confidence,
    )

    return decision
