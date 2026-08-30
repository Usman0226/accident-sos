"""
API routes for Reinforcement Learning Policy monitoring and feedback.

Exposes endpoints for querying Q-learning state-action values, inspecting policy
exploration statistics, and submitting ground-truth feedback rewards.
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from logger import get_logger, log_event
import rl_policy

router = APIRouter(prefix="/api/ml/rl", tags=["rl"])
_logger = get_logger("routes.rl")

_rl_instance: Optional[rl_policy.RLPolicyOptimizer] = None


def set_global_rl_optimizer(optimizer: rl_policy.RLPolicyOptimizer) -> None:
    """Set global RLPolicyOptimizer instance."""
    global _rl_instance
    _rl_instance = optimizer


def get_global_rl_optimizer() -> rl_policy.RLPolicyOptimizer:
    """Get global RLPolicyOptimizer instance or instantiate default."""
    global _rl_instance
    if _rl_instance is None:
        _rl_instance = rl_policy.RLPolicyOptimizer()
    return _rl_instance


class RLFeedbackPayload(BaseModel):
    """Payload for submitting reward feedback for an RL state transition."""

    state_idx: int = Field(..., ge=0, le=255)
    action: str = Field(..., pattern=r"^(reject|observe|escalate)$")
    actual_is_accident: bool
    notes: Optional[str] = None


@router.get("/stats")
async def get_rl_stats() -> dict[str, Any]:
    """Retrieve RL policy optimization metrics and exploration status."""
    try:
        optimizer = get_global_rl_optimizer()
        stats = optimizer.get_stats()
        return stats
    except Exception as exc:
        log_event(_logger, action="get_rl_stats_error", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch RL stats: {exc}"
        ) from exc


@router.post("/feedback")
async def submit_rl_feedback(payload: RLFeedbackPayload) -> dict[str, Any]:
    """Submit reward feedback to update the RL Q-policy."""
    try:
        optimizer = get_global_rl_optimizer()
        action_idx = rl_policy.ACTION_TO_IDX[payload.action]
        reward = optimizer.compute_reward_from_outcome(
            proposed_action=payload.action,
            actual_is_accident=payload.actual_is_accident,
        )
        new_q = optimizer.update_policy(
            state_idx=payload.state_idx,
            action_idx=action_idx,
            reward=reward,
        )

        log_event(
            _logger,
            action="rl_feedback_processed",
            state=payload.state_idx,
            action_name=payload.action,
            reward=reward,
            new_q=round(new_q, 4),
        )

        return {
            "status": "updated",
            "state_idx": payload.state_idx,
            "action": payload.action,
            "reward": reward,
            "updated_q_value": round(new_q, 4),
        }
    except Exception as exc:
        log_event(_logger, action="submit_rl_feedback_error", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Failed to apply feedback: {exc}"
        ) from exc
