"""Internal API: health/readiness probes, brand status page, webhook auth."""

from fastapi.testclient import TestClient

from app.api.main import app


def test_health_and_status_page():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        ready = client.get("/health/ready")
        assert ready.status_code == 200

        home = client.get("/")
        assert home.status_code == 200
        assert "GymCore" in home.text


def test_webhook_rejects_bad_secret():
    with TestClient(app) as client:
        response = client.post("/webhook/telegram/wrong-secret", json={})
        assert response.status_code == 403


def test_no_public_api_docs():
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
