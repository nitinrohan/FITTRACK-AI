"""Goal repository — all DB access for the goals domain.

Ownership is enforced by always filtering on user_id.  No route or service
should ever query goals without supplying the authenticated user's id.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.goal import Goal


def create_goal(
    db: Session,
    user_id: uuid.UUID,
    goal_type: str,
    title: str,
    **fields: object,
) -> Goal:
    """Insert a new goal row.  Returns the saved Goal."""
    goal = Goal(
        id=uuid.uuid4(),
        user_id=user_id,
        goal_type=goal_type,
        title=title,
        **{k: v for k, v in fields.items() if v is not None},
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def get_goal_by_id(db: Session, goal_id: uuid.UUID) -> Goal | None:
    """Return a goal by its primary key (no ownership check — caller must verify)."""
    return db.query(Goal).filter(Goal.id == goal_id).first()


def get_goal_for_user(db: Session, goal_id: uuid.UUID, user_id: uuid.UUID) -> Goal | None:
    """Return a goal only if it belongs to the given user."""
    return db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()


def list_goals_for_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    status: str | None = None,
    goal_type: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Goal], int]:
    """Return (goals, total_count) for the user, with optional filters."""
    query = db.query(Goal).filter(Goal.user_id == user_id)

    if status:
        query = query.filter(Goal.status == status)
    if goal_type:
        query = query.filter(Goal.goal_type == goal_type)

    total = query.count()
    goals = query.order_by(Goal.created_at.desc()).offset(offset).limit(limit).all()
    return goals, total


def update_goal(
    db: Session,
    goal: Goal,
    **fields: object,
) -> Goal:
    """Apply whitelisted field updates to a Goal and commit."""
    allowed = {
        "goal_type",
        "title",
        "description",
        "starting_value",
        "target_value",
        "current_value",
        "target_unit",
        "deadline",
        "status",
        "completed_at",
        "is_public",
    }
    for key, value in fields.items():
        if key in allowed:
            setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, goal: Goal) -> None:
    """Hard-delete a goal row."""
    db.delete(goal)
    db.commit()


def mark_completed(db: Session, goal: Goal) -> Goal:
    """Set status=completed and record completed_at timestamp."""
    goal.status = "completed"
    goal.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(goal)
    return goal
