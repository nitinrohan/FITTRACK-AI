"""Goals router - /api/v1/goals/*

Endpoints:
  POST   /           - Create a new goal.
  GET    /           - List the current user's goals (paginated, filterable).
  GET    /{goal_id}  - Get a single goal.
  PUT    /{goal_id}  - Update a goal (partial - only sent fields change).
  DELETE /{goal_id}  - Delete a goal permanently.

All endpoints require authentication.
Users can only access their own goals (enforced in the service layer).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.goals import (
    CreateGoalRequest,
    GoalListResponse,
    GoalResponse,
    UpdateGoalRequest,
)
from app.services import goal_service

router = APIRouter(prefix="/api/v1/goals", tags=["goals"])


@router.post(
    "",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new goal",
)
def create_goal(
    body: CreateGoalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    return goal_service.create_goal(db, current_user.id, body)


@router.get(
    "",
    response_model=GoalListResponse,
    summary="List goals for the current user",
)
def list_goals(
    status_filter: str | None = Query(default=None, alias="status"),
    goal_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalListResponse:
    return goal_service.list_goals(
        db,
        current_user.id,
        status=status_filter,
        goal_type=goal_type,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{goal_id}",
    response_model=GoalResponse,
    summary="Get a single goal",
)
def get_goal(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    return goal_service.get_goal(db, goal_id, current_user.id)


@router.put(
    "/{goal_id}",
    response_model=GoalResponse,
    summary="Update a goal",
)
def update_goal(
    goal_id: uuid.UUID,
    body: UpdateGoalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    return goal_service.update_goal(db, goal_id, current_user.id, body)


@router.delete(
    "/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a goal",
)
def delete_goal(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    goal_service.delete_goal(db, goal_id, current_user.id)
