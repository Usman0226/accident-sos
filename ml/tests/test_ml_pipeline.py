"""
Unit test suite for Scikit-Learn ML Pipeline and .pkl model serialization.
"""

import os
import time
import joblib
import pandas as pd
import pytest
import numpy as np

from feature_pipeline import IMUFeatureTransformer, build_ml_pipeline
from ml_classifier import MLAccidentClassifier, load_pipeline, classify_ml
from models import DeviceContext, ImpactPayload

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "accident_classifier.pkl")
PIPELINE_PATH = os.path.join(os.path.dirname(__file__), "..", "accident_pipeline.pkl")


def test_imu_feature_transformer_derived():
    """Test feature transformer with pre-calculated impact_g and gyro_delta."""
    transformer = IMUFeatureTransformer()
    data = {
        "impact_g": [2.5],
        "gyro_delta": [10.0],
        "Speed_kmh": [50.0],
    }
    df = pd.DataFrame(data)
    features = transformer.transform(df)
    assert features.shape == (1, 3)
    assert features[0, 0] == 2.5
    assert features[0, 1] == 10.0
    assert features[0, 2] == 50.0


def test_imu_feature_transformer_raw_imu():
    """Test feature transformer deriving impact_g and gyro_delta from raw IMU components."""
    transformer = IMUFeatureTransformer()
    data = {
        "Motion_Intensity": [14.81],  # impact_g = |14.81 - 9.81| = 5.0
        "Gyro_X": [0.1],
        "Gyro_Y": [0.0],
        "Gyro_Z": [0.0],  # mag ~ 0.1 rad/s -> ~ 5.73 deg/s
        "Speed_kmh": [10.0],
    }
    df = pd.DataFrame(data)
    features = transformer.transform(df)
    assert features.shape == (1, 3)
    assert pytest.approx(features[0, 0], 0.01) == 5.0
    assert pytest.approx(features[0, 1], 0.1) == 5.73
    assert features[0, 2] == 10.0


def test_pickle_file_existence():
    """Verify that train_model generated valid .pkl files."""
    assert os.path.exists(MODEL_PATH), "accident_classifier.pkl missing"
    assert os.path.exists(PIPELINE_PATH), "accident_pipeline.pkl missing"


def test_load_pickled_pipeline():
    """Test loading and making predictions with pickled pipeline."""
    pipeline = load_pipeline(MODEL_PATH)
    assert pipeline is not None

    # Test sample prediction on high impact (Crash sample matching dataset distribution)
    sample_crash = pd.DataFrame([{
        "impact_g": 3.5,
        "gyro_delta": 5.0,
        "Speed_kmh": 10.0,
    }])
    pred_crash = pipeline.predict(sample_crash)[0]
    prob_crash = pipeline.predict_proba(sample_crash)[0]
    assert pred_crash == 1
    assert prob_crash[1] > 0.8

    # Test sample prediction on low impact (Normal sample matching dataset distribution)
    sample_normal = pd.DataFrame([{
        "impact_g": 0.2,
        "gyro_delta": 0.5,
        "Speed_kmh": 50.0,
    }])
    pred_normal = pipeline.predict(sample_normal)[0]
    prob_normal = pipeline.predict_proba(sample_normal)[0]
    assert pred_normal == 0
    assert prob_normal[0] > 0.8


def test_ml_accident_classifier_payload():
    """Test MLAccidentClassifier wrapper with ImpactPayload and DeviceContext."""
    classifier = MLAccidentClassifier(MODEL_PATH)

    impact = ImpactPayload(
        device_id="TEST_VEH",
        timestamp=time.time(),
        impact_g=3.8,
        gyro_delta=5.0,
        gps_lat=17.385,
        gps_lon=78.4867,
        gps_fix=True,
    )
    context = DeviceContext(recent_speed=10.0)

    result = classifier.predict_payload(impact, context)
    assert result.decision == "accident"
    assert result.confidence >= 0.8
    assert "ML Pipeline" in result.reason

def test_behavior_crash_vs_pothole():
    """Test that a clear crash scores higher than a pothole (behavioral correctness)."""
    pipeline = load_pipeline(MODEL_PATH)
    
    crash = pd.DataFrame([{"impact_g": 8.7, "gyro_delta": 145.2, "Speed_kmh": 45.0}])
    pothole = pd.DataFrame([{"impact_g": 6.0, "gyro_delta": 0.5, "Speed_kmh": 40.0}])
    
    prob_crash = pipeline.predict_proba(crash)[0][1]
    prob_pothole = pipeline.predict_proba(pothole)[0][1]
    
    assert prob_crash > prob_pothole, f"Failed: Crash prob ({prob_crash:.4f}) is not higher than pothole prob ({prob_pothole:.4f})"
    assert prob_pothole < 0.5, f"Failed: Pothole prob should be < 0.5 but is {prob_pothole:.4f}"


def test_behavior_monotonicity():
    """Test that increasing impact_g does not decrease crash probability (behavioral correctness)."""
    pipeline = load_pipeline(MODEL_PATH)
    
    prev_prob = -1.0
    for impact_g in np.linspace(0.2, 9.0, 8):
        sample = pd.DataFrame([{"impact_g": impact_g, "gyro_delta": 50.0, "Speed_kmh": 30.0}])
        prob = pipeline.predict_proba(sample)[0][1]
        
        assert prob >= prev_prob, f"Failed: Monotonicity broken at impact_g={impact_g:.2f}, prob dropped from {prev_prob:.4f} to {prob:.4f}"
        prev_prob = prob
