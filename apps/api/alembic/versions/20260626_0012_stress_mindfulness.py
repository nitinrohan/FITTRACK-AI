"""Add stress_logs, mindfulness_sessions, mindfulness_logs tables.

Revision ID: 20260626_0012
Revises: 20260623_0011
Create Date: 2026-06-26

Stress & Mindfulness feature. Adds:
  - stress_logs: point-in-time 0-100 stress readings (multiple per day).
  - mindfulness_sessions: curated session library (system rows seeded here)
    plus optional user-created custom sessions.
  - mindfulness_logs: logged mindful minutes, optionally tied to a session.

Seeds a small set of system mindfulness sessions (user_id NULL, is_system
True). external_url is left empty; real links can be filled in later.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260626_0012"
down_revision = "20260623_0011"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    # ── stress_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "stress_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("level", sa.Integer, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("note", sa.Text, nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_stress_logs_user_id", "stress_logs", ["user_id"])
    op.create_index(
        "ix_stress_logs_user_id_recorded_at",
        "stress_logs",
        ["user_id", "recorded_at"],
    )

    # ── mindfulness_sessions ───────────────────────────────────────────────────
    sessions = op.create_table(
        "mindfulness_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "category", sa.String(length=20), nullable=False, server_default="meditation"
        ),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("external_url", sa.String(length=500), nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        *_timestamps(),
    )
    op.create_index(
        "ix_mindfulness_sessions_user_id", "mindfulness_sessions", ["user_id"]
    )

    # ── mindfulness_logs ───────────────────────────────────────────────────────
    op.create_table(
        "mindfulness_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mindfulness_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("recorded_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_mindfulness_logs_user_id", "mindfulness_logs", ["user_id"])
    op.create_index(
        "ix_mindfulness_logs_user_id_recorded_at",
        "mindfulness_logs",
        ["user_id", "recorded_at"],
    )

    # ── Seed system sessions ───────────────────────────────────────────────────
    seed = [
        ("Box breathing", "breathing", 5,
         "Inhale, hold, exhale and hold for equal counts to steady the nervous system."),
        ("4-7-8 breathing", "breathing", 4,
         "A slow breathing pattern that can help you wind down before rest."),
        ("Body scan", "meditation", 10,
         "Move attention gently through the body, noticing sensation without judgement."),
        ("Five-minute reset", "meditation", 5,
         "A short, guided pause to come back to the present moment."),
        ("Focus primer", "focus", 8,
         "Settle attention before deep work or training."),
        ("Gratitude reflection", "meditation", 6,
         "Bring to mind a few things you appreciate today."),
        ("Wind-down for sleep", "sleep", 12,
         "A calming sequence to ease into sleep."),
        ("Calm before training", "focus", 5,
         "A brief centring practice before a workout."),
    ]
    op.bulk_insert(
        sessions,
        [
            {
                "id": uuid.uuid4(),
                "user_id": None,
                "title": title,
                "category": category,
                "duration_minutes": minutes,
                "description": description,
                "external_url": None,
                "is_system": True,
                "is_active": True,
            }
            for (title, category, minutes, description) in seed
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_mindfulness_logs_user_id_recorded_at", table_name="mindfulness_logs")
    op.drop_index("ix_mindfulness_logs_user_id", table_name="mindfulness_logs")
    op.drop_table("mindfulness_logs")

    op.drop_index("ix_mindfulness_sessions_user_id", table_name="mindfulness_sessions")
    op.drop_table("mindfulness_sessions")

    op.drop_index("ix_stress_logs_user_id_recorded_at", table_name="stress_logs")
    op.drop_index("ix_stress_logs_user_id", table_name="stress_logs")
    op.drop_table("stress_logs")
