"""
Tunable thresholds for accident classification.

All values sourced from environment variables with hackathon-ready defaults.
Tune these in Milestone 2 with real drop-test data from Dhanu's ESP32.
"""

import os


def _float_env(key: str, default: float) -> float:
    """Read a float from env, falling back to default on missing/malformed."""
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except (ValueError, TypeError):
        return default


def _int_env(key: str, default: int) -> int:
    """Read an int from env, falling back to default on missing/malformed."""
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


# ── Classification Thresholds ────────────────────────────────────────────────
IMPACT_G_THRESHOLD: float = _float_env("IMPACT_G_THRESHOLD", 1.2)
GYRO_DELTA_THRESHOLD: float = _float_env("GYRO_DELTA_THRESHOLD", 3.0)
GYRO_VERY_LOW: float = _float_env("GYRO_VERY_LOW", 1.0)
SEVERE_IMPACT_G: float = _float_env("SEVERE_IMPACT_G", 4.5)

# ── Speed Context ────────────────────────────────────────────────────────────
SPEED_LOW_THRESHOLD: float = _float_env("SPEED_LOW_THRESHOLD", 5.0)
SPEED_HIGH_BOOST: float = _float_env("SPEED_HIGH_BOOST", 30.0)

# ── Decision ─────────────────────────────────────────────────────────────────
ACCIDENT_CONFIDENCE_CUTOFF: float = _float_env("ACCIDENT_CONFIDENCE_CUTOFF", 0.6)

# ── Debounce & Staleness ─────────────────────────────────────────────────────
DEBOUNCE_WINDOW_S: int = _int_env("DEBOUNCE_WINDOW_S", 30)
HEARTBEAT_STALE_S: int = _int_env("HEARTBEAT_STALE_S", 30)
STALENESS_CHECK_INTERVAL_S: int = _int_env("STALENESS_CHECK_INTERVAL_S", 10)

# ── Device Heartbeat Buffer ──────────────────────────────────────────────────
HEARTBEAT_BUFFER_SIZE: int = _int_env("HEARTBEAT_BUFFER_SIZE", 10)

# ── Safety Gate ──────────────────────────────────────────────────────────────
SAFETY_MIN_CONFIDENCE_FLOOR: float = _float_env("SAFETY_MIN_CONFIDENCE_FLOOR", 0.3)
SAFETY_MAX_SUPPRESSION_RATE: float = _float_env("SAFETY_MAX_SUPPRESSION_RATE", 0.05)
SAFETY_ROLLING_WINDOW: int = _int_env("SAFETY_ROLLING_WINDOW", 100)

# ── Drift Detection ─────────────────────────────────────────────────────────
DRIFT_PSI_THRESHOLD: float = _float_env("DRIFT_PSI_THRESHOLD", 0.2)
DRIFT_WINDOW_SIZE: int = _int_env("DRIFT_WINDOW_SIZE", 500)
DRIFT_NUM_BINS: int = _int_env("DRIFT_NUM_BINS", 10)

# ── Model Registry ──────────────────────────────────────────────────────────
REGISTRY_DIR: str = os.environ.get(
    "REGISTRY_DIR", os.path.join(os.path.dirname(__file__), "registry")
)

# ── Training Pool ───────────────────────────────────────────────────────────
TRAINING_POOL_DIR: str = os.environ.get(
    "TRAINING_POOL_DIR", os.path.join(os.path.dirname(__file__), "training_pool")
)
MIN_RETRAIN_SAMPLES: int = _int_env("MIN_RETRAIN_SAMPLES", 100)
RETRAIN_CLASS_BALANCE_MIN: float = _float_env("RETRAIN_CLASS_BALANCE_MIN", 0.15)
RETRAIN_CLASS_BALANCE_MAX: float = _float_env("RETRAIN_CLASS_BALANCE_MAX", 0.85)
PSEUDO_LABEL_HIGH_CONFIDENCE: float = _float_env("PSEUDO_LABEL_HIGH_CONFIDENCE", 0.9)
PSEUDO_LABEL_LOW_CONFIDENCE: float = _float_env("PSEUDO_LABEL_LOW_CONFIDENCE", 0.1)

# ── RL Policy ────────────────────────────────────────────────────────────────
RL_EPSILON: float = _float_env("RL_EPSILON", 0.1)
RL_LEARNING_RATE: float = _float_env("RL_LEARNING_RATE", 0.01)
RL_DISCOUNT_FACTOR: float = _float_env("RL_DISCOUNT_FACTOR", 0.95)
RL_STATE_BINS: int = _int_env("RL_STATE_BINS", 8)

# ── Decision Policy ─────────────────────────────────────────────────────────
POLICY_HIGHWAY_SPEED: float = _float_env("POLICY_HIGHWAY_SPEED", 80.0)
POLICY_HIGHWAY_THRESHOLD_REDUCTION: float = _float_env(
    "POLICY_HIGHWAY_THRESHOLD_REDUCTION", 0.15
)
POLICY_STANDSTILL_THRESHOLD_INCREASE: float = _float_env(
    "POLICY_STANDSTILL_THRESHOLD_INCREASE", 0.20
)
