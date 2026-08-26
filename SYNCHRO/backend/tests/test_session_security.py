REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
CHANGE_URL = "/api/v1/auth/change-password"


def _register(client, email, password="password-123"):
    return client.post(REGISTER_URL, json={"email": email, "password": password})


def test_refresh_replay_revokes_whole_family(client):
    email = "replay@example.com"
    tokens = _register(client, email).json()

    rotated = client.post(REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200
    second_gen = rotated.json()

    replay = client.post(REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    assert "revoked" in replay.json()["detail"]

    dead = client.post(REFRESH_URL, json={"refresh_token": second_gen["refresh_token"]})
    assert dead.status_code == 401


def test_logout_kills_family(client):
    tokens = _register(client, "logout@example.com").json()

    response = client.post(LOGOUT_URL, json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 204

    after = client.post(REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})
    assert after.status_code == 401

    me_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=me_headers).status_code == 200


def test_logout_with_garbage_still_204(client):
    response = client.post(LOGOUT_URL, json={"refresh_token": "not-a-jwt"})
    assert response.status_code == 204


def test_change_password_revokes_old_sessions(client):
    email = "changepw@example.com"
    original_tokens = _register(client, email).json()

    headers = {"Authorization": f"Bearer {original_tokens['access_token']}"}
    changed = client.post(
        CHANGE_URL,
        json={"current_password": "password-123", "new_password": "brand-new-pw-456"},
        headers=headers,
    )
    assert changed.status_code == 200
    new_pair = changed.json()

    old_refresh = client.post(
        REFRESH_URL, json={"refresh_token": original_tokens["refresh_token"]}
    )
    assert old_refresh.status_code == 401

    new_me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_pair['access_token']}"},
    )
    assert new_me.status_code == 200

    relogin_old = client.post(
        LOGIN_URL, json={"email": email, "password": "password-123"}
    )
    assert relogin_old.status_code == 401

    relogin_new = client.post(
        LOGIN_URL, json={"email": email, "password": "brand-new-pw-456"}
    )
    assert relogin_new.status_code == 200


def test_change_password_requires_correct_current(client):
    email = "wrongcurrent@example.com"
    tokens = _register(client, email).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = client.post(
        CHANGE_URL,
        json={"current_password": "totally-wrong", "new_password": "another-pw-789"},
        headers=headers,
    )
    assert response.status_code == 401


def test_lockout_after_repeated_failures_blocks_even_correct_password(client):
    email = "lockout@example.com"
    _register(client, email)

    for _ in range(3):
        client.post(LOGIN_URL, json={"email": email, "password": "bad-guess-1"})
    locked = client.post(LOGIN_URL, json={"email": email, "password": "password-123"})
    assert locked.status_code == 429
    assert "Retry-After" in locked.headers
