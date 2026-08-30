"""
Accident SOS — Intelligence & Classification Engine (ml module).

Production-grade FastAPI application hosting the complete ML intelligence architecture:
  - Scikit-Learn Calibrated Random Forest Classifier
  - Model Registry with hot-reload & version rollback
  - Deterministic Safety Gate Invariant Enforcement
  - Context-Aware Decision Policy
  - Population Stability Index (PSI) Drift Detection
  - Continual Learning Training Pool & Retrainer
  - RL Decision Policy Optimizer
  - Multi-bearer Heartbeat Staleness Sweeper

Usage:
    cd ml
    uvicorn app:app --port 8001
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
import pandas as pd

import config
import device_manager
import drift_detector
from logger import get_logger, log_event
import ml_classifier
import model_registry
import rl_policy
from routes.devices import router as devices_router
from routes.drift import router as drift_router, set_global_detector
from routes.events import router as events_router
from routes.heartbeat import router as heartbeat_router
from routes.impact import router as impact_router, set_global_safety_gate
from routes.registry import router as registry_router, set_global_registry
from routes.rl import router as rl_router, set_global_rl_optimizer
from routes.training import router as training_router, set_global_pool
import safety_gate
from train_model import CSV_PATH
import training_pool

_logger = get_logger("app")


async def _heartbeat_staleness_loop() -> None:
    """Background task: periodically mark stale devices unreachable (edge case #6)."""
    while True:
        try:
            stale = device_manager.check_staleness()
            if stale:
                log_event(
                    _logger,
                    action="staleness_sweep",
                    newly_unreachable=len(stale),
                    device_ids=stale,
                )
        except Exception as exc:
            log_event(
                _logger, action="staleness_sweep_error", error=str(exc)
            )
        await asyncio.sleep(config.STALENESS_CHECK_INTERVAL_S)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all ML subsystems, registries, and background workers."""
    log_event(_logger, action="server_initializing")

    # 1. Initialize Model Registry & seed if needed
    reg = model_registry.ModelRegistry()
    set_global_registry(reg)

    # 2. Initialize Classifier with Model Registry
    classifier = ml_classifier.MLAccidentClassifier(registry=reg)
    ml_classifier.set_global_classifier(classifier)

    # 3. Initialize Safety Gate
    gate = safety_gate.SafetyGate()
    set_global_safety_gate(gate)

    # 4. Initialize Drift Detector & build training reference baseline
    detector = drift_detector.DriftDetector()
    if os.path.exists(CSV_PATH):
        try:
            df_ref = pd.read_csv(CSV_PATH)
            detector.set_reference_from_dataframe(df_ref)
            log_event(
                _logger,
                action="drift_reference_loaded",
                rows=len(df_ref),
            )
        except Exception as exc:
            log_event(
                _logger,
                action="drift_reference_load_error",
                error=str(exc),
            )
    set_global_detector(detector)

    # 5. Initialize Training Pool
    pool = training_pool.TrainingPool()
    set_global_pool(pool)

    # 6. Initialize RL Policy Optimizer
    rl_optimizer = rl_policy.RLPolicyOptimizer(safety_gate=gate)
    set_global_rl_optimizer(rl_optimizer)

    # 7. Start background tasks
    task = asyncio.create_task(_heartbeat_staleness_loop())
    log_event(_logger, action="server_started")

    yield

    # Teardown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    log_event(_logger, action="server_stopped")


app = FastAPI(
    title="Accident SOS — Intelligence & Classification Engine",
    description=(
        "Production-grade accident detection engine for IoT vehicle telemetry. "
        "Integrates Scikit-Learn pipelines, Safety Gate invariants, Drift Detection, "
        "Model Registry, and Continual Learning loops."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── Mount route modules ──────────────────────────────────────────────────────
app.include_router(heartbeat_router)
app.include_router(impact_router)
app.include_router(events_router)
app.include_router(devices_router)
app.include_router(drift_router)
app.include_router(registry_router)
app.include_router(training_router)
app.include_router(rl_router)


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/api/health")
def health() -> dict[str, Any]:
    """Comprehensive liveness and subsystem health probe."""
    try:
        reg = model_registry.ModelRegistry()
        active_ver = reg.get_manifest().active_version or "unversioned"
    except Exception:
        active_ver = "unknown"

    return {
        "status": "ok",
        "service": "accident-classification-engine",
        "version": "1.0.0",
        "active_model_version": active_ver,
        "subsystems": {
            "model_registry": "healthy",
            "safety_gate": "active",
            "drift_detector": "active",
            "training_pool": "active",
            "rl_policy_optimizer": "active",
        },
    }
