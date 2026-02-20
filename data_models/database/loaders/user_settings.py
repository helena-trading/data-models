"""
User Settings Loader - Loads user settings from database
"""

import os
from typing import Any, Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data_models.logging import error, info
from data_models.database.tables.user_settings import UserSettings

# Explicit list of fields that can be updated via save_user_settings
# Excludes: user_id (primary key), created_at, updated_at (managed by DB)
UPDATABLE_SETTINGS_FIELDS = frozenset(
    {
        "run_live_tests_before_start",
        "live_test_efficiency",
        "live_test_exchange",
        "live_test_cancel_maker",
        "live_test_cancel_inverted",
        "live_test_execution",
        "theme",
        "timezone",
        "language",
        "preferences",
    }
)


def load_user_settings(user_id: str = "default") -> Optional[Dict[str, Any]]:
    """
    Load user settings from database

    Args:
        user_id: User identifier (defaults to 'default')

    Returns:
        User settings dictionary or None if not found
    """
    try:
        # Get database URL from environment
        database_url = os.environ.get("DATABASE_URL", "postgresql://helena:helena123@localhost:5432/helena_bot")

        # Create database connection
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as session:
            # Query user settings from database
            settings = session.query(UserSettings).filter_by(user_id=user_id).first()

            if not settings:
                info(f"User settings for {user_id!r} not found, using defaults")
                # Return default settings
                return {
                    "user_id": user_id,
                    "run_live_tests_before_start": False,
                    "live_test_efficiency": True,
                    "live_test_exchange": True,
                    "live_test_cancel_maker": True,
                    "live_test_cancel_inverted": False,
                    "live_test_execution": False,
                    "theme": "dark",
                    "timezone": "UTC",
                    "language": "en",
                    "preferences": {"use_websocket_for_orders": True},  # Default to WebSocket for better performance
                }

            return settings.to_dict()

    except Exception as e:
        error(f"Error loading user settings: {str(e)}")
        # Return default settings on error
        return {
            "user_id": user_id,
            "run_live_tests_before_start": False,
            "live_test_efficiency": True,
            "live_test_exchange": True,
            "live_test_cancel_maker": True,
            "live_test_cancel_inverted": False,
            "live_test_execution": False,
            "theme": "dark",
            "timezone": "UTC",
            "language": "en",
            "preferences": {"use_websocket_for_orders": True},  # Default to WebSocket for better performance
        }


def get_live_test_config(user_id: str = "default") -> Dict[str, Any]:
    """
    Get live testing configuration for a user

    Args:
        user_id: User identifier (defaults to 'default')

    Returns:
        Live testing configuration dictionary
    """
    settings = load_user_settings(user_id)

    if settings:
        return {
            "enabled": settings.get("run_live_tests_before_start", False),
            "efficiency": settings.get("live_test_efficiency", True),
            "exchange": settings.get("live_test_exchange", True),
            "cancel_maker": settings.get("live_test_cancel_maker", True),
            "cancel_inverted": settings.get("live_test_cancel_inverted", False),
            "execution": settings.get("live_test_execution", False),
        }

    # Default configuration if settings not found
    return {
        "enabled": False,
        "efficiency": True,
        "exchange": True,
        "cancel_maker": True,
        "cancel_inverted": False,
        "execution": False,
    }


def save_user_settings(user_id: str, settings: Dict[str, Any]) -> bool:
    """
    Save or update user settings in database

    Args:
        user_id: User identifier
        settings: Settings dictionary to save

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get database URL from environment
        database_url = os.environ.get("DATABASE_URL", "postgresql://helena:helena123@localhost:5432/helena_bot")

        # Create database connection
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as session:
            # Check if settings already exist
            existing = session.query(UserSettings).filter_by(user_id=user_id).first()

            if existing:
                # Update existing settings using explicit allowed fields
                for key, value in settings.items():
                    if key in UPDATABLE_SETTINGS_FIELDS:
                        setattr(existing, key, value)
            else:
                # Create new settings
                new_settings = UserSettings(user_id=user_id, **settings)
                session.add(new_settings)

            session.commit()
            info(f"User settings saved for {user_id!r}")
            return True

    except Exception as e:
        error(f"Error saving user settings: {str(e)}")
        return False
