"""
Machine Learning Model Pipeline Training for Accident Detection.

Trains a Scikit-Learn Pipeline combining IMUFeatureTransformer and Calibrated
Random Forest classifier on the merged dataset (original + augmented).
Saves the fitted pipeline into a .pkl file for deployment and live inference.

Changes from original:
  - Merges augmented_negatives.csv to fix the pothole-zone gap and speed confound
  - Reports per-class metrics and feature importances
  - Runs behavioral gate checks before saving
"""

from __future__ import annotations

import os
import hashlib
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

from feature_pipeline import build_ml_pipeline

CSV_PATH = "road_accident_imu_dataset_8000.csv"
AUGMENTED_PATH = "augmented_negatives.csv"
MODEL_PATH = "accident_classifier.pkl"
PIPELINE_PATH = "accident_pipeline.pkl"


def load_dataset() -> tuple[pd.DataFrame, pd.Series]:
    """Load and merge original + augmented datasets."""
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Dataset file not found at {CSV_PATH}")

    print(f"Loading original dataset: {CSV_PATH}...")
    df_orig = pd.read_csv(CSV_PATH)
    print(f"  Original: {len(df_orig)} rows, {df_orig['Crash_Label'].sum()} crashes")

    if os.path.exists(AUGMENTED_PATH):
        print(f"Loading augmented dataset: {AUGMENTED_PATH}...")
        df_aug = pd.read_csv(AUGMENTED_PATH)
        print(f"  Augmented: {len(df_aug)} rows, {df_aug['Crash_Label'].sum()} crashes")
        df = pd.concat([df_orig, df_aug], ignore_index=True)
        print(f"  Merged: {len(df)} rows")
    else:
        print(f"  No augmented data found at {AUGMENTED_PATH}, using original only.")
        df = df_orig

    y = df["Crash_Label"]
    return df, y


def compute_dataset_hash(df: pd.DataFrame) -> str:
    """Compute a reproducible hash of the dataset for versioning."""
    content = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(content).hexdigest()[:16]


def extract_feature_importances(pipeline) -> dict[str, float]:
    """Extract feature importances from the calibrated RF inside the pipeline."""
    classifier_step = pipeline.named_steps["classifier"]
    importances_list = []

    if hasattr(classifier_step, "calibrated_classifiers_"):
        for cal_clf in classifier_step.calibrated_classifiers_:
            est = getattr(cal_clf, "estimator", getattr(cal_clf, "base_estimator", None))
            if est is not None and hasattr(est, "feature_importances_"):
                importances_list.append(est.feature_importances_)

    if importances_list:
        avg = np.mean(importances_list, axis=0)
        return {
            "impact_g": float(avg[0]),
            "gyro_delta": float(avg[1]),
            "Speed_kmh": float(avg[2]) if len(avg) > 2 else 0.0,
        }
    return {}


def run_behavioral_checks(pipeline) -> tuple[bool, list[str]]:
    """
    Run behavioral gate checks that the model MUST pass before saving.

    Returns:
        (all_passed, list_of_failure_reasons)
    """
    failures = []

    # --- Check 1: Clear crash scores higher than pothole ---
    crash_sample = pd.DataFrame([{"impact_g": 8.7, "gyro_delta": 145.2, "Speed_kmh": 45.0}])
    pothole_sample = pd.DataFrame([{"impact_g": 6.0, "gyro_delta": 0.5, "Speed_kmh": 40.0}])

    prob_crash = pipeline.predict_proba(crash_sample)[0][1]
    prob_pothole = pipeline.predict_proba(pothole_sample)[0][1]

    print(f"\n  Behavioral check 1: crash ({prob_crash:.4f}) > pothole ({prob_pothole:.4f})")
    if prob_crash <= prob_pothole:
        failures.append(f"Crash prob ({prob_crash:.4f}) not higher than pothole ({prob_pothole:.4f})")
    if prob_pothole >= 0.5:
        failures.append(f"Pothole prob ({prob_pothole:.4f}) should be < 0.5")

    # --- Check 2: Monotonicity — increasing impact_g shouldn't decrease crash prob ---
    # (at fixed moderate gyro + speed, which is a crash signature)
    print("  Behavioral check 2: monotonicity (impact_g sweep at gyro=50, speed=30)")
    prev_prob = -1.0
    for impact_g in np.linspace(0.5, 9.0, 6):
        sample = pd.DataFrame([{"impact_g": impact_g, "gyro_delta": 50.0, "Speed_kmh": 30.0}])
        prob = pipeline.predict_proba(sample)[0][1]
        if prob < prev_prob - 0.02:  # Allow 2% tolerance for calibration noise
            failures.append(
                f"Monotonicity broken at impact_g={impact_g:.2f}: "
                f"prob dropped from {prev_prob:.4f} to {prob:.4f}"
            )
        prev_prob = prob

    # --- Check 3: Standstill jolt should NOT trigger ---
    standstill = pd.DataFrame([{"impact_g": 3.0, "gyro_delta": 0.3, "Speed_kmh": 0.5}])
    prob_standstill = pipeline.predict_proba(standstill)[0][1]
    print(f"  Behavioral check 3: standstill jolt prob = {prob_standstill:.4f} (should be < 0.5)")
    if prob_standstill >= 0.5:
        failures.append(f"Standstill jolt prob ({prob_standstill:.4f}) should be < 0.5")

    # --- Check 4: Normal driving should NOT trigger ---
    normal = pd.DataFrame([{"impact_g": 0.3, "gyro_delta": 1.0, "Speed_kmh": 50.0}])
    prob_normal = pipeline.predict_proba(normal)[0][1]
    print(f"  Behavioral check 4: normal driving prob = {prob_normal:.4f} (should be < 0.2)")
    if prob_normal >= 0.2:
        failures.append(f"Normal driving prob ({prob_normal:.4f}) should be < 0.2")

    # --- Check 5: Highway crash MUST trigger ---
    highway_crash = pd.DataFrame([{"impact_g": 5.0, "gyro_delta": 30.0, "Speed_kmh": 80.0}])
    prob_highway = pipeline.predict_proba(highway_crash)[0][1]
    print(f"  Behavioral check 5: highway crash prob = {prob_highway:.4f} (should be > 0.7)")
    if prob_highway <= 0.7:
        failures.append(f"Highway crash prob ({prob_highway:.4f}) should be > 0.7")

    # --- Check 6: Door slam / loading must NOT trigger ---
    door_slam = pd.DataFrame([{"impact_g": 4.0, "gyro_delta": 0.2, "Speed_kmh": 0.0}])
    prob_door = pipeline.predict_proba(door_slam)[0][1]
    print(f"  Behavioral check 6: door slam prob = {prob_door:.4f} (should be < 0.5)")
    if prob_door >= 0.5:
        failures.append(f"Door slam prob ({prob_door:.4f}) should be < 0.5")

    all_passed = len(failures) == 0
    return all_passed, failures


def main() -> None:
    df, y = load_dataset()

    print(f"\nTotal samples: {len(df)}")
    print(f"Crash labels (1): {y.sum()} | Normal (0): {len(y) - y.sum()}")
    print(f"Class balance: {y.sum()/len(y)*100:.1f}% crash / {(1 - y.sum()/len(y))*100:.1f}% normal")

    dataset_hash = compute_dataset_hash(df)
    print(f"Dataset hash: {dataset_hash}")

    # 1. 5-Fold Stratified CV Evaluation
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    fold_metrics: list[dict] = []

    print("\n--- 5-Fold Stratified CV Evaluation (End-to-End Pipeline) ---")
    for fold, (train_idx, test_idx) in enumerate(skf.split(df, y), 1):
        df_train, df_test = df.iloc[train_idx], df.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        fold_pipeline = build_ml_pipeline(random_state=42)
        fold_pipeline.fit(df_train, y_train)

        y_pred = fold_pipeline.predict(df_test)
        metrics = {
            "f1": f1_score(y_test, y_pred, zero_division=0),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "accuracy": accuracy_score(y_test, y_pred),
        }
        fold_metrics.append(metrics)
        print(
            f"Fold {fold}: F1={metrics['f1']:.4f}  "
            f"Prec={metrics['precision']:.4f}  "
            f"Rec={metrics['recall']:.4f}  "
            f"Acc={metrics['accuracy']:.4f}"
        )

    avg_metrics = {k: np.mean([m[k] for m in fold_metrics]) for k in fold_metrics[0]}
    print(f"\nAverage CV: F1={avg_metrics['f1']:.4f}  "
          f"Prec={avg_metrics['precision']:.4f}  "
          f"Rec={avg_metrics['recall']:.4f}  "
          f"Acc={avg_metrics['accuracy']:.4f}")

    # 2. Train final pipeline on full dataset
    print("\nTraining final pipeline on full dataset...")
    final_pipeline = build_ml_pipeline(random_state=42)
    final_pipeline.fit(df, y)

    # Full dataset metrics
    y_pred_full = final_pipeline.predict(df)
    acc = accuracy_score(y, y_pred_full)
    prec = precision_score(y, y_pred_full, zero_division=0)
    rec = recall_score(y, y_pred_full, zero_division=0)
    f1_full = f1_score(y, y_pred_full, zero_division=0)

    print(f"\n--- Final Model Metrics (Full Dataset) ---")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print(f"F1:        {f1_full:.4f}")

    cm = confusion_matrix(y, y_pred_full)
    print("Confusion Matrix:")
    print("                Predicted")
    print("                No-Acc  Accident")
    print(f"Actual No-Acc | {cm[0,0]:>6} | {cm[0,1]:>7} |")
    print(f"Actual Acc    | {cm[1,0]:>6} | {cm[1,1]:>7} |")

    print("\nClassification Report:")
    print(classification_report(y, y_pred_full, target_names=["No Accident", "Accident"]))

    # 3. Feature importances
    importances = extract_feature_importances(final_pipeline)
    if importances:
        print("--- Feature Importances ---")
        for feat, imp in importances.items():
            bar = "#" * int(imp * 50)
            print(f"  {feat:>12}: {imp:.4f}  {bar}")

        gyro_importance = importances.get("gyro_delta", 0)
        if gyro_importance < 0.05:
            print(f"\n  WARNING: gyro_delta importance ({gyro_importance:.4f}) is below 5%.")
            print("  The model may still not be using rotational data effectively.")

    # 4. Behavioral gate checks
    print("\n--- Behavioral Gate Checks ---")
    passed, failures = run_behavioral_checks(final_pipeline)

    if not passed:
        print(f"\n  BEHAVIORAL GATE FAILED — {len(failures)} failure(s):")
        for f_reason in failures:
            print(f"    FAIL: {f_reason}")
        print("\n  Model will NOT be saved. Fix the training data or architecture.")
        return

    print("\n  ALL BEHAVIORAL CHECKS PASSED")

    # 5. Export fitted pipeline to .pkl files
    model_artifact = {
        "pipeline": final_pipeline,
        "features": ["impact_g", "gyro_delta", "Speed_kmh"],
        "name": "Calibrated Random Forest IMU Pipeline v2 (augmented)",
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1_score": float(avg_metrics["f1"]),
        "feature_importances": importances,
        "dataset_hash": dataset_hash,
        "dataset_size": len(df),
        "augmented": os.path.exists(AUGMENTED_PATH),
    }

    joblib.dump(model_artifact, MODEL_PATH)
    joblib.dump(final_pipeline, PIPELINE_PATH)

    print(f"\nSaved ML Model Artifact to {MODEL_PATH}")
    print(f"Saved Pure Scikit-Learn Pipeline to {PIPELINE_PATH}")


if __name__ == "__main__":
    main()
