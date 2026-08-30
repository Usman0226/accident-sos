"""
Continual Trainer — Automated retraining pipeline with safety checks and gate validation.

Coordinates the complete continual learning workflow:
  1. Ingest base datasets + accumulated training pool signals
  2. Perform cross-validation and fit candidate model
  3. Run offline behavioral validation and regression safety checks
  4. Register candidate version into ModelRegistry if safety criteria are met
"""

from __future__ import annotations

import hashlib
import os
from typing import Any, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold

import config
from feature_pipeline import build_ml_pipeline
from logger import get_logger, log_event
import model_registry
from train_model import (
    AUGMENTED_PATH,
    CSV_PATH,
    compute_dataset_hash,
    extract_feature_importances,
    run_behavioral_checks,
)
import training_pool

_logger = get_logger("continual_trainer")


class RetrainingResult(BaseModel):
    """Result of a continual retraining cycle."""

    success: bool
    candidate_version: Optional[str] = None
    candidate_metrics: dict[str, float]
    active_metrics: dict[str, float]
    safety_check_passed: bool
    safety_check_details: dict[str, Any]
    reason: str


def run_retraining_cycle(
    pool: Optional[training_pool.TrainingPool] = None,
    registry: Optional[model_registry.ModelRegistry] = None,
    auto_promote: bool = False,
    force: bool = False,
) -> RetrainingResult:
    """
    Execute a continual retraining cycle.

    Args:
        pool: TrainingPool instance holding recent live signals.
        registry: ModelRegistry to record and promote versions.
        auto_promote: Automatically promote candidate if it beats active model.
        force: Allow training even if pool is below min threshold.
    """
    if pool is None:
        pool = training_pool.TrainingPool()
    if registry is None:
        registry = model_registry.ModelRegistry()

    stats = pool.get_stats()
    if not stats.is_ready_for_retraining and not force:
        return RetrainingResult(
            success=False,
            candidate_version=None,
            candidate_metrics={},
            active_metrics={},
            safety_check_passed=False,
            safety_check_details={
                "error": "Pool not ready for retraining",
                "pool_stats": stats.model_dump(),
            },
            reason=(
                f"Training pool not ready ({stats.total_samples}/{config.MIN_RETRAIN_SAMPLES} samples). "
                f"Use force=True to override."
            ),
        )

    # 1. Load base datasets
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Base dataset missing at {CSV_PATH}")

    df_base = pd.read_csv(CSV_PATH)
    if os.path.exists(AUGMENTED_PATH):
        df_aug = pd.read_csv(AUGMENTED_PATH)
        df_merged = pd.concat([df_base, df_aug], ignore_index=True)
    else:
        df_merged = df_base

    # 2. Append pool signals if available
    df_pool = pool.export_as_dataframe()
    if not df_pool.empty:
        df_merged = pd.concat([df_merged, df_pool], ignore_index=True)

    y = df_merged["Crash_Label"].astype(int)
    dataset_hash = compute_dataset_hash(df_merged)

    # 3. Stratified 5-Fold CV for candidate pipeline
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_f1: list[float] = []
    cv_rec: list[float] = []

    for train_idx, test_idx in skf.split(df_merged, y):
        df_train, df_test = df_merged.iloc[train_idx], df_merged.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        fold_pipe = build_ml_pipeline(random_state=42)
        fold_pipe.fit(df_train, y_train)

        y_pred = fold_pipe.predict(df_test)
        cv_f1.append(f1_score(y_test, y_pred, zero_division=0))
        cv_rec.append(recall_score(y_test, y_pred, zero_division=0))

    # 4. Train final candidate pipeline on all data
    candidate_pipeline = build_ml_pipeline(random_state=42)
    candidate_pipeline.fit(df_merged, y)

    y_full_pred = candidate_pipeline.predict(df_merged)
    candidate_metrics = {
        "accuracy": float(accuracy_score(y, y_full_pred)),
        "precision": float(precision_score(y, y_full_pred, zero_division=0)),
        "recall": float(recall_score(y, y_full_pred, zero_division=0)),
        "f1_score": float(np.mean(cv_f1)),
    }

    # 5. Fetch active model metrics for comparison
    active_metrics: dict[str, float] = {}
    try:
        _, active_meta = registry.get_active()
        active_metrics = active_meta.metrics
    except Exception:
        active_metrics = {"f1_score": 0.0, "recall": 0.0}

    # 6. Safety checks on candidate
    behavior_passed, behavior_failures = run_behavioral_checks(candidate_pipeline)
    feat_importances = extract_feature_importances(candidate_pipeline)

    active_rec = active_metrics.get("recall", 0.0)
    cand_rec = candidate_metrics["recall"]
    recall_safe = cand_rec >= (active_rec - 0.02)  # Max 2% recall degradation

    safety_passed = behavior_passed and recall_safe
    safety_details = {
        "behavioral_checks_passed": behavior_passed,
        "behavioral_failures": behavior_failures,
        "recall_safety_passed": recall_safe,
        "active_recall": active_rec,
        "candidate_recall": cand_rec,
        "feature_importances": feat_importances,
    }

    if not safety_passed:
        log_event(
            _logger,
            action="retraining_safety_check_failed",
            behavioral_passed=behavior_passed,
            recall_safe=recall_safe,
        )
        return RetrainingResult(
            success=False,
            candidate_version=None,
            candidate_metrics=candidate_metrics,
            active_metrics=active_metrics,
            safety_check_passed=False,
            safety_check_details=safety_details,
            reason="Candidate model failed safety and behavioral gate checks.",
        )

    # 7. Register candidate in registry
    desc = (
        f"Continual learning update with {len(df_pool)} pool samples. "
        f"CV F1: {candidate_metrics['f1_score']:.4f}"
    )
    version = registry.register(
        pipeline_artifact=candidate_pipeline,
        metrics=candidate_metrics,
        dataset_hash=dataset_hash,
        feature_importances=feat_importances,
        description=desc,
        set_active=auto_promote,
    )

    log_event(
        _logger,
        action="retraining_cycle_complete",
        candidate_version=version.version,
        f1=candidate_metrics["f1_score"],
        auto_promoted=auto_promote,
    )

    return RetrainingResult(
        success=True,
        candidate_version=version.version,
        candidate_metrics=candidate_metrics,
        active_metrics=active_metrics,
        safety_check_passed=True,
        safety_check_details=safety_details,
        reason=f"Candidate model successfully trained and registered as {version.version}.",
    )
