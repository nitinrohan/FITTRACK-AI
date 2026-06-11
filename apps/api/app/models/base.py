"""Declarative base and shared mixins for all ORM models.

Design decisions:
- UUID primary keys: globally unique, safe to expose in URLs, avoids
  sequential ID enumeration attacks.
- created_at / updated_at on every table: essential for auditing, data
  export, conflict resolution, and debugging.
- Soft-delete pattern (is_deleted + deleted_at) is available but opt-in.
  Not all entities need it; add the DeleteMixin where appropriate.
- All timestamps stored in UTC without timezone info (assumed UTC).
  Application code must ensure only UTC datetimes are written.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    pass


class TimestampMixin:
    """Adds created_at and updated_at columns to any model.

    created_at is set once at INSERT time by the database server.
    updated_at is maintained by SQLAlchemy on every UPDATE.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key column.

    The default value is generated in Python (not the DB) so that the
    application always has the ID before the INSERT is committed.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
