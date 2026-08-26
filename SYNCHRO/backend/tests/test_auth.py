REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
ME_URL = "/api/v1/auth/me"

USER = {"email": "trader@example.com", "password": "super-secret-123"}


def register(client, email=USER["email"], password=USER["password"]):
    return client.post(REGISTER_URL, json={"email": email, "password": password})


def test_register_success(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == USER["email"]
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_register_duplicate_email(client):
    register(client)
    response = register(client)
    assert response.status_code == 409


def test_register_short_password(client):
    response = register(client, password="short")
    assert response.status_code == 422


def test_register_invalid_email(client):
    response = register(client, email="not-an-email")
    assert response.status_code == 422


def test_login_success(client):
    register(client)
    response = client.post(LOGIN_URL, json=USER)
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_wrong_password(client):
    register(client)
    response = client.post(LOGIN_URL, json={"email": USER["email"], "password": "wrong-pass-999"})
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post(LOGIN_URL, json=USER)
    assert response.status_code == 401


def test_me_requires_auth(client):
    response = client.get(ME_URL)
    assert response.status_code in (401, 403)


def test_me_with_access_token(client):
    tokens = register(client).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = client.get(ME_URL, headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == USER["email"]


def test_me_rejects_refresh_token_as_access(client):
    tokens = register(client).json()
    headers = {"Authorization": f"Bearer {tokens['refresh_token']}"}
    response = client.get(ME_URL, headers=headers)
    assert response.status_code == 401


def test_refresh_flow(client):
    tokens = register(client).json()
    response = client.post(REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["access_token"]
    headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    me_response = client.get(ME_URL, headers=headers)
    assert me_response.status_code == 200


def test_refresh_rejects_access_token(client):
    tokens = register(client).json()
    response = client.post(REFRESH_URL, json={"refresh_token": tokens["access_token"]})
    assert response.status_code == 401
