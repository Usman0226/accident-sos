"""
Rule-based accident classification engine.

Pure function, no side effects, fully testable.

Scoring model:
  1. Base confidence from impact_g × gyro_delta thresholds
  2. Pothole reinforcement penalty (high impact, very low gyro)
  3. Speed context modifier (near-zero penalty, high-speed boost)
  4. Severe impact boost (impact_g > 10)
  5. Decision cutoff at configurable confidence threshold
"""

from __future__ import annotations

import config
from models import ClassificationResult, DeviceContext, ImpactPayload


def classify(impact: ImpactPayload, context: DeviceContext) -> ClassificationResult:
    """
    Classify an impact event as accident or not.

    Args:
        impact:  Validated impact payload from the device.
        context: Assembled device context (speed, status, cached GPS).

    Returns:
        ClassificationResult with decision, confidence [0.0–1.0], and
        human-readable reason string.
    """
    reasons: list[str] = []

    high_impact = impact.impact_g > config.IMPACT_G_THRESHOLD
    high_gyro = impact.gyro_delta > config.GYRO_DELTA_THRESHOLD

    # ── Base scoring ─────────────────────────────────────────────────────
    if high_impact and high_gyro:
        confidence = 0.70
        reasons.append(
            f"impact_g={impact.impact_g:.1f} (>{config.IMPACT_G_THRESHOLD})"
        )
        reasons.append(
            f"gyro_delta={impact.gyro_delta:.1f} (>{config.GYRO_DELTA_THRESHOLD})"
        )
    elif high_impact:
        # Edge case #1: high accel + low rotation → pothole / hard brake
        confidence = 0.20
        reasons.append(
            f"impact_g={impact.impact_g:.1f} (>{config.IMPACT_G_THRESHOLD}) "
            f"but low gyro_delta={impact.gyro_delta:.1f} "
            f"— possible pothole/hard brake"
        )
    elif high_gyro:
        confidence = 0.15
        reasons.append(
            f"gyro_delta={impact.gyro_delta:.1f} (>{config.GYRO_DELTA_THRESHOLD}) "
            f"but low impact_g={impact.impact_g:.1f}"
        )
    else:
        confidence = 0.05
        reasons.append(
            f"impact_g={impact.impact_g:.1f} and "
            f"gyro_delta={impact.gyro_delta:.1f} both below thresholds"
        )

    # ── Pothole reinforcement: high impact + very low gyro ───────────────
    if high_impact and impact.gyro_delta < config.GYRO_VERY_LOW:
        confidence *= 0.5
        reasons.append(
            f"very low gyro_delta (<{config.GYRO_VERY_LOW}) "
            f"— strong pothole/brake indicator"
        )

    # ── Speed context (edge case #2) ─────────────────────────────────────
    if context.recent_speed is not None:
        if context.recent_speed < config.SPEED_LOW_THRESHOLD:
            confidence *= 0.3
            reasons.append(
                f"speed={context.recent_speed:.1f} km/h (~0) "
                f"— near-standstill penalty"
            )
        elif context.recent_speed > config.SPEED_HIGH_BOOST:
            confidence = min(confidence + 0.15, 1.0)
            reasons.append(
                f"speed={context.recent_speed:.1f} km/h "
                f"(>{config.SPEED_HIGH_BOOST}) — moving at significant speed"
            )
    else:
        reasons.append("no speed data available — neutral")

    # ── Severe impact boost ──────────────────────────────────────────────
    if impact.impact_g > config.SEVERE_IMPACT_G:
        confidence = min(confidence + 0.10, 1.0)
        reasons.append(
            f"severe impact_g={impact.impact_g:.1f} (>{config.SEVERE_IMPACT_G})"
        )

    # ── Clamp and decide ─────────────────────────────────────────────────
    confidence = round(max(0.0, min(1.0, confidence)), 2)
    decision = (
        "accident"
        if confidence >= config.ACCIDENT_CONFIDENCE_CUTOFF
        else "no_accident"
    )

    return ClassificationResult(
        decision=decision,
        confidence=confidence,
        reason=" + ".join(reasons),
    )
