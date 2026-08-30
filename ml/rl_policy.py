"""
Reinforcement Learning Policy Optimizer — Contextual Bandit for emergency decision actions.

Per README §12 & §33: RL optimizes the response/decision policy (escalate,
observe, reject) rather than replacing the classifier, and is always constrained
by the deterministic Safety Gate.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

import numpy as np
from pydantic import BaseModel

import config
from logger import get_logger, log_event
from models import ClassificationResult, DeviceContext, ImpactPayload
from safety_gate import SafetyGate, SafetyGateResult

_logger = get_logger("rl_policy")

ACTIONS = ["reject", "observe", "escalate"]
ACTION_TO_IDX = {"reject": 0, "observe": 1, "escalate": 2}
IDX_TO_ACTION = {0: "reject", 1: "observe", 2: "escalate"}

# Asymmetric rewards enforcing safety
REWARD_TRUE_POSITIVE = 1.0
REWARD_FALSE_POSITIVE = -0.5
REWARD_FALSE_NEGATIVE = -2.0  # Heavy penalty for missed accidents
REWARD_TRUE_NEGATIVE = 0.2
REWARD_TIMELY_OBSERVE = 0.3


class RLActionProposal(BaseModel):
    """Action proposed by the RL policy."""

    action: str  # "reject" | "observe" | "escalate"
    action_idx: int
    q_values: list[float]
    state_idx: int
    is_exploratory: bool


class RLPolicyOptimizer:
    """
    Contextual Q-Bandit policy optimizer wrapped with SafetyGate veto authority.
    """

    def __init__(
        self,
        safety_gate: Optional[SafetyGate] = None,
        epsilon: float = config.RL_EPSILON,
        learning_rate: float = config.RL_LEARNING_RATE,
        discount: float = config.RL_DISCOUNT_FACTOR,
        q_table_path: Optional[str] = None,
    ) -> None:
        self.safety_gate = safety_gate or SafetyGate()
        self.epsilon = epsilon
        self.learning_rate = learning_rate
        self.discount = discount
        self.q_table_path = q_table_path or os.path.join(
            os.path.dirname(__file__), "rl_q_table.json"
        )

        # 4 features binned into 4 bins each = 4^4 = 256 states, 3 actions
        self.num_states = 256
        self.num_actions = len(ACTIONS)
        self.q_table = np.zeros((self.num_states, self.num_actions), dtype=np.float64)

        # Initialize Q-table with heuristic defaults so it starts safe
        self._initialize_baseline_q_table()
        self._load_q_table()

        self.total_steps = 0
        self.total_rewards = 0.0
        self.experience_log: list[dict[str, Any]] = []

    def _initialize_baseline_q_table(self) -> None:
        """Seed Q-table with deterministic prior."""
        for state_idx in range(self.num_states):
            # Decompose state_idx -> (i_bin, g_bin, s_bin, c_bin)
            c_bin = state_idx % 4
            s_bin = (state_idx // 4) % 4
            g_bin = (state_idx // 16) % 4
            i_bin = (state_idx // 64) % 4

            if c_bin >= 2 or i_bin >= 2:
                # High confidence or high impact -> prefer escalate
                self.q_table[state_idx, ACTION_TO_IDX["escalate"]] = 0.8
                self.q_table[state_idx, ACTION_TO_IDX["observe"]] = 0.3
                self.q_table[state_idx, ACTION_TO_IDX["reject"]] = -0.5
            elif c_bin == 1 or i_bin == 1:
                # Borderline -> prefer observe
                self.q_table[state_idx, ACTION_TO_IDX["observe"]] = 0.6
                self.q_table[state_idx, ACTION_TO_IDX["reject"]] = 0.2
                self.q_table[state_idx, ACTION_TO_IDX["escalate"]] = 0.0
            else:
                # Low impact & low confidence -> prefer reject
                self.q_table[state_idx, ACTION_TO_IDX["reject"]] = 0.7
                self.q_table[state_idx, ACTION_TO_IDX["observe"]] = 0.1
                self.q_table[state_idx, ACTION_TO_IDX["escalate"]] = -0.5

    def _discretize_state(
        self,
        impact: ImpactPayload,
        context: DeviceContext,
        ml_confidence: float,
    ) -> int:
        """Discretize continuous state into a unique state index (0..255)."""
        # 1. impact_g: [0..1.2), [1.2..3.0), [3.0..4.5), [4.5..inf)
        if impact.impact_g < 1.2:
            i_bin = 0
        elif impact.impact_g < 3.0:
            i_bin = 1
        elif impact.impact_g < 4.5:
            i_bin = 2
        else:
            i_bin = 3

        # 2. gyro_delta: [0..2.0), [2.0..10.0), [10.0..50.0), [50.0..inf)
        if impact.gyro_delta < 2.0:
            g_bin = 0
        elif impact.gyro_delta < 10.0:
            g_bin = 1
        elif impact.gyro_delta < 50.0:
            g_bin = 2
        else:
            g_bin = 3

        # 3. speed_kmh: [0..5.0), [5.0..30.0), [30.0..80.0), [80.0..inf)
        speed = context.recent_speed or 0.0
        if speed < 5.0:
            s_bin = 0
        elif speed < 30.0:
            s_bin = 1
        elif speed < 80.0:
            s_bin = 2
        else:
            s_bin = 3

        # 4. ml_confidence: [0..0.3), [0.3..0.6), [0.6..0.85), [0.85..1.0]
        if ml_confidence < 0.3:
            c_bin = 0
        elif ml_confidence < 0.6:
            c_bin = 1
        elif ml_confidence < 0.85:
            c_bin = 2
        else:
            c_bin = 3

        return int(i_bin * 64 + g_bin * 16 + s_bin * 4 + c_bin)

    def propose_action(
        self,
        impact: ImpactPayload,
        context: DeviceContext,
        ml_confidence: float,
        exploit_only: bool = False,
    ) -> RLActionProposal:
        """Propose an action using epsilon-greedy exploration."""
        state_idx = self._discretize_state(impact, context, ml_confidence)
        q_vals = self.q_table[state_idx].tolist()

        is_exploratory = False
        if not exploit_only and np.random.rand() < self.epsilon:
            action_idx = int(np.random.randint(0, self.num_actions))
            is_exploratory = True
        else:
            action_idx = int(np.argmax(self.q_table[state_idx]))

        action_name = IDX_TO_ACTION[action_idx]

        return RLActionProposal(
            action=action_name,
            action_idx=action_idx,
            q_values=q_vals,
            state_idx=state_idx,
            is_exploratory=is_exploratory,
        )

    def safe_decide(
        self,
        ml_result: ClassificationResult,
        impact: ImpactPayload,
        context: DeviceContext,
        is_manual_sos: bool = False,
    ) -> tuple[RLActionProposal, SafetyGateResult]:
        """
        Produce an RL action proposal and apply the Safety Gate override.
        The Safety Gate ALWAYS has final authority.
        """
        proposal = self.propose_action(impact, context, ml_result.confidence)

        # Map RL action proposal to candidate classification
        if proposal.action == "escalate":
            candidate_ml = ClassificationResult(
                decision="accident",
                confidence=max(ml_result.confidence, 0.7),
                reason=f"RL proposal: {proposal.action} (state={proposal.state_idx})",
            )
        elif proposal.action == "observe":
            candidate_ml = ClassificationResult(
                decision="no_accident",
                confidence=min(ml_result.confidence, 0.45),
                reason=f"RL proposal: {proposal.action} (state={proposal.state_idx})",
            )
        else:
            candidate_ml = ClassificationResult(
                decision="no_accident",
                confidence=min(ml_result.confidence, 0.15),
                reason=f"RL proposal: {proposal.action} (state={proposal.state_idx})",
            )

        # Enforce safety constraints
        safety_result = self.safety_gate.evaluate(
            ml_result=candidate_ml,
            impact=impact,
            context=context,
            is_manual_sos=is_manual_sos,
        )

        return proposal, safety_result

    def update_policy(
        self,
        state_idx: int,
        action_idx: int,
        reward: float,
        next_state_idx: Optional[int] = None,
    ) -> float:
        """Perform Q-learning update step."""
        current_q = self.q_table[state_idx, action_idx]
        next_max_q = (
            np.max(self.q_table[next_state_idx])
            if next_state_idx is not None
            else 0.0
        )

        # Bellman update
        target = reward + self.discount * next_max_q
        td_error = target - current_q
        new_q = current_q + self.learning_rate * td_error
        self.q_table[state_idx, action_idx] = float(new_q)

        self.total_steps += 1
        self.total_rewards += reward
        self.experience_log.append({
            "state_idx": state_idx,
            "action": IDX_TO_ACTION.get(action_idx, "unknown"),
            "reward": reward,
            "td_error": round(float(td_error), 4),
        })

        # Save checkpoint periodically
        if self.total_steps % 20 == 0:
            self._save_q_table()

        return float(new_q)

    def compute_reward_from_outcome(
        self,
        proposed_action: str,
        actual_is_accident: bool,
    ) -> float:
        """Calculate asymmetric reward based on operational ground truth."""
        if proposed_action == "escalate" and actual_is_accident:
            return REWARD_TRUE_POSITIVE
        elif proposed_action == "escalate" and not actual_is_accident:
            return REWARD_FALSE_POSITIVE
        elif proposed_action == "reject" and actual_is_accident:
            return REWARD_FALSE_NEGATIVE
        elif proposed_action == "reject" and not actual_is_accident:
            return REWARD_TRUE_NEGATIVE
        elif proposed_action == "observe":
            return REWARD_TIMELY_OBSERVE
        return 0.0

    def _save_q_table(self) -> None:
        """Persist Q-table to disk."""
        try:
            data = {
                "q_table": self.q_table.tolist(),
                "total_steps": self.total_steps,
                "total_rewards": self.total_rewards,
                "epsilon": self.epsilon,
            }
            with open(self.q_table_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            log_event(_logger, action="save_q_table_error", error=str(exc))

    def _load_q_table(self) -> None:
        """Load persisted Q-table from disk if present."""
        if os.path.exists(self.q_table_path):
            try:
                with open(self.q_table_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.q_table = np.array(data["q_table"], dtype=np.float64)
                    self.total_steps = data.get("total_steps", 0)
                    self.total_rewards = data.get("total_rewards", 0.0)
            except Exception as exc:
                log_event(_logger, action="load_q_table_error", error=str(exc))

    def get_stats(self) -> dict[str, Any]:
        """Return operational statistics of the RL policy."""
        return {
            "total_steps": self.total_steps,
            "total_rewards": round(self.total_rewards, 4),
            "average_reward": (
                round(self.total_rewards / self.total_steps, 4)
                if self.total_steps > 0
                else 0.0
            ),
            "epsilon": self.epsilon,
            "learning_rate": self.learning_rate,
            "num_states": self.num_states,
            "num_actions": self.num_actions,
            "recent_experiences": self.experience_log[-10:],
        }
