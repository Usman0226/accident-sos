import joblib
import numpy as np
import pandas as pd
import math
from sklearn.ensemble import RandomForestClassifier

# 1. Feature Importances
model = joblib.load('accident_classifier.pkl')
pipeline = model['pipeline']
clf = pipeline.named_steps['classifier']

importances = []
for cal_clf in clf.calibrated_classifiers_:
    est = getattr(cal_clf, 'estimator', getattr(cal_clf, 'base_estimator', None))
    if est is not None:
        importances.append(est.feature_importances_)

if importances:
    avg_importances = np.mean(importances, axis=0)
    print("1. FEATURE IMPORTANCES (Current Pipeline):")
    print(f"impact_g:   {avg_importances[0]:.4f}")
    print(f"gyro_delta: {avg_importances[1]:.4f}")
else:
    print("Could not extract feature importances from pipeline.")

# 2. Dataset-level Check
df = pd.read_csv('road_accident_imu_dataset_8000.csv')
df['impact_g'] = (df['Motion_Intensity'] - 9.81).abs()
gyro_mag = np.sqrt(df['Gyro_X']**2 + df['Gyro_Y']**2 + df['Gyro_Z']**2)
df['gyro_delta'] = gyro_mag * (180.0 / math.pi)

filtered = df[(df['impact_g'] > 1.2) & (df['gyro_delta'] < 1.0)]
print(f"\n2. DATASET REGION CHECK (impact_g > 1.2 AND gyro_delta < 1.0):")
print(f"Total rows in region: {len(filtered)}")
if len(filtered) > 0:
    counts = filtered['Crash_Label'].value_counts()
    for label, count in counts.items():
        print(f"  Label {label}: {count} ({count/len(filtered)*100:.2f}%)")

# Throwaway check for max_depth=None
X = df[['impact_g', 'gyro_delta']].values
y = df['Crash_Label'].values
rf_deep = RandomForestClassifier(n_estimators=100, max_depth=None, class_weight='balanced', random_state=42)
rf_deep.fit(X, y)
print("\nTHROWAWAY CHECK (max_depth=None on full dataset):")
print(f"impact_g:   {rf_deep.feature_importances_[0]:.4f}")
print(f"gyro_delta: {rf_deep.feature_importances_[1]:.4f}")
