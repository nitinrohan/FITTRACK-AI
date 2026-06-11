"""Tests for application configuration loading."""

from __future__ import annotations


class TestSettings:
    """Verify that Settings loads and validates environment variables."""

    def test_default_env_is_test(self) -> None:
        # conftest.py sets APP_ENV=test before this runs.
        from app.config import get_settings

        get_settings.cache_clear()
        s = get_settings()
        assert s.app_env == "test"

    def test_is_test_property(self) -> None:
        from app.config import get_settings

        get_settings.cache_clear()
        s = get_settings()
        assert s.is_test is True
        assert s.is_production is False

    def test_ai_disabled_when_provider_none(self) -> None:
        from app.config import Settings

        s = Settings(ai_provider="none")  # type: ignore[call-arg]
        assert s.ai_enabled is False

    def test_ai_disabled_when_anthropic_key_missing(self) -> None:
        from app.config import Settings

        s = Settings(ai_provider="anthropic", anthropic_api_key="")  # type: ignore[call-arg]
        assert s.ai_enabled is False

    def test_ai_enabled_when_anthropic_key_present(self) -> None:
        from app.config import Settings

        s = Settings(  # type: ignore[call-arg]
            ai_provider="anthropic",
            anthropic_api_key="sk-ant-test-key",
        )
        assert s.ai_enabled is True

    def test_cors_origins_parsed_from_json_string(self) -> None:
        from app.config import Settings

        s = Settings(  # type: ignore[call-arg]
            backend_cors_origins='["http://localhost:3000","http://example.com"]',
        )
        assert "http://localhost:3000" in s.backend_cors_origins
        assert "http://example.com" in s.backend_cors_origins

    def test_cors_origins_parsed_from_comma_string(self) -> None:
        from app.config import Settings

        s = Settings(backend_cors_origins="http://localhost:3000,http://example.com")  # type: ignore[call-arg]
        assert "http://localhost:3000" in s.backend_cors_origins
        assert "http://example.com" in s.backend_cors_origins
