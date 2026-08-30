"""
Unit tests for the Broader Validation Suite matrix.
"""

import joblib
import pytest

from ml_classifier import load_pipeline
from validation_suite import run_validation_suite, generate_validation_scenarios


def test_validation_suite_matrix_coverage():
    """Ensure validation scenarios cover all required categories."""
    scenarios = generate_validation_scenarios()
    categories = {sc.category for sc in scenarios}
    assert "road_surface" in categories
    assert "false_alarm" in categories
    assert "severe_crash" in categories
    assert "normal_driving" in categories
    assert len(scenarios) >= 10


def test_validation_suite_on_trained_pipeline():
    """Verify that current production pipeline passes the full validation suite."""
    pipeline = load_pipeline()
    report = run_validation_suite(pipeline)
    assert report.total_scenarios >= 10
    assert report.all_passed is True
    assert report.pass_rate == 1.0
