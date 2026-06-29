"""Fix ai_usage_logs timestamp columns - add server DEFAULT now().

Migration 0008 created created_at and updated_at as NOT NULL but without
a server-side DEFAULT.  Every INSERT from SQLAlchemy fails with
NotNullViolation because SQLAlchemy relies on the server default to
populate those columns rather than sending them explicitly.

Revision ID: 20260619_0010
Revises: 20260616_0008
Create Date: 2026-06-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260619_0010"
down_revision = "20260618_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add server DEFAULT now() so SQLAlchemy's RETURNING pattern works.
    op.alter_column(
        "ai_usage_logs",
        "created_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "ai_usage_logs",
        "updated_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.alter_column(
        "ai_usage_logs",
        "updated_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=None,
    )
    op.alter_column(
        "ai_usage_logs",
        "created_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=None,
    )
