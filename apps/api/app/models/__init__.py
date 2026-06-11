"""SQLAlchemy ORM models.

Import ALL models here so Alembic's autogenerate can detect schema changes.
Add a new import every time a new model file is created.
"""

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.goal import Goal
from app.models.user import User, UserPreference, UserProfile
from app.models.weight_entry import WeightEntry

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "User",
    "UserProfile",
    "UserPreference",
    "Goal",
    "WeightEntry",
]
