"""Goal service — business rules for creating, updating, and reading goals.

Calculations:
  progress_pct is computed here (not stored) from starting_value,
  target_value, and current_value.  It is attached to GoalResponse objects
  before they are returned so the frontend never has to recalculate.

Formulas:
  If target > starting:   progress = (current - starting) / (target - starting)
  If target < starting:   progress = (starting - current) / (starting - target)
  (handles both "increase to" and "decrease to" goals)
  Clamped to [0, 100].  Returns None when any value is missing.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ValidationError
from app.models.goal import Goal
from app.repositories import goal_repository
from app.schemas.goals import (
    CreateGoalRequest,
    GoalListResponse,
    GoalResponse,
    UpdateGoalRequest,
)

# ── Progress calculation ──────────────────────────────────────────────────────


def compute_progress_pct(
    starting: float | None,
    target: float | None,
    current: float | None,
) -> float | None:
    """Return progress as a percentage [0, 100], or None if data is insufficient."""
    if target is None or current is None:
        return None

    # If no starting value, treat 0 as the baseline.
    start = starting if starting is not None else 0.0

    span = abs(target - start)
    if span == 0:
        # Target equals starting — immediately 100% if current matches target.
        return 100.0 if current == target else 0.0

    raw = (current - start) / span if target >= start else (start - current) / span

    return round(max(0.0, min(100.0, raw * 100)), 1)


def _to_response(goal: Goal) -> GoalResponse:
    resp = GoalResponse.model_validate(goal)
    resp.progress_pct = compute_progress_pct(
        goal.starting_value, goal.target_value, goal.current_value
    )
    return resp


# ── CRUD ──────────────────────────────────────────────────────────────────────


def create_goal(db: Session, user_id: uuid.UUID, body: CreateGoalRequest) -> GoalResponse:
    fields = body.model_dump(exclude={"goal_type", "title"}, exclude_none=True)
    goal = goal_repository.create_goal(
        db,
        user_id=user_id,
        goal_type=body.goal_type,
        title=body.title,
        **fields,
    )
    return _to_response(goal)


def get_goal(db: Session, goal_id: uuid.UUID, user_id: uuid.UUID) -> GoalResponse:
    goal = goal_repository.get_goal_for_user(db, goal_id, user_id)
    if goal is None:
        raise NotFoundError("Goal not found")
    return _to_response(goal)


def list_goals(
    db: Session,
    user_id: uuid.UUID,
    *,
    status: str | None = None,
    goal_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> GoalListResponse:
    offset = (page - 1) * page_size
    goals, total = goal_repository.list_goals_for_user(
        db,
        user_id,
        status=status,
        goal_type=goal_type,
        offset=offset,
        limit=page_size,
    )
    return GoalListResponse(
        goals=[_to_response(g) for g in goals],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + len(goals)) < total,
    )


def update_goal(
    db: Session,
    goal_id: uuid.UUID,
    user_id: uuid.UUID,
    body: UpdateGoalRequest,
) -> GoalResponse:
    goal = goal_repository.get_goal_for_user(db, goal_id, user_id)
    if goal is None:
        raise NotFoundError("Goal not found")

    fields = body.model_dump(exclude_none=True)

    # Enforce status transition rules.
    if "status" in fields:
        new_status = fields["status"]
        _validate_status_transition(goal.status, new_status)
        # Auto-set completed_at when marking complete.
        if new_status == "completed" and goal.status != "completed":
            from datetime import datetime, timezone

            fields["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

    goal = goal_repository.update_goal(db, goal, **fields)
    return _to_response(goal)


def delete_goal(db: Session, goal_id: uuid.UUID, user_id: uuid.UUID) -> None:
    goal = goal_repository.get_goal_for_user(db, goal_id, user_id)
    if goal is None:
        raise NotFoundError("Goal not found")
    goal_repository.delete_goal(db, goal)


# ── Status transitions ────────────────────────────────────────────────────────

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "active": {"completed", "paused", "cancelled"},
    "paused": {"active", "cancelled"},
    "completed": set(),  # terminal
    "cancelled": set(),  # terminal
}


def _validate_status_transition(current: str, new: str) -> None:
    if new == current:
        return
    allowed = _ALLOWED_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise ValidationError(
            f"Cannot transition goal from '{current}' to '{new}'. "
            f"Allowed transitions: {sorted(allowed) or 'none (terminal state)'}."
        )
