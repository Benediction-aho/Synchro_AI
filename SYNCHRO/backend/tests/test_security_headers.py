from fastapi.testclient import TestClient

from synchro.services.api_gateway.main import app

client = TestClient(app)


def test_security_headers_present_on_health():
    response = client.get("/api/v1/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "Content-Security-Policy" in response.headers
    assert response.headers["Permissions-Policy"].startswith("camera=()")


def test_no_hsts_locally():
    response = client.get("/api/v1/health")
    assert "Strict-Transport-Security" not in response.headers


def test_cors_allows_configured_origin():
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_unknown_origin():
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_body_size_limit_returns_413():
    big = b"x" * (2_000_000)
    response = client.post(
        "/api/v1/auth/login",
        content=big,
        headers={"Content-Type": "application/json", "Content-Length": str(len(big))},
    )
    assert response.status_code == 413


def test_production_guard_rejects_default_secret(monkeypatch):
    import pytest
    from synchro.core.config import Settings

    with pytest.raises(ValueError, match="insecure production configuration"):
        Settings(environment="production", debug=False)

    with pytest.raises(ValueError):
        Settings(environment="production", jwt_secret_key="x" * 40)

    safe = Settings(
        environment="production",
        debug=False,
        jwt_secret_key="p" * 48,
        encryption_key="e" * 32,
    )
    assert safe.environment == "production"
