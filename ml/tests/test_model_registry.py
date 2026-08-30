"""
Unit tests for Model Registry versioning, promotion, rollback, and comparison.
"""

import shutil
import tempfile
import pytest

from model_registry import ModelRegistry


@pytest.fixture
def temp_registry():
    temp_dir = tempfile.mkdtemp()
    reg = ModelRegistry(registry_dir=temp_dir)
    yield reg
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_model_registry_register_and_promote(temp_registry):
    """Test registering multiple versions and promoting between them."""
    mock_pipeline_1 = {"name": "model_v1"}
    mock_pipeline_2 = {"name": "model_v2"}

    # Register v1
    v1 = temp_registry.register(
        pipeline_artifact=mock_pipeline_1,
        metrics={"accuracy": 0.95, "f1_score": 0.94},
        dataset_hash="hash_v1",
        description="First version",
        set_active=True,
    )
    assert v1.version == "v1"
    assert v1.is_active is True

    # Register v2
    v2 = temp_registry.register(
        pipeline_artifact=mock_pipeline_2,
        metrics={"accuracy": 0.98, "f1_score": 0.97},
        dataset_hash="hash_v2",
        description="Second version",
        set_active=False,
    )
    assert v2.version == "v2"
    assert v2.is_active is False

    # Check active model
    _, active_meta = temp_registry.get_active()
    assert active_meta.version == "v1"

    # Promote v2
    assert temp_registry.promote("v2") is True
    _, new_active_meta = temp_registry.get_active()
    assert new_active_meta.version == "v2"

    # Rollback to v1
    restored = temp_registry.rollback()
    assert restored == "v1"
    _, restored_meta = temp_registry.get_active()
    assert restored_meta.version == "v1"


def test_model_registry_compare(temp_registry):
    """Test comparing metrics between two model versions."""
    temp_registry.register(
        pipeline_artifact={"name": "model_v1"},
        metrics={"f1_score": 0.90, "accuracy": 0.92},
        dataset_hash="h1",
    )
    temp_registry.register(
        pipeline_artifact={"name": "model_v2"},
        metrics={"f1_score": 0.95, "accuracy": 0.96},
        dataset_hash="h2",
    )

    diff = temp_registry.compare("v1", "v2")
    assert "metrics_comparison" in diff
    f1_diff = diff["metrics_comparison"]["f1_score"]
    assert f1_diff["delta"] == 0.05
