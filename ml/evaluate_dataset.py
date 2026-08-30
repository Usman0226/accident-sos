"""
Dataset evaluation script for the Accident Detection Engine.

Evaluates the existing rule-based classifier against the
road_accident_imu_dataset_8000.csv dataset and reports:
  - Column mapping from dataset → classifier schema
  - Baseline classifier accuracy (current thresholds)
  - Optimal threshold search
  - Confusion matrix + precision/recall/F1
  - Comparison with Motion_Intensity-only threshold

Run from ml/:
    python evaluate_dataset.py
"""

import csv
import math
import sys

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8")

CSV_PATH = "road_accident_imu_dataset_8000.csv"


def load_dataset():
    """Load CSV and derive impact_g and gyro_delta from raw IMU columns."""
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            ax = float(r["Acc_X"])
            ay = float(r["Acc_Y"])
            az = float(r["Acc_Z"])
            gx = float(r["Gyro_X"])
            gy = float(r["Gyro_Y"])
            gz = float(r["Gyro_Z"])

            # Motion_Intensity = sqrt(ax^2+ay^2+az^2), i.e. total accel magnitude
            motion_intensity = float(r["Motion_Intensity"])

            # impact_g: deviation from resting gravity (9.81 m/s^2)
            # This is the true "shock" signal — how far the sensor reading
            # deviates from normal 1g gravity.
            impact_g = abs(motion_intensity - 9.81)

            # gyro_delta: magnitude of angular velocity in deg/s
            # Dataset stores gyro in rad/s, our classifier expects deg/s
            gyro_mag_rads = math.sqrt(gx**2 + gy**2 + gz**2)
            gyro_delta = gyro_mag_rads * (180.0 / math.pi)

            rows.append({
                "impact_g": impact_g,
                "gyro_delta": gyro_delta,
                "motion_intensity": motion_intensity,
                "speed_kmph": float(r["Speed_kmh"]),
                "lat": float(r["Latitude"]),
                "lon": float(r["Longitude"]),
                "label": int(r["Crash_Label"]),
            })
    return rows


def evaluate_thresholds(rows, impact_thresh, gyro_thresh, label=""):
    """Run rule-based classifier with given thresholds, return metrics."""
    tp = fp = fn = tn = 0
    for r in rows:
        predicted = r["impact_g"] > impact_thresh and r["gyro_delta"] > gyro_thresh
        actual = r["label"] == 1

        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and actual:
            fn += 1
        else:
            tn += 1

    n = len(rows)
    accuracy = (tp + tn) / n if n > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "label": label,
        "impact_thresh": impact_thresh,
        "gyro_thresh": gyro_thresh,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def evaluate_impact_only(rows, impact_thresh, label=""):
    """Evaluate using only impact_g threshold (no gyro requirement)."""
    tp = fp = fn = tn = 0
    for r in rows:
        predicted = r["impact_g"] > impact_thresh
        actual = r["label"] == 1

        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and actual:
            fn += 1
        else:
            tn += 1

    n = len(rows)
    accuracy = (tp + tn) / n if n > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "label": label,
        "impact_thresh": impact_thresh,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def print_metrics(m):
    """Pretty-print a metrics dict."""
    print(f"  {'Accuracy:':<12} {m['accuracy']:.4f}  ({m['accuracy']*100:.1f}%)")
    print(f"  {'Precision:':<12} {m['precision']:.4f}")
    print(f"  {'Recall:':<12} {m['recall']:.4f}")
    print(f"  {'F1 Score:':<12} {m['f1']:.4f}")
    print(f"  Confusion Matrix:")
    print(f"                  Predicted")
    print(f"                  Accident  No-Accident")
    print(f"    Actual Acc  |  {m['tp']:>5}   |  {m['fn']:>5}   |")
    print(f"    Actual NoA  |  {m['fp']:>5}   |  {m['tn']:>5}   |")


def main():
    rows = load_dataset()
    crashes = [r for r in rows if r["label"] == 1]
    normals = [r for r in rows if r["label"] == 0]

    print("=" * 70)
    print("  DATASET EVALUATION — Accident Detection Classifier")
    print("=" * 70)

    # ── Dataset Summary ──────────────────────────────────────────────────
    print(f"\nDataset: {CSV_PATH}")
    print(f"  Total rows: {len(rows)}")
    print(f"  Crash=1:    {len(crashes)} ({len(crashes)/len(rows)*100:.1f}%)")
    print(f"  Normal=0:   {len(normals)} ({len(normals)/len(rows)*100:.1f}%)")

    # ── Feature Distribution ─────────────────────────────────────────────
    print("\n--- Derived Feature Distributions ---")
    for name, subset in [("CRASH", crashes), ("NORMAL", normals)]:
        ig = sorted([r["impact_g"] for r in subset])
        gd = sorted([r["gyro_delta"] for r in subset])
        sp = sorted([r["speed_kmph"] for r in subset])
        n = len(ig)
        print(f"\n  {name} (n={n}):")
        print(f"    impact_g:    min={ig[0]:.2f}  p25={ig[n//4]:.2f}  med={ig[n//2]:.2f}  p75={ig[3*n//4]:.2f}  max={ig[-1]:.2f}")
        print(f"    gyro_delta:  min={gd[0]:.2f}  p25={gd[n//4]:.2f}  med={gd[n//2]:.2f}  p75={gd[3*n//4]:.2f}  max={gd[-1]:.2f}")
        print(f"    speed_kmph:  min={sp[0]:.1f}  p25={sp[n//4]:.1f}  med={sp[n//2]:.1f}  p75={sp[3*n//4]:.1f}  max={sp[-1]:.1f}")

    # ── Current Classifier (impact_g>4 AND gyro_delta>100) ───────────────
    print("\n" + "=" * 70)
    print("  TEST 1: Current thresholds (impact_g > 4.0 AND gyro_delta > 100)")
    print("=" * 70)
    m1 = evaluate_thresholds(rows, 4.0, 100.0, "current")
    print_metrics(m1)

    # ── Why the current thresholds fail ──────────────────────────────────
    print("\n  DIAGNOSIS:")
    print("    The dataset's gyro values are in rad/s (max ~0.2 rad/s = ~12 deg/s).")
    print("    Our threshold of gyro_delta > 100 deg/s is NEVER reached.")
    print("    The 'AND' rule means ZERO true positives.")

    # ── Impact-only evaluation ───────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  TEST 2: Impact-only thresholds (gyro requirement removed)")
    print("=" * 70)
    for thresh in [0.5, 1.0, 1.2, 1.5, 1.7, 2.0]:
        m = evaluate_impact_only(rows, thresh, f"impact_g>{thresh}")
        print(f"\n  impact_g > {thresh}:")
        print_metrics(m)

    # ── Optimized dual-threshold search ──────────────────────────────────
    print("\n" + "=" * 70)
    print("  TEST 3: Dual-threshold search (impact_g AND gyro_delta)")
    print("          (using dataset-appropriate ranges)")
    print("=" * 70)
    best_f1 = 0
    best_m = None
    for ig_t in [0.8, 1.0, 1.2, 1.5, 1.7]:
        for gd_t in [0.5, 1.0, 2.0, 3.0, 5.0]:
            m = evaluate_thresholds(rows, ig_t, gd_t)
            if m["f1"] > best_f1:
                best_f1 = m["f1"]
                best_m = m

    if best_m:
        print(f"\n  Best dual threshold: impact_g > {best_m['impact_thresh']} AND gyro_delta > {best_m['gyro_thresh']}")
        print_metrics(best_m)

    # ── Motion_Intensity direct threshold ────────────────────────────────
    print("\n" + "=" * 70)
    print("  TEST 4: Motion_Intensity threshold (total accel magnitude)")
    print("=" * 70)
    for mi_thresh in [10.0, 10.5, 10.9, 11.0, 11.2]:
        tp = sum(1 for r in rows if r["label"] == 1 and r["motion_intensity"] > mi_thresh)
        fp = sum(1 for r in rows if r["label"] == 0 and r["motion_intensity"] > mi_thresh)
        fn = sum(1 for r in rows if r["label"] == 1 and r["motion_intensity"] <= mi_thresh)
        tn = sum(1 for r in rows if r["label"] == 0 and r["motion_intensity"] <= mi_thresh)
        n = len(rows)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        acc = (tp + tn) / n
        print(f"\n  Motion_Intensity > {mi_thresh}:")
        print(f"    Accuracy={acc:.4f}  Prec={prec:.4f}  Rec={rec:.4f}  F1={f1:.4f}")
        print(f"    TP={tp}  FP={fp}  FN={fn}  TN={tn}")

    # ── Recommendation ───────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  RECOMMENDATIONS")
    print("=" * 70)
    print("""
  1. DATASET FIELD MAPPING:
     - impact_g = |Motion_Intensity - 9.81|  (deviation from resting gravity)
     - gyro_delta = sqrt(gx^2+gy^2+gz^2) * 57.296  (rad/s → deg/s)

  2. THRESHOLD RECALIBRATION NEEDED:
     - Current:  impact_g > 4.0 AND gyro_delta > 100  → 0% recall on this dataset
     - The dataset's gyro range is 0-12 deg/s, not 0-200+ deg/s
     - The dataset's impact_g range is 0-5.5g deviation, not 0-20g+

  3. RECOMMENDED NEW THRESHOLDS (for this dataset):
     - impact_g > 1.2  (catches all crashes, since crash min = 1.74)
     - This alone achieves ~100% accuracy on this dataset

  4. THE REAL QUESTION for Dhanu:
     - What unit does the ESP32 report gyro in? (rad/s vs deg/s)
     - What is the raw magnitude of a real crash vs pothole?
     - This dataset may be synthetic — real sensor data will differ.
""")


if __name__ == "__main__":
    main()
