"""
Unit tests for Continual Retraining cycle and candidate validation.
"""

import shutil
import tempfile
import pytest

import continual_trainer
from model_registry import ModelRegistry
from training_pool import TrainingPool, TrainingSignal


@pytest.fixture
def temp_environment():
    temp_dir = tempfile.mkdtemp()
    pool = TrainingPool(pool_dir=temp_dir)
    reg = ModelRegistry(registry_dir=temp_dir)
    yield pool, reg
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_continual_trainer_respects_pool_not_ready(temp_environment):
    """Retraining without force flag aborts if pool is too small."""
    pool, reg = temp_environment
    result = continual_trainer.run_retraining_cycle(pool=pool, registry=reg, force=False)
    assert result.success is False
    assert "not ready" in result.reason


def test_continual_trainer_force_cycle(temp_environment):
    """Retraining with force=True successfully trains candidate and evaluates safety."""
    pool, reg = temp_environment

    # Add a couple of synthetic signals
    pool.add_signal(
        TrainingSignal(
            impact_g=5.0,
            gyro_delta=40.0,
            speed_kmh=60.0,
            pseudo_label=1,
            confidence=0.95,
            source="manual_feedback",
            event_id="EVT_FORCED_01",
            device_id="DEV_01",
        )
    )

    result = continual_trainer.run_retraining_cycle(
        pool=pool, registry=reg, auto_promote=False, force=True
    )
    assert result.success is True
    assert result.candidate_version is not None
    assert result.safety_check_passed is True
    assert "f1_score" in result.candidate_metrics
