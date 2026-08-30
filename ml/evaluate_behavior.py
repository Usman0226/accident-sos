import joblib
import pandas as pd
import numpy as np
import sys
import math

# Load pipeline
model_artifact = joblib.load('accident_classifier.pkl')
pipeline = model_artifact['pipeline']
print("1. Pipeline steps:", pipeline.steps)

classifier_step = pipeline.named_steps['classifier']
if hasattr(classifier_step, 'calibrated_classifiers_'):
    rf = getattr(classifier_step.calibrated_classifiers_[0], 'estimator', None)
    if rf is None:
        rf = getattr(classifier_step.calibrated_classifiers_[0], 'base_estimator', None)
else:
    rf = classifier_step

if hasattr(classifier_step, 'estimator'):
    rf = classifier_step.estimator
elif hasattr(classifier_step, 'base_estimator'):
    rf = classifier_step.base_estimator
elif hasattr(classifier_step, 'calibrated_classifiers_'):
    if hasattr(classifier_step.calibrated_classifiers_[0], 'estimator'):
        rf = classifier_step.calibrated_classifiers_[0].estimator
    else:
        rf = classifier_step.calibrated_classifiers_[0].base_estimator

print(f"RandomForest: class_weight={rf.class_weight}, n_estimators={rf.n_estimators}, max_depth={rf.max_depth}")

raw_sample = pd.DataFrame([{'Motion_Intensity': 14.81, 'Gyro_X': 0.1, 'Gyro_Y': 0, 'Gyro_Z': 0, 'Speed_kmh': 10.0}])
derived_sample = pd.DataFrame([{'impact_g': 5.0, 'gyro_delta': 0.1 * (180.0 / math.pi), 'Speed_kmh': 10.0}])

raw_prob = pipeline.predict_proba(raw_sample)[0][1]
derived_prob = pipeline.predict_proba(derived_sample)[0][1]
print(f"\n2. Raw prob: {raw_prob:.4f}, Derived prob: {derived_prob:.4f}, Diff: {abs(raw_prob - derived_prob):.4f}")

edge_cases = {
    'Clear crash': {'impact_g': 8.7, 'gyro_delta': 145.2, 'Speed_kmh': 45.0},
    'Pothole': {'impact_g': 6.0, 'gyro_delta': 0.5, 'Speed_kmh': 40.0},
    'Sharp turn': {'impact_g': 0.8, 'gyro_delta': 120.0, 'Speed_kmh': 30.0},
    'Standstill jolt': {'impact_g': 3.0, 'gyro_delta': 10.0, 'Speed_kmh': 0.5},
    'Normal driving': {'impact_g': 0.3, 'gyro_delta': 1.0, 'Speed_kmh': 25.0},
    'Borderline': {'impact_g': 1.3, 'gyro_delta': 3.5, 'Speed_kmh': 20.0}
}

print("\n3. Edge Cases:")
for name, case in edge_cases.items():
    prob = pipeline.predict_proba(pd.DataFrame([case]))[0][1]
    print(f"{name}: prob={prob:.4f}")

print("\n4. Sweeping impact_g (gyro=50, speed=30):")
prev_prob = None
for impact_g in np.linspace(0.2, 9.0, 8):
    prob = pipeline.predict_proba(pd.DataFrame([{'impact_g': impact_g, 'gyro_delta': 50.0, 'Speed_kmh': 30.0}]))[0][1]
    monotonic_flag = ""
    if prev_prob is not None and prob < prev_prob:
        monotonic_flag = f" [WARNING: Decreased from {prev_prob:.4f}]"
    print(f"impact_g={impact_g:.2f}: prob={prob:.4f}{monotonic_flag}")
    prev_prob = prob

from classifier import classify
from models import ImpactPayload, DeviceContext
import config

print(f"\n5. Cross-Check with Rule-Based (Cutoff: {config.ACCIDENT_CONFIDENCE_CUTOFF}):")
for name, case in edge_cases.items():
    impact = ImpactPayload(
        device_id="TEST",
        timestamp=0.0,
        impact_g=case['impact_g'],
        gyro_delta=case['gyro_delta'],
        gps_lat=0.0,
        gps_lon=0.0,
        gps_fix=True
    )
    context = DeviceContext(recent_speed=case['Speed_kmh'])
    res = classify(impact, context)
    ml_prob = pipeline.predict_proba(pd.DataFrame([case]))[0][1]
    ml_decision = "accident" if ml_prob >= 0.5 else "no_accident"
    print(f"{name}:\n  ML: prob={ml_prob:.4f} ({ml_decision})\n  Rule: conf={res.confidence:.4f} ({res.decision})\n  Disagree: {ml_decision != res.decision}")
