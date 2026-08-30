"""
Drift Detector — PSI-based feature distribution monitoring.

Detects when live event distributions shift from the training-time
reference, signaling potential model staleness or concept drift.

Uses Population Stability Index (PSI):
  PSI < 0.1  → no significant drift
  PSI 0.1–0.2 → moderate drift (monitor)
  PSI > 0.2 → significant drift (action needed)
"""

from __future__ import annotations

import time
from collections import deque
from typing import Optional

import numpy as np
from pydantic import BaseModel

import config
from logger import get_logger, log_event

_logger = get_logger("drift_detector")

FEATURE_NAMES = ["impact_g", "gyro_delta", "Speed_kmh"]


class DriftReport(BaseModel):
    """Drift assessment for a single feature."""

    feature_name: str
    psi_score: float
    is_drifted: bool
    sample_count: int
    timestamp: float


class DriftDetector:
    """
    Monitors feature distribution drift using PSI.

    Thread-safety: single-threaded asyncio — deque mutations are safe.
    """

    def __init__(
        self,
        reference_data: Optional[dict[str, list[float]]] = None,
        psi_threshold: float = config.DRIFT_PSI_THRESHOLD,
        window_size: int = config.DRIFT_WINDOW_SIZE,
        num_bins: int = config.DRIFT_NUM_BINS,
    ) -> None:
        self._psi_threshold = psi_threshold
        self._num_bins = num_bins
        self._window_size = window_size

        # Per-feature rolling windows
        self._live_windows: dict[str, deque[float]] = {
            name: deque(maxlen=window_size) for name in FEATURE_NAMES
        }

        # Reference distributions (binned)
        self._reference_bins: dict[str, np.ndarray] = {}
        self._bin_edges: dict[str, np.ndarray] = {}

        # History of drift reports
        self._history: list[list[DriftReport]] = []

        if reference_data is not None:
            self._build_reference(reference_data)

    def _build_reference(self, reference_data: dict[str, list[float]]) -> None:
        """Build reference histograms from training data with open outer bounds."""
        for name in FEATURE_NAMES:
            values = reference_data.get(name, [])
            if not values:
                continue

            arr = np.array(values, dtype=np.float64)
            _, raw_edges = np.histogram(arr, bins=self._num_bins)

            # Open outer bounds [-inf, ..., +inf] to capture full live range
            bins = np.concatenate([[-np.inf], raw_edges[1:-1], [np.inf]])
            counts, _ = np.histogram(arr, bins=bins)

            # Normalize to proportions, add small epsilon to avoid division by zero
            proportions = counts / counts.sum()
            proportions = np.where(proportions == 0, 1e-6, proportions)
            # Re-normalize
            proportions = proportions / proportions.sum()

            self._reference_bins[name] = proportions
            self._bin_edges[name] = bins

        log_event(
            _logger,
            action="reference_built",
            features=list(self._reference_bins.keys()),
            num_bins=self._num_bins,
        )

    def set_reference_from_dataframe(self, df) -> None:
        """Build reference from a pandas DataFrame (convenience method)."""
        reference_data: dict[str, list[float]] = {}
        for name in FEATURE_NAMES:
            if name in df.columns:
                reference_data[name] = df[name].astype(float).tolist()
            elif name == "impact_g" and "Motion_Intensity" in df.columns:
                reference_data[name] = (
                    (df["Motion_Intensity"].astype(float) - 9.81).abs().tolist()
                )
        self._build_reference(reference_data)

    def record_event(self, features: dict[str, float]) -> None:
        """Record a single event's features into the rolling windows."""
        for name in FEATURE_NAMES:
            value = features.get(name)
            if value is not None:
                self._live_windows[name].append(float(value))

    def compute_drift(self) -> list[DriftReport]:
        """Compute PSI for each feature and return drift reports."""
        reports: list[DriftReport] = []
        now = time.time()

        for name in FEATURE_NAMES:
            if name not in self._reference_bins:
                continue

            window = self._live_windows[name]
            if len(window) < self._num_bins * 2:
                # Not enough samples for reliable PSI
                reports.append(
                    DriftReport(
                        feature_name=name,
                        psi_score=0.0,
                        is_drifted=False,
                        sample_count=len(window),
                        timestamp=now,
                    )
                )
                continue

            # Bin live data using open edges
            edges = self._bin_edges[name]
            live_arr = np.array(window, dtype=np.float64)
            live_counts, _ = np.histogram(live_arr, bins=edges)

            total_live = live_counts.sum()
            if total_live == 0:
                continue

            live_proportions = live_counts / total_live
            live_proportions = np.where(
                live_proportions == 0, 1e-6, live_proportions
            )
            live_proportions = live_proportions / live_proportions.sum()

            ref = self._reference_bins[name]

            # PSI = Σ (p_live - p_ref) * ln(p_live / p_ref)
            psi = float(
                np.sum(
                    (live_proportions - ref) * np.log(live_proportions / ref)
                )
            )
            psi = max(0.0, psi)

            is_drifted = psi > self._psi_threshold

            reports.append(
                DriftReport(
                    feature_name=name,
                    psi_score=round(psi, 6),
                    is_drifted=is_drifted,
                    sample_count=len(window),
                    timestamp=now,
                )
            )

            if is_drifted:
                log_event(
                    _logger,
                    action="drift_detected",
                    feature=name,
                    psi=round(psi, 6),
                    threshold=self._psi_threshold,
                    sample_count=len(window),
                )

        if reports:
            self._history.append(reports)

        return reports

    def is_any_drifted(self) -> bool:
        """Quick check: is any feature currently drifted?"""
        reports = self.compute_drift()
        return any(r.is_drifted for r in reports)

    def get_history(self, limit: int = 50) -> list[list[DriftReport]]:
        """Return recent drift report history."""
        return self._history[-limit:]

    def get_stats(self) -> dict:
        """Return current detector state."""
        return {
            "features_tracked": list(self._reference_bins.keys()),
            "window_size": self._window_size,
            "psi_threshold": self._psi_threshold,
            "samples_collected": {
                name: len(self._live_windows[name]) for name in FEATURE_NAMES
            },
            "history_entries": len(self._history),
        }
