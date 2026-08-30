"""
Generate physically-plausible synthetic negative examples to fill the dataset gap.

Root cause: The original dataset has ZERO non-accident examples with impact_g > 1.2,
and speed is inverted (crashes only 0-20 km/h, normals only 20-80 km/h).

This script generates negative samples (Crash_Label=0) for scenarios that produce
high impact_g but are NOT accidents:
  1. Potholes — high vertical impact, near-zero rotation
  2. Speed bumps — moderate impact, near-zero rotation, low speed
  3. Hard braking — moderate impact, low rotation, any speed
  4. Door slam / loading — high impact, zero rotation, zero speed
  5. Aggressive turns — low impact, high rotation, moderate speed
  6. Normal driving at all speeds — low impact, low rotation

AND fixes the speed confound by generating:
  7. Real crashes at highway speeds (40-120 km/h)
  8. Normal driving at low speeds (0-20 km/h)

Physics references for plausible magnitudes:
  - Pothole at 40 km/h: 2-6g vertical spike, <0.5 deg/s rotation
  - Speed bump at 20 km/h: 1.5-3g, <0.3 deg/s
  - Hard brake from 60 km/h: 1-2g longitudinal, <1 deg/s
  - Real side-impact crash: 3-8g, 30-200 deg/s (high rotation)
  - Real frontal crash at highway: 5-15g, 5-50 deg/s
  - Real rollover: 3-6g, 100-300 deg/s
"""

import csv
import math
import random
import hashlib
import os

random.seed(42)

OUTPUT_PATH = "augmented_negatives.csv"

# Original dataset columns:
# Timestamp,Acc_X,Acc_Y,Acc_Z,Gyro_X,Gyro_Y,Gyro_Z,Speed_kmh,Latitude,Longitude,Motion_Intensity,Crash_Label

# We need to generate raw sensor values that produce the desired derived features:
#   impact_g = |Motion_Intensity - 9.81|
#   gyro_delta = sqrt(gx^2+gy^2+gz^2) * (180/pi)
#
# So we work backwards:
#   Motion_Intensity = 9.81 + impact_g  (for upward jolt, e.g. pothole)
#   OR 9.81 - impact_g (for downward, but keep positive)
#   Gyro magnitude (rad/s) = gyro_delta_deg / (180/pi)


def impact_g_to_motion_intensity(impact_g: float) -> float:
    """Convert desired impact_g to Motion_Intensity (accel magnitude)."""
    # Randomly choose above or below resting gravity
    if random.random() > 0.3:
        return 9.81 + impact_g  # Upward jolt (pothole, bump)
    else:
        return max(0.1, 9.81 - impact_g)  # Downward (freefall phase)


def decompose_accel(motion_intensity: float) -> tuple[float, float, float]:
    """Decompose total accel magnitude into Acc_X/Y/Z components."""
    # For pothole/bump: mostly Z-axis (vertical)
    # For brake: mostly X-axis (longitudinal)
    # Add small noise to other axes
    dominant_axis = random.choice(["x", "y", "z"])
    noise_scale = 0.3

    base_x = random.gauss(0, noise_scale)
    base_y = random.gauss(0, noise_scale)
    base_z = random.gauss(0, noise_scale)

    # Assign dominant component so total magnitude matches
    remaining = math.sqrt(max(0, motion_intensity**2 - base_x**2 - base_y**2 - base_z**2))

    if dominant_axis == "z":
        base_z = remaining * (1 if random.random() > 0.3 else -1)
    elif dominant_axis == "x":
        base_x = remaining * (1 if random.random() > 0.5 else -1)
    else:
        base_y = remaining * (1 if random.random() > 0.5 else -1)

    return base_x, base_y, base_z


def gyro_delta_to_components(gyro_delta_deg: float) -> tuple[float, float, float]:
    """Convert desired gyro_delta (deg/s) to Gyro_X/Y/Z in rad/s."""
    gyro_mag_rads = gyro_delta_deg * (math.pi / 180.0)

    # Distribute across axes with some randomness
    gx = random.gauss(0, 1)
    gy = random.gauss(0, 1)
    gz = random.gauss(0, 1)
    mag = math.sqrt(gx**2 + gy**2 + gz**2)
    if mag < 1e-6:
        gx, gy, gz = gyro_mag_rads, 0, 0
    else:
        scale = gyro_mag_rads / mag
        gx *= scale
        gy *= scale
        gz *= scale

    return gx, gy, gz


def make_row(
    impact_g: float,
    gyro_delta_deg: float,
    speed: float,
    label: int,
    base_lat: float = 17.385,
    base_lon: float = 78.487,
) -> dict:
    """Generate a single dataset row from desired derived features."""
    mi = impact_g_to_motion_intensity(impact_g)
    ax, ay, az = decompose_accel(mi)
    gx, gy, gz = gyro_delta_to_components(gyro_delta_deg)

    # Slight GPS jitter
    lat = base_lat + random.gauss(0, 0.005)
    lon = base_lon + random.gauss(0, 0.005)

    return {
        "Timestamp": f"2026-01-15 {random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}",
        "Acc_X": f"{ax:.6f}",
        "Acc_Y": f"{ay:.6f}",
        "Acc_Z": f"{az:.6f}",
        "Gyro_X": f"{gx:.6f}",
        "Gyro_Y": f"{gy:.6f}",
        "Gyro_Z": f"{gz:.6f}",
        "Speed_kmh": f"{speed:.4f}",
        "Latitude": f"{lat:.6f}",
        "Longitude": f"{lon:.6f}",
        "Motion_Intensity": f"{mi:.6f}",
        "Crash_Label": str(label),
    }


def generate_augmented_data() -> list[dict]:
    """Generate all augmented samples."""
    samples = []

    # =========================================================================
    # NEGATIVE EXAMPLES (label=0) — filling the pothole zone gap
    # =========================================================================

    # --- 1. Potholes: high impact_g, very low gyro_delta, various speeds ---
    # A pothole produces a sharp vertical jolt with NO rotational component
    for _ in range(80):
        impact_g = random.uniform(1.5, 6.0)
        gyro_delta = random.uniform(0.01, 0.8)
        speed = random.uniform(15, 70)
        samples.append(make_row(impact_g, gyro_delta, speed, label=0))

    # --- 2. Speed bumps: moderate impact_g, very low rotation, low speed ---
    for _ in range(50):
        impact_g = random.uniform(1.2, 3.5)
        gyro_delta = random.uniform(0.01, 0.5)
        speed = random.uniform(5, 30)
        samples.append(make_row(impact_g, gyro_delta, speed, label=0))

    # --- 3. Hard braking: moderate impact_g, low rotation, any speed ---
    for _ in range(60):
        impact_g = random.uniform(1.0, 2.5)
        gyro_delta = random.uniform(0.1, 2.0)
        speed = random.uniform(20, 80)
        samples.append(make_row(impact_g, gyro_delta, speed, label=0))

    # --- 4. Door slam / loading: high impact, zero rotation, zero speed ---
    for _ in range(30):
        impact_g = random.uniform(2.0, 5.0)
        gyro_delta = random.uniform(0.01, 0.3)
        speed = random.uniform(0, 2)
        samples.append(make_row(impact_g, gyro_delta, speed, label=0))

    # --- 5. Aggressive turns: LOW impact, HIGH rotation, moderate speed ---
    # Sharp turns produce rotation but NOT impact — model must not confuse
    for _ in range(40):
        impact_g = random.uniform(0.3, 1.5)
        gyro_delta = random.uniform(5.0, 12.0)
        speed = random.uniform(20, 60)
        samples.append(make_row(impact_g, gyro_delta, speed, label=0))

    # --- 6. Normal driving at LOW speeds (0-20 km/h) ---
    # Fixes the speed confound: not everything at low speed is a crash
    for _ in range(80):
        impact_g = random.uniform(0.0, 0.8)
        gyro_delta = random.uniform(0.1, 5.0)
        speed = random.uniform(0, 20)
        samples.append(make_row(impact_g, gyro_delta, speed, label=0))

    # --- 7. Normal driving at medium/high speeds ---
    for _ in range(40):
        impact_g = random.uniform(0.0, 0.5)
        gyro_delta = random.uniform(0.1, 3.0)
        speed = random.uniform(40, 120)
        samples.append(make_row(impact_g, gyro_delta, speed, label=0))

    # =========================================================================
    # POSITIVE EXAMPLES (label=1) — crashes at realistic speeds
    # =========================================================================
    # Fixes the speed confound: crashes happen at ALL speeds, not just 0-20

    # --- 8. Highway frontal crash ---
    for _ in range(40):
        impact_g = random.uniform(3.0, 8.0)
        gyro_delta = random.uniform(5.0, 50.0)
        speed = random.uniform(60, 120)
        samples.append(make_row(impact_g, gyro_delta, speed, label=1))

    # --- 9. City-speed side impact ---
    for _ in range(30):
        impact_g = random.uniform(2.5, 6.0)
        gyro_delta = random.uniform(20.0, 150.0)
        speed = random.uniform(20, 50)
        samples.append(make_row(impact_g, gyro_delta, speed, label=1))

    # --- 10. Rollover ---
    for _ in range(20):
        impact_g = random.uniform(2.0, 5.0)
        gyro_delta = random.uniform(80.0, 250.0)
        speed = random.uniform(30, 80)
        samples.append(make_row(impact_g, gyro_delta, speed, label=1))

    # --- 11. Low-speed crash (parking lot, reversing) ---
    # These DO exist but should have HIGH gyro (vehicle rotates on impact)
    for _ in range(20):
        impact_g = random.uniform(2.0, 4.0)
        gyro_delta = random.uniform(10.0, 60.0)
        speed = random.uniform(2, 15)
        samples.append(make_row(impact_g, gyro_delta, speed, label=1))

    # --- 12. High-g crash with clear rotation signature ---
    # Ensures the model learns: impact + rotation = crash
    for _ in range(30):
        impact_g = random.uniform(4.0, 10.0)
        gyro_delta = random.uniform(15.0, 100.0)
        speed = random.uniform(30, 100)
        samples.append(make_row(impact_g, gyro_delta, speed, label=1))

    return samples


def main():
    samples = generate_augmented_data()

    neg = sum(1 for s in samples if s["Crash_Label"] == "0")
    pos = sum(1 for s in samples if s["Crash_Label"] == "1")
    print(f"Generated {len(samples)} augmented samples: {neg} negatives, {pos} positives")

    fieldnames = [
        "Timestamp", "Acc_X", "Acc_Y", "Acc_Z",
        "Gyro_X", "Gyro_Y", "Gyro_Z",
        "Speed_kmh", "Latitude", "Longitude",
        "Motion_Intensity", "Crash_Label",
    ]

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(samples)

    print(f"Saved to {OUTPUT_PATH}")

    # Category breakdown
    print("\nCategory breakdown:")
    print(f"  Potholes (neg):        80")
    print(f"  Speed bumps (neg):     50")
    print(f"  Hard braking (neg):    60")
    print(f"  Door slam (neg):       30")
    print(f"  Aggressive turns (neg):40")
    print(f"  Low-speed normal (neg):80")
    print(f"  High-speed normal (neg):40")
    print(f"  Highway crash (pos):   40")
    print(f"  Side impact (pos):     30")
    print(f"  Rollover (pos):        20")
    print(f"  Low-speed crash (pos): 20")
    print(f"  High-g crash (pos):    30")


if __name__ == "__main__":
    main()
