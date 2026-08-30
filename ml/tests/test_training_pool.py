"""
Unit tests for Training Pool data curation and quality gating.
"""

import shutil
import tempfile
import pytest

from training_pool import TrainingPool, TrainingSignal


@pytest.fixture
def temp_pool():
    temp_dir = tempfile.mkdtemp()
    pool = TrainingPool(pool_dir=temp_dir)
    yield pool
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_training_pool_ingest_high_confidence(temp_pool):
    """Signals with high confidence are accepted."""
    sig = TrainingSignal(
        impact_g=4.5,
        gyro_delta=35.0,
        speed_kmh=60.0,
        pseudo_label=1,
        confidence=0.95,
        source="high_confidence_ml",
        event_id="EVT_01",
        device_id="DEV_01",
    )
    assert temp_pool.add_signal(sig) is True
    stats = temp_pool.get_stats()
    assert stats.total_samples == 1
    assert stats.crash_count == 1


def test_training_pool_rejects_ambiguous_automated_signal(temp_pool):
    """Automated ML signals in the ambiguous confidence band (e.g. 0.50) are rejected."""
    sig = TrainingSignal(
        impact_g=2.0,
        gyro_delta=5.0,
        speed_kmh=30.0,
        pseudo_label=1,
        confidence=0.50,
        source="high_confidence_ml",
        event_id="EVT_02",
        device_id="DEV_02",
    )
    assert temp_pool.add_signal(sig) is False
    stats = temp_pool.get_stats()
    assert stats.total_samples == 0


def test_training_pool_deduplication(temp_pool):
    """Near-duplicate signals are discarded."""
    sig1 = TrainingSignal(
        impact_g=3.0,
        gyro_delta=10.0,
        speed_kmh=40.0,
        pseudo_label=1,
        confidence=0.92,
        source="sos_confirmed",
        event_id="EVT_03A",
        device_id="DEV_03",
    )
    sig2 = TrainingSignal(
        impact_g=3.01,
        gyro_delta=10.05,
        speed_kmh=40.1,
        pseudo_label=1,
        confidence=0.92,
        source="sos_confirmed",
        event_id="EVT_03B",
        device_id="DEV_03",
    )
    assert temp_pool.add_signal(sig1) is True
    assert temp_pool.add_signal(sig2) is False
    assert temp_pool.get_stats().total_samples == 1
