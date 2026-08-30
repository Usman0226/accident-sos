"""
API routes for Continual Learning and Training Pool management.

Exposes endpoints for querying pool statistics, ingesting ground-truth signals,
and triggering automated retraining cycles.
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query

import continual_trainer
from logger import get_logger, log_event
import model_registry
import training_pool

router = APIRouter(prefix="/api/ml/training", tags=["training"])
_logger = get_logger("routes.training")

_pool_instance: Optional[training_pool.TrainingPool] = None


def set_global_pool(pool: training_pool.TrainingPool) -> None:
    """Set global TrainingPool instance."""
    global _pool_instance
    _pool_instance = pool


def get_global_pool() -> training_pool.TrainingPool:
    """Get global TrainingPool instance or instantiate default."""
    global _pool_instance
    if _pool_instance is None:
        _pool_instance = training_pool.TrainingPool()
    return _pool_instance


@router.get("/pool/stats")
async def get_pool_stats() -> dict[str, Any]:
    """Retrieve training pool statistics and readiness for retraining."""
    try:
        pool = get_global_pool()
        stats = pool.get_stats()
        return stats.model_dump()
    except Exception as exc:
        log_event(_logger, action="get_pool_stats_error", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch pool stats: {exc}"
        ) from exc


@router.post("/signals")
async def add_training_signal(signal: training_pool.TrainingSignal) -> dict[str, Any]:
    """Ingest a training signal into the pool."""
    try:
        pool = get_global_pool()
        accepted = pool.add_signal(signal)
        return {
            "accepted": accepted,
            "event_id": signal.event_id,
            "message": "Signal accepted into pool" if accepted else "Signal filtered/duplicate",
        }
    except Exception as exc:
        log_event(_logger, action="add_signal_error", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Failed to ingest signal: {exc}"
        ) from exc


@router.post("/retrain")
async def trigger_retraining(
    auto_promote: bool = Query(False, description="Promote candidate if safe"),
    force: bool = Query(False, description="Force retrain even if pool is small"),
) -> dict[str, Any]:
    """Execute a continual retraining cycle."""
    try:
        pool = get_global_pool()
        reg = model_registry.ModelRegistry()
        result = continual_trainer.run_retraining_cycle(
            pool=pool,
            registry=reg,
            auto_promote=auto_promote,
            force=force,
        )
        return result.model_dump()
    except Exception as exc:
        log_event(_logger, action="retraining_trigger_error", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Retraining cycle failed: {exc}"
        ) from exc
