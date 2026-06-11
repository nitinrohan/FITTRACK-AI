"""Tests for /health and /ready endpoints.

These are unit-level tests: they do not require a real database.
The /ready test mocks check_database_connection so it can verify both
the healthy and degraded paths without a live PostgreSQL instance.
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestHealth:
    """Tests for the /health liveness endpoint."""

    def test_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_response_status_ok(self, client: TestClient) -> None:
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_response_contains_service_name(self, client: TestClient) -> None:
        data = client.get("/health").json()
        assert data["service"] == "fittrack-api"

    def test_response_contains_uptime(self, client: TestClient) -> None:
        data = client.get("/health").json()
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], int | float)
        assert data["uptime_seconds"] >= 0


class TestReady:
    """Tests for the /ready readiness endpoint."""

    def test_returns_200_when_db_ok(self, client: TestClient) -> None:
        with patch("app.routers.health.check_database_connection", return_value=True):
            response = client.get("/ready")
        assert response.status_code == 200

    def test_returns_503_when_db_unavailable(self, client: TestClient) -> None:
        with patch("app.routers.health.check_database_connection", return_value=False):
            response = client.get("/ready")
        assert response.status_code == 503

    def test_response_ok_when_db_ok(self, client: TestClient) -> None:
        with patch("app.routers.health.check_database_connection", return_value=True):
            data = client.get("/ready").json()
        assert data["status"] == "ok"
        assert data["checks"]["database"] == "ok"

    def test_response_degraded_when_db_unavailable(self, client: TestClient) -> None:
        with patch("app.routers.health.check_database_connection", return_value=False):
            data = client.get("/ready").json()
        assert data["status"] == "degraded"
        assert data["checks"]["database"] == "unavailable"


class TestRoot:
    """Tests for the root / endpoint."""

    def test_returns_200(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200

    def test_response_contains_service(self, client: TestClient) -> None:
        data = client.get("/").json()
        assert data["service"] == "fittrack-api"

    def test_response_contains_links(self, client: TestClient) -> None:
        data = client.get("/").json()
        assert "docs" in data
        assert "health" in data
        assert "ready" in data
