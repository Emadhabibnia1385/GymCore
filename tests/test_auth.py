"""Auth: bootstrap admin, login, token protection."""


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_wrong_password(client):
    response = client.post(
        "/api/v1/auth/login", json={"phone": "09120000000", "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_and_me(client, admin_headers):
    response = client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "ADMIN"
    assert body["phone"] == "09120000000"


def test_protected_route_requires_token(client):
    client.cookies.clear()  # no leftover auth cookie from earlier logins
    assert client.get("/api/v1/persons").status_code == 401


def test_persian_phone_digits_normalized_on_login(client):
    # Same admin, phone typed with Persian digits.
    response = client.post(
        "/api/v1/auth/login",
        json={"phone": "۰۹۱۲۰۰۰۰۰۰۰", "password": "admin-pass-123"},
    )
    assert response.status_code == 200
    client.cookies.clear()
