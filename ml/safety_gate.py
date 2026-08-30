"""
Deterministic Safety Gate — final guardrail on all ML/RL decisions.

Per README §12: "An adaptive model must never be allowed to freely
experiment with emergency suppression."

Safety invariants:
  1. NEVER suppress manual SOS
  2. NEVER suppress severe impact (impact_g > SEVERE_IMPACT_G)
  3. NEVER suppress high-speed non-pothole events (speed > SPEED_HIGH_BOOST & impact_g > IMPACT_G_THRESHOLD & gyro_delta >= GYRO_VERY_LOW)
  4. Enforce minimum confidence floor on physically significant collisions
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

import config
from logger import get_logger, log_event
from models import ClassificationResult, DeviceContext, ImpactPayload

_logger = get_logger("safety_gate")


class SafetyGateResult(BaseModel):
    """Output of the safety gate layer."""

    final_decision: str  # "accident" | "no_accident"
    original_decision: str  # what ML said
    was_overridden: bool
    override_reason: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class SafetyGate:
    """
    Deterministic Safety Gate enforcing non-negotiable safety guardrails.
    """

    def __init__(
        self,
        severe_impact_g: float = config.SEVERE_IMPACT_G,
        impact_threshold: float = config.IMPACT_G_THRESHOLD,
        speed_high: float = config.SPEED_HIGH_BOOST,
        confidence_floor: float = config.SAFETY_MIN_CONFIDENCE_FLOOR,
        max_suppression_rate: float = config.SAFETY_MAX_SUPPRESSION_RATE,
        rolling_window: int = config.SAFETY_ROLLING_WINDOW,
    ) -> None:
        self._severe_impact_g = severe_impact_g
        self._impact_threshold = impact_threshold
        self._speed_high = speed_high
        self._confidence_floor = confidence_floor
        self._total_evaluated = 0

    @property
    def total_decisions(self) -> int:
        return self._total_evaluated

    def evaluate(
        self,
        ml_result: ClassificationResult,
        impact: ImpactPayload,
        context: DeviceContext,
        is_manual_sos: bool = False,
    ) -> SafetyGateResult:
        """
        Apply deterministic safety constraints to an ML decision.
        """
        self._total_evaluated += 1
        original = ml_result.decision
        confidence = ml_result.confidence

        # ── Rule 1: NEVER suppress manual SOS ────────────────────────────
        if is_manual_sos:
            result = SafetyGateResult(
                final_decision="accident",
                original_decision=original,
                was_overridden=original != "accident",
                override_reason="manual_sos_override" if original != "accident" else None,
                confidence=max(confidence, 0.95),
            )
            self._log_decision(result, impact)
            return result

        # ── Rule 2: NEVER suppress severe impact ─────────────────────────
        if impact.impact_g > self._severe_impact_g and original == "no_accident":
            result = SafetyGateResult(
                final_decision="accident",
                original_decision=original,
                was_overridden=True,
                override_reason=(
                    f"severe_impact_override: impact_g={impact.impact_g:.1f} "
                    f"> threshold={self._severe_impact_g}"
                ),
                confidence=max(confidence, 0.85),
            )
            self._log_decision(result, impact)
            return result

        # ── Rule 3: NEVER suppress high-speed events with rotational component ──
        speed = context.recent_speed
        if (
            speed is not None
            and speed > self._speed_high
            and impact.impact_g > self._impact_threshold
            and impact.gyro_delta >= config.GYRO_VERY_LOW
            and original == "no_accident"
        ):
            result = SafetyGateResult(
                final_decision="accident",
                original_decision=original,
                was_overridden=True,
                override_reason=(
                    f"high_speed_impact_override: speed={speed:.1f}km/h "
                    f"+ impact_g={impact.impact_g:.1f}"
                ),
                confidence=max(confidence, 0.80),
            )
            self._log_decision(result, impact)
            return result

        # ── Rule 4: Confidence floor — uncertain no_accident → escalate ──
        if original == "no_accident" and confidence < self._confidence_floor:
            if impact.impact_g > self._impact_threshold and impact.gyro_delta > config.GYRO_DELTA_THRESHOLD:
                result = SafetyGateResult(
                    final_decision="accident",
                    original_decision=original,
                    was_overridden=True,
                    override_reason=(
                        f"low_confidence_escalation: confidence={confidence:.2f} "
                        f"< floor={self._confidence_floor}"
                    ),
                    confidence=self._confidence_floor,
                )
                self._log_decision(result, impact)
                return result

        # ── No override — pass through ML decision ──────────────────────
        result = SafetyGateResult(
            final_decision=original,
            original_decision=original,
            was_overridden=False,
            override_reason=None,
            confidence=confidence,
        )
        self._log_decision(result, impact)
        return result

    def _log_decision(
        self, result: SafetyGateResult, impact: ImpactPayload
    ) -> None:
        """Emit structured audit log for every safety gate decision."""
        log_event(
            _logger,
            action="safety_gate_decision",
            resource_id=impact.device_id,
            actor="safety_gate",
            final_decision=result.final_decision,
            original_decision=result.original_decision,
            was_overridden=result.was_overridden,
            override_reason=result.override_reason or "none",
            confidence=result.confidence,
            impact_g=impact.impact_g,
        )

    def get_stats(self) -> dict:
        """Return current safety gate statistics."""
        return {
            "total_decisions": self.total_decisions,
            "severe_impact_threshold": self._severe_impact_g,
            "confidence_floor": self._confidence_floor,
        }
