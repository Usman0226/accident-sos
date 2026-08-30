"""
Unit tests for PSI-based Drift Detector.
"""

import numpy as np
import pytest

from drift_detector import DriftDetector


def test_drift_detector_initialization():
    """Verify reference building from data."""
    ref_data = {
        "impact_g": list(np.random.normal(1.0, 0.2, 500)),
        "gyro_delta": list(np.random.normal(5.0, 1.0, 500)),
        "Speed_kmh": list(np.random.normal(40.0, 10.0, 500)),
    }
    detector = DriftDetector(reference_data=ref_data, window_size=200, num_bins=10)
    stats = detector.get_stats()
    assert len(stats["features_tracked"]) == 3


def test_drift_detector_in_distribution_no_drift():
    """Data drawn from same distribution should have low PSI (<0.1)."""
    np.random.seed(42)
    ref_data = {
        "impact_g": list(np.random.normal(1.0, 0.2, 500)),
        "gyro_delta": list(np.random.normal(5.0, 1.0, 500)),
        "Speed_kmh": list(np.random.normal(40.0, 10.0, 500)),
    }
    detector = DriftDetector(reference_data=ref_data, window_size=200, num_bins=10)

    # Ingest 100 samples from identical distribution
    for _ in range(100):
        detector.record_event({
            "impact_g": float(np.random.normal(1.0, 0.2)),
            "gyro_delta": float(np.random.normal(5.0, 1.0)),
            "Speed_kmh": float(np.random.normal(40.0, 10.0)),
        })

    reports = detector.compute_drift()
    assert len(reports) == 3
    for r in reports:
        assert r.is_drifted is False
        assert r.psi_score < 0.2


def test_drift_detector_out_of_distribution_flags_drift():
    """Severely shifted distribution must trigger is_drifted=True."""
    np.random.seed(42)
    ref_data = {
        "impact_g": list(np.random.normal(1.0, 0.2, 500)),
        "gyro_delta": list(np.random.normal(5.0, 1.0, 500)),
        "Speed_kmh": list(np.random.normal(40.0, 10.0, 500)),
    }
    detector = DriftDetector(reference_data=ref_data, window_size=200, num_bins=10, psi_threshold=0.2)

    # Ingest heavily shifted data (e.g. speed shifted to 150 km/h)
    for _ in range(100):
        detector.record_event({
            "impact_g": float(np.random.normal(8.0, 0.5)),
            "gyro_delta": float(np.random.normal(80.0, 10.0)),
            "Speed_kmh": float(np.random.normal(150.0, 10.0)),
        })

    reports = detector.compute_drift()
    drifted_features = [r.feature_name for r in reports if r.is_drifted]
    assert len(drifted_features) > 0
    assert detector.is_any_drifted() is True
