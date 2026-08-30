"""
Impact event processing and multi-stage classification endpoint.

Orchestrates the complete intelligence chain:
  1. Auto-registration & Debouncing
  2. Telemetry Context Assembly & GPS Resolution
  3. ML Pipeline Inference (Calibrated Random Forest)
  4. Live Drift Distribution Tracking
  5. Context-Aware Policy Evaluation (escalate/observe/reject)
  6. Deterministic Safety Gate Invariant Enforcement
  7. High-confidence Training Signal Collection
  8. Event Lifecycle State Initialization
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException

import decision_policy
import device_manager
import event_manager
from logger import get_logger, log_event
import ml_classifier
from models import ClassificationResult, GPSCoord, ImpactPayload
from routes.drift import get_global_detector
from routes.training import get_global_pool
from safety_gate import SafetyGate, SafetyGateResult
import training_pool

router = APIRouter(prefix="/api", tags=["impact"])
_logger = get_logger("routes.impact")

_safety_gate_instance: Optional[SafetyGate] = None


def set_global_safety_gate(gate: SafetyGate) -> None:
    """Set global SafetyGate instance."""
    global _safety_gate_instance
    _safety_gate_instance = gate


def get_global_safety_gate() -> SafetyGate:
    """Get global SafetyGate instance or instantiate default."""
    global _safety_gate_instance
    if _safety_gate_instance is None:
        _safety_gate_instance = SafetyGate()
    return _safety_gate_instance


@router.post("/impact")
async def receive_impact(payload: ImpactPayload):
    """
    Process an impact event through the full ML intelligence & Safety Gate pipeline.
    """
    try:
        # Step 1: Auto-register unknown device
        device_manager.register_or_get(payload.device_id)

        # Step 2: Debounce check — same device within window
        debounced, existing_event_id = event_manager.is_debounced(
            payload.device_id
        )
        if debounced:
            log_event(
                _logger,
                action="impact_debounced",
                resource_id=existing_event_id,
                actor=payload.device_id,
            )
            return {
                "event_id": existing_event_id,
                "debounced": True,
                "message": "Impact already being processed for this device",
            }

        # Step 3: Build device context from heartbeat buffer
        context = device_manager.build_context(payload.device_id)

        # Step 4: Resolve GPS — fall back to cache if fix is false
        if payload.gps_fix:
            gps = GPSCoord(
                lat=payload.gps_lat,
                lon=payload.gps_lon,
                is_approximate=False,
            )
            device_manager.cache_gps_from_impact(payload)
        else:
            cached = device_manager.get_last_known_gps(payload.device_id)
            if cached is not None:
                gps = GPSCoord(
                    lat=cached.lat, lon=cached.lon, is_approximate=True
                )
            else:
                gps = GPSCoord(
                    lat=payload.gps_lat,
                    lon=payload.gps_lon,
                    is_approximate=True,
                )
            log_event(
                _logger,
                action="gps_fallback",
                resource_id=payload.device_id,
                used_cache=cached is not None,
            )

        # Step 5: Execute ML Model Inference
        ml_result = ml_classifier.classify_ml(payload, context)

        # Step 6: Record Live Features in Drift Detector
        speed_val = context.recent_speed if context.recent_speed is not None else 0.0
        detector = get_global_detector()
        detector.record_event({
            "impact_g": payload.impact_g,
            "gyro_delta": payload.gyro_delta,
            "Speed_kmh": speed_val,
        })

        # Step 7: Evaluate Context-Aware Decision Policy
        policy = decision_policy.evaluate_policy(ml_result, payload, context)

        if policy.action == "escalate":
            candidate_decision = "accident"
            candidate_conf = max(ml_result.confidence, 0.65)
        elif policy.action == "observe":
            candidate_decision = "no_accident"
            candidate_conf = min(ml_result.confidence, 0.45)
        else:  # reject
            candidate_decision = "no_accident"
            candidate_conf = min(ml_result.confidence, 0.35)

        candidate_result = ClassificationResult(
            decision=candidate_decision,
            confidence=candidate_conf,
            reason=f"Policy: {policy.action} ({policy.reason})",
        )

        # Step 8: Apply Deterministic Safety Gate Guardrails
        gate = get_global_safety_gate()
        is_manual_sos = getattr(payload, "type", "impact") == "sos"
        safety_result: SafetyGateResult = gate.evaluate(
            ml_result=candidate_result,
            impact=payload,
            context=context,
            is_manual_sos=is_manual_sos,
        )

        # Build combined explainable reason
        reason_parts = [
            f"impact_g={payload.impact_g:.2f}",
            f"gyro_delta={payload.gyro_delta:.2f}",
            ml_result.reason,
            f"Policy: {policy.action} ({policy.reason})",
        ]
        if safety_result.was_overridden:
            reason_parts.append(f"SAFETY GATE OVERRIDE: {safety_result.override_reason}")
        combined_reason = " | ".join(reason_parts)

        final_result = ClassificationResult(
            decision=safety_result.final_decision,
            confidence=safety_result.confidence,
            reason=combined_reason,
        )

        # Step 9: Ingest High-Confidence Signal into Continual Training Pool
        try:
            pool = get_global_pool()
            pseudo_label = 1 if safety_result.final_decision == "accident" else 0
            pool.add_signal(
                training_pool.TrainingSignal(
                    impact_g=payload.impact_g,
                    gyro_delta=payload.gyro_delta,
                    speed_kmh=speed_val,
                    pseudo_label=pseudo_label,
                    confidence=safety_result.confidence,
                    source="high_confidence_ml",
                    event_id=f"evt_tmp_{payload.device_id}",
                    device_id=payload.device_id,
                )
            )
        except Exception as pool_err:
            log_event(
                _logger,
                action="pool_ingest_silent_fail",
                error=str(pool_err),
            )

        # Step 10: Create Persisted Event in State Machine
        event = event_manager.create_event(payload, final_result, gps)

        return {
            "event_id": event.event_id,
            "device_id": event.device_id,
            "decision": event.decision,
            "confidence": event.confidence,
            "reason": event.reason,
            "policy_action": policy.action,
            "safety_overridden": safety_result.was_overridden,
            "gps": event.gps.model_dump(),
            "status": event.status.value,
        }

    except Exception as exc:
        log_event(
            _logger,
            action="impact_error",
            resource_id=payload.device_id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to process impact event: {exc}"
        ) from exc
