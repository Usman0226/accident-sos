"""
Unit tests for Reinforcement Learning Policy Optimizer and Safety Gate enforcement.
"""

import os
import shutil
import tempfile
import time
import pytest

from models import ClassificationResult, DeviceContext, ImpactPayload
from rl_policy import RLPolicyOptimizer, ACTION_TO_IDX
from safety_gate import SafetyGate


@pytest.fixture
def temp_rl():
    temp_dir = tempfile.mkdtemp()
    q_path = os.path.join(temp_dir, "test_q.json")
    gate = SafetyGate()
    optimizer = RLPolicyOptimizer(safety_gate=gate, q_table_path=q_path)
    yield optimizer
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_rl_policy_safe_decide_severe_impact(temp_rl):
    """Safety Gate must override any RL action if impact is severe (>4.5g)."""
    impact = ImpactPayload(
        device_id="DEV_RL_01",
        timestamp=time.time(),
        impact_g=6.0,
        gyro_delta=1.0,
        gps_lat=17.385,
        gps_lon=78.487,
        gps_fix=True,
    )
    context = DeviceContext(recent_speed=40.0)
    ml_result = ClassificationResult(decision="no_accident", confidence=0.10, reason="low gyro")

    # Force RL to prefer 'reject' for this state
    state_idx = temp_rl._discretize_state(impact, context, ml_result.confidence)
    temp_rl.q_table[state_idx, :] = -1.0
    temp_rl.q_table[state_idx, ACTION_TO_IDX["reject"]] = 10.0

    proposal, safety_result = temp_rl.safe_decide(ml_result, impact, context)
    assert proposal.action == "reject"
    assert safety_result.final_decision == "accident"
    assert safety_result.was_overridden is True
    assert "severe_impact_override" in safety_result.override_reason


def test_rl_policy_q_update(temp_rl):
    """Q-learning Bellman update step updates Q-table values properly."""
    state_idx = 100
    action_idx = 2  # escalate
    initial_q = temp_rl.q_table[state_idx, action_idx]

    new_q = temp_rl.update_policy(state_idx=state_idx, action_idx=action_idx, reward=1.0)
    assert new_q > initial_q
    assert temp_rl.total_steps == 1
    assert temp_rl.total_rewards == 1.0
