"""
Model Registry — File-based versioned artifact and model management.

Manages model versions, manifests, promotion, rollback, and offline evaluation
comparisons in a structured directory layout under config.REGISTRY_DIR.

Directory structure:
  ml/registry/
  ├── manifest.json
  ├── v1/
  │   ├── model.pkl
  │   ├── metadata.json
  │   └── evaluation.json
  └── v2/
      └── ...
"""

from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from typing import Any, Optional

import joblib
from pydantic import BaseModel, Field

import config
from logger import get_logger, log_event

_logger = get_logger("model_registry")


class ModelVersion(BaseModel):
    """Metadata describing a registered model version."""

    version: str
    created_at: str
    dataset_hash: str
    metrics: dict[str, float]
    is_active: bool = False
    promoted_at: Optional[str] = None
    feature_importances: dict[str, float] = Field(default_factory=dict)
    description: str = ""
    model_path: str = ""


class RegistryManifest(BaseModel):
    """Top-level manifest tracking active version and history."""

    active_version: Optional[str] = None
    previous_version: Optional[str] = None
    versions: dict[str, ModelVersion] = Field(default_factory=dict)
    last_updated: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ModelRegistry:
    """
    File-based Model Registry.

    Supports atomic versioning, promotion, rollbacks, and manifest updates.
    """

    def __init__(self, registry_dir: str = config.REGISTRY_DIR) -> None:
        self.registry_dir = os.path.abspath(registry_dir)
        self.manifest_path = os.path.join(self.registry_dir, "manifest.json")
        os.makedirs(self.registry_dir, exist_ok=True)
        self._manifest: RegistryManifest = self._load_or_create_manifest()

    def _load_or_create_manifest(self) -> RegistryManifest:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return RegistryManifest.model_validate(data)
            except Exception as exc:
                log_event(
                    _logger,
                    action="manifest_load_error",
                    error=str(exc),
                    path=self.manifest_path,
                )
        manifest = RegistryManifest()
        self._save_manifest(manifest)
        return manifest

    def _save_manifest(self, manifest: Optional[RegistryManifest] = None) -> None:
        if manifest is not None:
            self._manifest = manifest
        self._manifest.last_updated = datetime.now(timezone.utc).isoformat()
        temp_path = f"{self.manifest_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self._manifest.model_dump(), f, indent=2)
        shutil.move(temp_path, self.manifest_path)

    def get_manifest(self) -> RegistryManifest:
        """Return the current registry manifest."""
        return self._manifest

    def list_versions(self) -> list[ModelVersion]:
        """Return all registered model versions."""
        return list(self._manifest.versions.values())

    def get_version_metadata(self, version: str) -> Optional[ModelVersion]:
        """Fetch metadata for a specific version."""
        return self._manifest.versions.get(version)

    def register(
        self,
        pipeline_artifact: Any,
        metrics: dict[str, float],
        dataset_hash: str,
        feature_importances: Optional[dict[str, float]] = None,
        description: str = "",
        set_active: bool = False,
    ) -> ModelVersion:
        """
        Register a new model version into the registry.
        """
        existing_versions = [
            int(v.lstrip("v"))
            for v in self._manifest.versions.keys()
            if v.startswith("v") and v.lstrip("v").isdigit()
        ]
        next_idx = max(existing_versions, default=0) + 1
        version_tag = f"v{next_idx}"

        version_dir = os.path.join(self.registry_dir, version_tag)
        os.makedirs(version_dir, exist_ok=True)

        model_file = os.path.join(version_dir, "model.pkl")
        joblib.dump(pipeline_artifact, model_file)

        now_iso = datetime.now(timezone.utc).isoformat()
        metadata = ModelVersion(
            version=version_tag,
            created_at=now_iso,
            dataset_hash=dataset_hash,
            metrics=metrics,
            is_active=False,
            promoted_at=None,
            feature_importances=feature_importances or {},
            description=description,
            model_path=model_file,
        )

        meta_path = os.path.join(version_dir, "metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2)

        self._manifest.versions[version_tag] = metadata
        self._save_manifest()

        log_event(
            _logger,
            action="model_registered",
            version=version_tag,
            f1=metrics.get("f1_score", metrics.get("f1", 0.0)),
            accuracy=metrics.get("accuracy", 0.0),
        )

        if set_active:
            self.promote(version_tag)

        return self._manifest.versions[version_tag]

    def promote(self, version: str) -> bool:
        """
        Promote a version to active status.
        """
        if version not in self._manifest.versions:
            log_event(
                _logger,
                action="promotion_failed_not_found",
                target_version=version,
            )
            return False

        old_active = self._manifest.active_version
        if old_active and old_active in self._manifest.versions:
            self._manifest.versions[old_active].is_active = False

        self._manifest.previous_version = old_active
        self._manifest.active_version = version

        target_meta = self._manifest.versions[version]
        target_meta.is_active = True
        target_meta.promoted_at = datetime.now(timezone.utc).isoformat()

        # Update metadata file in version dir
        version_dir = os.path.join(self.registry_dir, version)
        meta_path = os.path.join(version_dir, "metadata.json")
        if os.path.exists(version_dir):
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(target_meta.model_dump(), f, indent=2)

        self._save_manifest()
        log_event(
            _logger,
            action="model_promoted",
            previous_version=old_active,
            active_version=version,
        )
        return True

    def rollback(self) -> Optional[str]:
        """
        Roll back active model to the previously active version.
        """
        prev = self._manifest.previous_version
        if not prev or prev not in self._manifest.versions:
            log_event(_logger, action="rollback_failed_no_previous")
            return None

        success = self.promote(prev)
        if success:
            log_event(_logger, action="model_rollback_success", restored_version=prev)
            return prev
        return None

    def get_active(self) -> tuple[Any, ModelVersion]:
        """
        Load and return the currently active model pipeline and metadata.
        """
        active_ver = self._manifest.active_version
        if not active_ver or active_ver not in self._manifest.versions:
            raise RuntimeError(
                f"No active model found in registry at {self.registry_dir}."
            )

        meta = self._manifest.versions[active_ver]
        model_path = meta.model_path
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model file for active version {active_ver} not found at {model_path}."
            )

        loaded = joblib.load(model_path)
        pipeline = loaded["pipeline"] if isinstance(loaded, dict) and "pipeline" in loaded else loaded
        return pipeline, meta

    def get_version(self, version: str) -> tuple[Any, ModelVersion]:
        """
        Load and return a specific model version and metadata.
        """
        if version not in self._manifest.versions:
            raise KeyError(f"Version {version} not found in registry.")

        meta = self._manifest.versions[version]
        model_path = meta.model_path
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model artifact not found for {version} at {model_path}."
            )

        loaded = joblib.load(model_path)
        pipeline = loaded["pipeline"] if isinstance(loaded, dict) and "pipeline" in loaded else loaded
        return pipeline, meta

    def compare(self, v1: str, v2: str) -> dict[str, Any]:
        """
        Compare metrics and feature importances between two versions.
        """
        meta1 = self._manifest.versions.get(v1)
        meta2 = self._manifest.versions.get(v2)
        if not meta1 or not meta2:
            raise KeyError(f"One or both versions ({v1}, {v2}) do not exist in registry.")

        metric_diffs = {}
        all_metric_keys = set(meta1.metrics.keys()) | set(meta2.metrics.keys())
        for k in all_metric_keys:
            val1 = meta1.metrics.get(k, 0.0)
            val2 = meta2.metrics.get(k, 0.0)
            metric_diffs[k] = {
                v1: val1,
                v2: val2,
                "delta": round(val2 - val1, 4),
            }

        return {
            "v1": v1,
            "v2": v2,
            "metrics_comparison": metric_diffs,
            "v1_created": meta1.created_at,
            "v2_created": meta2.created_at,
        }
