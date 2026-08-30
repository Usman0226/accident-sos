"""
Training Pool — Curated pseudo-label and operational outcome signal collection.

Collects high-confidence pseudo-labels and ground-truth operational signals
(human cancellation, responder confirmation, operator manual feedback) to form
a validated training pool for continual learning without manual labeling dependencies.
"""

from __future__ import annotations

import csv
import json
import os
import time
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, Field

import config
from logger import get_logger, log_event

_logger = get_logger("training_pool")


class TrainingSignal(BaseModel):
    """A single training sample with provenance and metadata."""

    impact_g: float
    gyro_delta: float
    speed_kmh: float
    pseudo_label: int  # 0 or 1
    confidence: float
    source: str  # "high_confidence_ml" | "human_cancellation" | "sos_confirmed" | "manual_feedback"
    event_id: str
    device_id: str
    timestamp: float = Field(default_factory=time.time)


class PoolStats(BaseModel):
    """Summary statistics of current training pool."""

    total_samples: int
    crash_count: int
    normal_count: int
    crash_ratio: float
    is_ready_for_retraining: bool
    sources: dict[str, int]


class TrainingPool:
    """
    Manages live training data signals with deduplication and quality gating.
    """

    def __init__(self, pool_dir: str = config.TRAINING_POOL_DIR) -> None:
        self.pool_dir = os.path.abspath(pool_dir)
        os.makedirs(self.pool_dir, exist_ok=True)
        self.pool_file = os.path.join(self.pool_dir, "signals.jsonl")
        self._signals: list[TrainingSignal] = self._load_signals()

    def _load_signals(self) -> list[TrainingSignal]:
        signals: list[TrainingSignal] = []
        if os.path.exists(self.pool_file):
            try:
                with open(self.pool_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            signals.append(TrainingSignal.model_validate(data))
            except Exception as exc:
                log_event(
                    _logger,
                    action="pool_load_error",
                    error=str(exc),
                    path=self.pool_file,
                )
        return signals

    def add_signal(self, signal: TrainingSignal) -> bool:
        """
        Ingest a candidate training signal if it satisfies quality and confidence gates.
        """
        # Confidence gate for automated ML pseudo-labels
        if signal.source == "high_confidence_ml":
            if (
                signal.confidence < config.PSEUDO_LABEL_HIGH_CONFIDENCE
                and signal.confidence > config.PSEUDO_LABEL_LOW_CONFIDENCE
            ):
                # Ambiguous region — reject automated pseudo-label to avoid self-reinforcing errors
                log_event(
                    _logger,
                    action="signal_rejected_ambiguous",
                    event_id=signal.event_id,
                    confidence=signal.confidence,
                )
                return False

        # Deduplication check against recent signals
        for existing in self._signals[-200:]:
            if (
                abs(existing.impact_g - signal.impact_g) < 0.05
                and abs(existing.gyro_delta - signal.gyro_delta) < 0.1
                and abs(existing.speed_kmh - signal.speed_kmh) < 0.5
                and existing.pseudo_label == signal.pseudo_label
            ):
                return False

        self._signals.append(signal)

        # Append to disk
        with open(self.pool_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(signal.model_dump()) + "\n")

        log_event(
            _logger,
            action="signal_added",
            event_id=signal.event_id,
            source=signal.source,
            label=signal.pseudo_label,
            total_pool=len(self._signals),
        )
        return True

    def get_stats(self) -> PoolStats:
        """Calculate and return pool health metrics and retraining readiness."""
        total = len(self._signals)
        crashes = sum(1 for s in self._signals if s.pseudo_label == 1)
        normals = total - crashes
        ratio = (crashes / total) if total > 0 else 0.0

        sources: dict[str, int] = {}
        for s in self._signals:
            sources[s.source] = sources.get(s.source, 0) + 1

        is_ready = (
            total >= config.MIN_RETRAIN_SAMPLES
            and crashes >= 10
            and normals >= 10
            and config.RETRAIN_CLASS_BALANCE_MIN
            <= ratio
            <= config.RETRAIN_CLASS_BALANCE_MAX
        )

        return PoolStats(
            total_samples=total,
            crash_count=crashes,
            normal_count=normals,
            crash_ratio=round(ratio, 4),
            is_ready_for_retraining=is_ready,
            sources=sources,
        )

    def export_as_dataframe(self) -> pd.DataFrame:
        """Export pool signals as a DataFrame formatted for pipeline training."""
        if not self._signals:
            return pd.DataFrame()

        rows = []
        for s in self._signals:
            rows.append({
                "impact_g": s.impact_g,
                "gyro_delta": s.gyro_delta,
                "Speed_kmh": s.speed_kmh,
                "Crash_Label": s.pseudo_label,
            })
        return pd.DataFrame(rows)

    def clear(self) -> None:
        """Reset pool (used for testing or after major model promotions)."""
        self._signals.clear()
        if os.path.exists(self.pool_file):
            os.remove(self.pool_file)
