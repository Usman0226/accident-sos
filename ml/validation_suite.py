"""
Broader Validation Suite — Systematic scenario-based evaluation matrix.

Per README §29 & §32: Validate model behaviors across diverse speeds, surfaces,
impact geometries, false alarm non-crash events, and severe crash profiles.
"""

from __future__ import annotations

from typing import Any, Optional
import pandas as pd
from pydantic import BaseModel, Field

from logger import get_logger, log_event

_logger = get_logger("validation_suite")


class ValidationScenario(BaseModel):
    """A realistic test scenario to validate classification behavior."""

    name: str
    category: str  # "speed_profile" | "road_surface" | "false_alarm" | "severe_crash"
    impact_g: float
    gyro_delta: float
    speed_kmh: float
    expected_decision: str  # "accident" | "no_accident"
    expected_min_prob: Optional[float] = None
    expected_max_prob: Optional[float] = None
    description: str = ""


class ScenarioResult(BaseModel):
    """Outcome of a single validation scenario."""

    scenario: ValidationScenario
    actual_decision: str
    crash_prob: float
    passed: bool
    failure_reason: Optional[str] = None


class ValidationReport(BaseModel):
    """Aggregated validation suite report."""

    total_scenarios: int
    passed_count: int
    failed_count: int
    pass_rate: float
    all_passed: bool
    results: list[ScenarioResult]


def generate_validation_scenarios() -> list[ValidationScenario]:
    """Generate the standardized test matrix covering all critical operating conditions."""
    return [
        # --- Category 1: Road Surface / Non-Crash Disturbances ---
        ValidationScenario(
            name="Severe Deep Pothole",
            category="road_surface",
            impact_g=5.8,
            gyro_delta=0.4,
            speed_kmh=50.0,
            expected_decision="no_accident",
            expected_max_prob=0.45,
            description="High vertical acceleration spike with near-zero rotational delta.",
        ),
        ValidationScenario(
            name="Speed Table / Speed Bump",
            category="road_surface",
            impact_g=2.8,
            gyro_delta=0.3,
            speed_kmh=25.0,
            expected_decision="no_accident",
            expected_max_prob=0.40,
            description="Moderate vertical displacement over bump at city speed.",
        ),
        ValidationScenario(
            name="Rough Gravel Washboard",
            category="road_surface",
            impact_g=1.8,
            gyro_delta=1.2,
            speed_kmh=40.0,
            expected_decision="no_accident",
            expected_max_prob=0.35,
            description="Continuous vibration without genuine impact shock.",
        ),

        # --- Category 2: Vehicle Handling / False Alarms ---
        ValidationScenario(
            name="Emergency Hard Braking",
            category="false_alarm",
            impact_g=2.2,
            gyro_delta=0.8,
            speed_kmh=75.0,
            expected_decision="no_accident",
            expected_max_prob=0.40,
            description="Strong longitudinal deceleration without rotational instability.",
        ),
        ValidationScenario(
            name="Aggressive Slalom Turn",
            category="false_alarm",
            impact_g=1.1,
            gyro_delta=110.0,
            speed_kmh=55.0,
            expected_decision="no_accident",
            expected_max_prob=0.45,
            description="High angular rate but low net impact shock.",
        ),
        ValidationScenario(
            name="Heavy Trunk / Door Slam",
            category="false_alarm",
            impact_g=4.2,
            gyro_delta=0.2,
            speed_kmh=0.0,
            expected_decision="no_accident",
            expected_max_prob=0.40,
            description="Local shock at standstill with no angular motion.",
        ),

        # --- Category 3: True Crashes Across Speed Profiles ---
        ValidationScenario(
            name="Highway Head-On Collision",
            category="severe_crash",
            impact_g=8.5,
            gyro_delta=45.0,
            speed_kmh=90.0,
            expected_decision="accident",
            expected_min_prob=0.75,
            description="Extreme impact shock at high speed with significant rotation.",
        ),
        ValidationScenario(
            name="City T-Bone Side Impact",
            category="severe_crash",
            impact_g=5.5,
            gyro_delta=95.0,
            speed_kmh=45.0,
            expected_decision="accident",
            expected_min_prob=0.70,
            description="High lateral acceleration with rapid vehicle spin.",
        ),
        ValidationScenario(
            name="Vehicle Rollover",
            category="severe_crash",
            impact_g=4.2,
            gyro_delta=180.0,
            speed_kmh=60.0,
            expected_decision="accident",
            expected_min_prob=0.70,
            description="Sustained extreme angular rate with multiple impact contacts.",
        ),
        ValidationScenario(
            name="City Fender Bender",
            category="severe_crash",
            impact_g=3.8,
            gyro_delta=25.0,
            speed_kmh=35.0,
            expected_decision="accident",
            expected_min_prob=0.60,
            description="Moderate impact with clear rotational offset at driving speed.",
        ),

        # --- Category 4: Normal Driving Baseline ---
        ValidationScenario(
            name="Smooth Highway Cruising",
            category="normal_driving",
            impact_g=0.2,
            gyro_delta=0.8,
            speed_kmh=100.0,
            expected_decision="no_accident",
            expected_max_prob=0.15,
            description="Clean highway driving with negligible disturbances.",
        ),
        ValidationScenario(
            name="City Stop-and-Go Traffic",
            category="normal_driving",
            impact_g=0.4,
            gyro_delta=1.5,
            speed_kmh=20.0,
            expected_decision="no_accident",
            expected_max_prob=0.20,
            description="Frequent start/stops with minor road texture.",
        ),
    ]


def run_validation_suite(pipeline: Any) -> ValidationReport:
    """
    Execute all validation scenarios against a given Scikit-Learn pipeline.
    """
    scenarios = generate_validation_scenarios()
    results: list[ScenarioResult] = []

    for sc in scenarios:
        sample_df = pd.DataFrame([{
            "impact_g": sc.impact_g,
            "gyro_delta": sc.gyro_delta,
            "Speed_kmh": sc.speed_kmh,
        }])

        probs = pipeline.predict_proba(sample_df)[0]
        crash_prob = float(probs[1]) if len(probs) > 1 else float(probs[0])
        decision = "accident" if crash_prob >= 0.5 else "no_accident"

        # Evaluate rules
        passed = True
        failure_reasons = []

        if decision != sc.expected_decision:
            passed = False
            failure_reasons.append(
                f"Decision mismatch: expected {sc.expected_decision}, got {decision}"
            )

        if sc.expected_min_prob is not None and crash_prob < sc.expected_min_prob:
            passed = False
            failure_reasons.append(
                f"Crash prob {crash_prob:.4f} < expected minimum {sc.expected_min_prob}"
            )

        if sc.expected_max_prob is not None and crash_prob > sc.expected_max_prob:
            passed = False
            failure_reasons.append(
                f"Crash prob {crash_prob:.4f} > expected maximum {sc.expected_max_prob}"
            )

        reason_str = "; ".join(failure_reasons) if failure_reasons else None
        results.append(
            ScenarioResult(
                scenario=sc,
                actual_decision=decision,
                crash_prob=round(crash_prob, 4),
                passed=passed,
                failure_reason=reason_str,
            )
        )

    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    pass_rate = round((passed_count / total_count), 4) if total_count > 0 else 0.0

    report = ValidationReport(
        total_scenarios=total_count,
        passed_count=passed_count,
        failed_count=total_count - passed_count,
        pass_rate=pass_rate,
        all_passed=passed_count == total_count,
        results=results,
    )

    log_event(
        _logger,
        action="validation_suite_executed",
        total=total_count,
        passed=passed_count,
        pass_rate=f"{pass_rate:.2%}",
    )

    return report
