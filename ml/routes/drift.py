"""
API routes for Drift Detection and distribution monitoring.

Exposes endpoints to query current feature drift metrics, historical drift
reports, and manual reference updates.
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException

import drift_detector
from logger import get_logger, log_event

router = APIRouter(prefix="/api/ml/drift", tags=["drift"])
_logger = get_logger("routes.drift")

# Global singleton or reference holder managed by app lifespan
_detector_instance: Optional[drift_detector.DriftDetector] = None


def set_global_detector(detector: drift_detector.DriftDetector) -> None:
    """Set global DriftDetector instance."""
    global _detector_instance
    _detector_instance = detector


def get_global_detector() -> drift_detector.DriftDetector:
    """Retrieve global DriftDetector instance or instantiate fallback."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = drift_detector.DriftDetector()
    return _detector_instance


@router.get("")
async def get_drift_status() -> dict[str, Any]:
    """
    Get current feature drift status evaluated via Population Stability Index (PSI).
    """
    try:
        detector = get_global_detector()
        reports = detector.compute_drift()
        stats = detector.get_stats()
        is_drifted = any(r.is_drifted for r in reports)

        return {
            "status": "drift_detected" if is_drifted else "stable",
            "is_drifted": is_drifted,
            "reports": [r.model_dump() for r in reports],
            "stats": stats,
        }
    except Exception as exc:
        log_event(_logger, action="get_drift_status_error", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Failed to compute drift status: {exc}"
        ) from exc


@router.get("/history")
async def get_drift_history(limit: int = 50) -> dict[str, Any]:
    """
    Retrieve recent historical drift evaluation runs.
    """
    try:
        detector = get_global_detector()
        history = detector.get_history(limit=limit)
        serialized_history = [
            [report.model_dump() for report in run] for run in history
        ]
        return {
            "history_count": len(serialized_history),
            "runs": serialized_history,
        }
    except Exception as exc:
        log_event(_logger, action="get_drift_history_error", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve drift history: {exc}"
        ) from exc
