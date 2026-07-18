"""Production-hardening guarantees: readiness probe and security headers."""


def test_liveness_does_not_touch_db(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_reports_db_reachable(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_security_headers_present_on_every_response(client):
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"
    # HSTS must NOT be advertised while running over plain HTTP (dev/tests).
    assert "Strict-Transport-Security" not in response.headers
