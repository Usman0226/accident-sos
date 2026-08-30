"""
Machine Learning Accident Classifier using pickled Scikit-Learn Pipeline
backed by ModelRegistry with hot-reload capability.

Exposes inference helper functions for real-time sensor telemetry classification.
"""

from __future__ import annotations

import os
from typing import Any, Optional
import joblib
import pandas as pd

from models import ClassificationResult, DeviceContext, ImpactPayload
from feature_pipeline import IMUFeatureTransformer  # Ensure unpickling context
import model_registry
from logger import get_logger, log_event

_logger = get_logger("ml_classifier")
DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "accident_classifier.pkl")


def load_pipeline(model_path: str = DEFAULT_MODEL_PATH) -> Any:
    """
    Load pickled Scikit-Learn Pipeline from disk.

    Supports both direct Pipeline objects and dictionary artifacts.
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model file not found at {model_path}. Run train_model.py first."
        )

    loaded = joblib.load(model_path)
    if isinstance(loaded, dict) and "pipeline" in loaded:
        return loaded["pipeline"]
    return loaded


class MLAccidentClassifier:
    """Singleton-friendly wrapper for ML Pipeline inference with registry support."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        registry: Optional[model_registry.ModelRegistry] = None,
    ) -> None:
        self.registry = registry
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self.active_version: Optional[str] = None
        self._pipeline: Any = None
        self.reload()

    def reload(self) -> None:
        """Hot-reload model pipeline from registry or model_path."""
        if self.registry is not None:
            try:
                pipeline, meta = self.registry.get_active()
                self._pipeline = pipeline
                self.active_version = meta.version
                log_event(
                    _logger,
                    action="model_hot_reloaded",
                    source="registry",
                    version=self.active_version,
                )
                return
            except Exception as exc:
                log_event(
                    _logger,
                    action="registry_load_fallback",
                    error=str(exc),
                )

        # Fallback to direct path
        self._pipeline = load_pipeline(self.model_path)
        self.active_version = "direct_file"
        log_event(
            _logger,
            action="model_loaded",
            source="file",
            path=self.model_path,
        )

    def predict_payload(
        self, impact: ImpactPayload, context: DeviceContext
    ) -> ClassificationResult:
        """
        Classify an incoming ImpactPayload using the active ML pipeline.
        """
        speed = context.recent_speed if context.recent_speed is not None else 0.0

        sample = {
            "impact_g": impact.impact_g,
            "gyro_delta": impact.gyro_delta,
            "Speed_kmh": speed,
        }

        df_sample = pd.DataFrame([sample])
        probs = self._pipeline.predict_proba(df_sample)[0]
        prediction = self._pipeline.predict(df_sample)[0]

        crash_prob = float(probs[1]) if len(probs) > 1 else float(prediction)
        decision = "accident" if prediction == 1 else "no_accident"
        version_label = f"[{self.active_version}] " if self.active_version else ""
        reason = (
            f"{version_label}ML Pipeline (Calibrated RF): crash_prob={crash_prob:.4f}, "
            f"impact_g={impact.impact_g:.2f}, gyro_delta={impact.gyro_delta:.2f}, "
            f"speed={speed:.1f} km/h"
        )

        return ClassificationResult(
            decision=decision,
            confidence=round(crash_prob, 2),
            reason=reason,
        )


_global_classifier: Optional[MLAccidentClassifier] = None


def set_global_classifier(classifier: MLAccidentClassifier) -> None:
    """Set the global MLAccidentClassifier instance."""
    global _global_classifier
    _global_classifier = classifier


def get_global_classifier() -> MLAccidentClassifier:
    """Retrieve global classifier instance or instantiate with registry."""
    global _global_classifier
    if _global_classifier is None:
        reg = model_registry.ModelRegistry()
        _global_classifier = MLAccidentClassifier(registry=reg)
    return _global_classifier


def classify_ml(impact: ImpactPayload, context: DeviceContext) -> ClassificationResult:
    """Global helper for classifying impact using the active ML pipeline."""
    return get_global_classifier().predict_payload(impact, context)
