"""AIUsageLog ORM model.

Records every call made to an external AI provider.  This allows:
  - Auditing what AI generated on behalf of each user.
  - Estimating costs.
  - Replaying or diffing prompt versions.
  - Respecting user opt-out of AI features.

Design notes:
  - input_tokens / output_tokens are best-effort; set to None if the
    provider does not return usage data.
  - cost_usd is an estimate based on publicly listed prices at call time.
  - accepted is None until the user explicitly accepts or rejects the result.
  - prompt_version is a short string (e.g. "weekly_v1") that maps to a
    specific prompt template in the codebase.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AIUsageLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_usage_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Which feature triggered the call
    feature: Mapped[str] = mapped_column(String(64), nullable=False)

    # Provider / model details
    provider: Mapped[str] = mapped_column(String(64), nullable=False)   # "anthropic"|"openai"
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)

    # Token usage (best-effort)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Outcome
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # User decision (None = pending, True = accepted, False = dismissed)
    accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Stored response (raw JSON string) for audit / replay
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_ai_usage_logs_user_id", "user_id"),
        Index("ix_ai_usage_logs_feature", "feature"),
    )

    def __repr__(self) -> str:
        return (
            f"<AIUsageLog id={self.id} user_id={self.user_id} "
            f"feature={self.feature!r} provider={self.provider!r}>"
        )
