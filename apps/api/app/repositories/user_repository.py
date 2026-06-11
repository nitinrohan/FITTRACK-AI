"""User, UserProfile, and UserPreference repository.

All database queries for user-related data are centralised here.
Services call these functions; routes never touch SQLAlchemy directly.

Ownership rule: every function that looks up a user-owned resource
accepts user_id as an explicit argument — there is no global "current user"
singleton. This keeps authorisation explicit and prevents accidental
cross-user data leaks.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session, joinedload

from app.models.user import User, UserPreference, UserProfile


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return the User with the given email, or None if not found."""
    return db.query(User).filter(User.email == email.lower().strip()).first()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    """Return the User with the given id, or None if not found."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_with_relations(db: Session, user_id: uuid.UUID) -> User | None:
    """Return User eagerly loading profile and preferences in a single query."""
    return (
        db.query(User)
        .options(joinedload(User.profile), joinedload(User.preferences))
        .filter(User.id == user_id)
        .first()
    )


def create_user(
    db: Session,
    email: str,
    hashed_password: str,
) -> User:
    """Create a new User with blank Profile and default Preferences.

    All three records are created atomically in the same transaction.
    Returns the User with profile and preferences already populated.
    """
    user = User(
        id=uuid.uuid4(),
        email=email.lower().strip(),
        hashed_password=hashed_password,
    )
    db.add(user)
    db.flush()  # Get the user.id without committing.

    profile = UserProfile(id=uuid.uuid4(), user_id=user.id)
    preferences = UserPreference(id=uuid.uuid4(), user_id=user.id)
    db.add(profile)
    db.add(preferences)
    db.commit()
    db.refresh(user)
    return user


def update_user_profile(
    db: Session,
    user_id: uuid.UUID,
    **fields: object,
) -> UserProfile | None:
    """Update allowed fields on a UserProfile.

    Only whitelisted fields are applied — callers cannot inject arbitrary
    column names via **fields because the repository controls the mapping.
    """
    allowed = {
        "display_name",
        "bio",
        "avatar_url",
        "date_of_birth",
        "height_cm",
        "biological_sex",
        "experience_level",
        "country_code",
        "onboarding_completed",
        "onboarding_step",
    }
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        return None
    for key, value in fields.items():
        if key in allowed:
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


def update_user_preferences(
    db: Session,
    user_id: uuid.UUID,
    **fields: object,
) -> UserPreference | None:
    """Update allowed fields on UserPreferences."""
    allowed = {
        "unit_system",
        "timezone",
        "language",
        "first_day_of_week",
        "email_notifications_enabled",
        "ai_features_enabled",
    }
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not prefs:
        return None
    for key, value in fields.items():
        if key in allowed:
            setattr(prefs, key, value)
    db.commit()
    db.refresh(prefs)
    return prefs


def email_exists(db: Session, email: str) -> bool:
    """Return True if any user is registered with this email."""
    return db.query(User.id).filter(User.email == email.lower().strip()).first() is not None


def deactivate_user(db: Session, user_id: uuid.UUID) -> bool:
    """Soft-deactivate a user account. Returns True if the user was found."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    user.is_active = False
    db.commit()
    return True
