"""
Scikit-Learn Feature Transformation and Pipeline construction for Accident Detection.

Provides IMUFeatureTransformer for turning raw sensor telemetries or DataFrames
into structured feature matrices, and build_ml_pipeline() to instantiate the
complete end-to-end classification pipeline.
"""

from __future__ import annotations

import math
from typing import Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline


class IMUFeatureTransformer(BaseEstimator, TransformerMixin):
    """
    Scikit-Learn Transformer for IMU sensor feature extraction.

    Transforms raw IMU DataFrames, dictionaries, or lists of records into
    a 2D numpy feature array containing:
      1. impact_g: Absolute deviation from resting gravity (9.81 m/s^2)
      2. gyro_delta: Angular velocity magnitude in degrees/second
      3. Speed_kmh: Vehicle speed in km/h
    """

    def __init__(self, gravity_constant: float = 9.81, include_speed: bool = True) -> None:
        self.gravity_constant = gravity_constant
        self.include_speed = include_speed

    def fit(self, X: Any, y: Any = None) -> IMUFeatureTransformer:
        return self

    def transform(self, X: Any) -> np.ndarray:
        if isinstance(X, pd.DataFrame):
            df = X.copy()
        elif isinstance(X, dict):
            df = pd.DataFrame([X])
        elif isinstance(X, list):
            df = pd.DataFrame(X)
        elif isinstance(X, np.ndarray):
            expected_cols = 3 if self.include_speed else 2
            if X.ndim == 2 and X.shape[1] == expected_cols:
                return X.astype(np.float64)
            df = pd.DataFrame(X)
        else:
            raise ValueError(f"Unsupported input type for IMUFeatureTransformer: {type(X)}")

        # 1. Compute impact_g (deviation from 9.81 m/s^2)
        if "impact_g" in df.columns and not df["impact_g"].isna().all():
            impact_s = df["impact_g"].astype(float)
            if impact_s.isna().any():
                if "Motion_Intensity" in df.columns:
                    fallback = np.abs(df["Motion_Intensity"].astype(float) - self.gravity_constant)
                    impact_s = impact_s.fillna(fallback)
                elif all(col in df.columns for col in ["Acc_X", "Acc_Y", "Acc_Z"]):
                    acc_mag = np.sqrt(
                        df["Acc_X"].astype(float) ** 2 +
                        df["Acc_Y"].astype(float) ** 2 +
                        df["Acc_Z"].astype(float) ** 2
                    )
                    fallback = np.abs(acc_mag - self.gravity_constant)
                    impact_s = impact_s.fillna(fallback)
            impact_g = impact_s.fillna(0.0).values
        elif "Motion_Intensity" in df.columns:
            impact_g = np.abs(df["Motion_Intensity"].astype(float).values - self.gravity_constant)
        elif all(col in df.columns for col in ["Acc_X", "Acc_Y", "Acc_Z"]):
            acc_mag = np.sqrt(
                df["Acc_X"].astype(float).values ** 2 +
                df["Acc_Y"].astype(float).values ** 2 +
                df["Acc_Z"].astype(float).values ** 2
            )
            impact_g = np.abs(acc_mag - self.gravity_constant)
        else:
            raise ValueError("Missing acceleration input to calculate impact_g")

        # 2. Compute gyro_delta (magnitude in deg/s)
        if "gyro_delta" in df.columns and not df["gyro_delta"].isna().all():
            gyro_s = df["gyro_delta"].astype(float)
            if gyro_s.isna().any():
                if all(col in df.columns for col in ["Gyro_X", "Gyro_Y", "Gyro_Z"]):
                    gyro_mag_rads = np.sqrt(
                        df["Gyro_X"].astype(float) ** 2 +
                        df["Gyro_Y"].astype(float) ** 2 +
                        df["Gyro_Z"].astype(float) ** 2
                    )
                    fallback = gyro_mag_rads * (180.0 / math.pi)
                    gyro_s = gyro_s.fillna(fallback)
            gyro_delta = gyro_s.fillna(0.0).values
        elif all(col in df.columns for col in ["Gyro_X", "Gyro_Y", "Gyro_Z"]):
            gyro_mag_rads = np.sqrt(
                df["Gyro_X"].astype(float).values ** 2 +
                df["Gyro_Y"].astype(float).values ** 2 +
                df["Gyro_Z"].astype(float).values ** 2
            )
            gyro_delta = gyro_mag_rads * (180.0 / math.pi)
        else:
            gyro_delta = np.zeros(len(df), dtype=float)

        # 3. Extract Speed_kmh
        if "Speed_kmh" in df.columns:
            speed = df["Speed_kmh"].astype(float).fillna(0.0).values
        elif "speed_kmph" in df.columns:
            speed = df["speed_kmph"].astype(float).fillna(0.0).values
        elif "speed" in df.columns:
            speed = df["speed"].astype(float).fillna(0.0).values
        else:
            speed = np.zeros(len(df), dtype=float)

        if self.include_speed:
            return np.column_stack([impact_g, gyro_delta, speed])
        else:
            return np.column_stack([impact_g, gyro_delta])


def build_ml_pipeline(random_state: int = 42, include_speed: bool = True) -> Pipeline:
    """
    Constructs an end-to-end Scikit-Learn Pipeline combining feature engineering
    and a calibrated Random Forest Classifier.

    Returns:
        sklearn.pipeline.Pipeline ready to fit or predict on raw IMU data.
    """
    base_rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        class_weight="balanced",
        random_state=random_state,
    )
    calibrated_rf = CalibratedClassifierCV(base_rf, method="sigmoid", cv=5)

    return Pipeline([
        ("imu_features", IMUFeatureTransformer(include_speed=include_speed)),
        ("classifier", calibrated_rf),
    ])
