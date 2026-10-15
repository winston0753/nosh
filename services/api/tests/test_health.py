"""Health endpoint tests — run without a real database."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


def test_liveness_returns_ok(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_liveness_does_not_require_auth(client):
    """Liveness must work without a Bearer token."""
    resp = client.get("/health/live")
    assert resp.status_code == 200


def test_readiness_ok_when_db_responds(client):
    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)
    mock_conn.execute = AsyncMock()

    with patch("app.main.get_engine") as mock_engine:
        mock_engine.return_value.connect.return_value = mock_conn
        resp = client.get("/health/ready")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_readiness_503_when_db_fails(client):
    with patch("app.main.get_engine") as mock_engine:
        mock_engine.return_value.connect.side_effect = Exception("connection refused")
        resp = client.get("/health/ready")

    assert resp.status_code == 503
