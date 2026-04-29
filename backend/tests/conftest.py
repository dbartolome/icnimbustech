"""
Fixtures compartidos para todos los tests.

Tests de integración síncronos contra el servidor real (localhost:8000).
Requiere que el backend esté corriendo: uvicorn app.main:app --port 8000
"""

import pytest
import httpx
import os

BASE_URL = "http://localhost:8000"
TEST_ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@sgs-dev.com")
TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin_change_me")


@pytest.fixture
def cliente():
    """Cliente HTTP síncrono — simple y sin problemas de event loop."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="session")
def token_admin():
    """JWT del admin — obtenido una vez por sesión."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        respuesta = c.post(
            "/auth/login",
            json={"email": TEST_ADMIN_EMAIL, "contrasena": TEST_ADMIN_PASSWORD},
        )
        assert respuesta.status_code == 200, f"Login falló: {respuesta.text}"
        return respuesta.json()["access_token"]


@pytest.fixture
def headers_admin(token_admin):
    return {"Authorization": f"Bearer {token_admin}"}
