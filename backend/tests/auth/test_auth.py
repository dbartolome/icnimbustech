"""
Tests del módulo de autenticación.
Cubre login, refresh, logout y protección de rutas.
"""

import pytest
import os

TEST_ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@sgs-dev.com")
TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin_change_me")


@pytest.mark.integracion
class TestLogin:
    def test_login_credenciales_correctas(self, cliente):
        respuesta = cliente.post(
            "/auth/login",
            json={"email": TEST_ADMIN_EMAIL, "contrasena": TEST_ADMIN_PASSWORD},
        )
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert "access_token" in datos
        assert datos["tipo_token"] == "bearer"
        assert len(datos["access_token"]) > 50

    def test_login_contrasena_incorrecta(self, cliente):
        respuesta = cliente.post(
            "/auth/login",
            json={"email": TEST_ADMIN_EMAIL, "contrasena": "incorrecta"},
        )
        assert respuesta.status_code in (204, 401)

    def test_login_email_inexistente(self, cliente):
        respuesta = cliente.post(
            "/auth/login",
            json={"email": "noexiste@sgs.com", "contrasena": "cualquiera"},
        )
        assert respuesta.status_code in (204, 401)

    def test_login_email_invalido(self, cliente):
        respuesta = cliente.post(
            "/auth/login",
            json={"email": "no-es-un-email", "contrasena": TEST_ADMIN_PASSWORD},
        )
        assert respuesta.status_code == 422

    @pytest.mark.parametrize("campo,valor", [
        ("email", ""),
        ("contrasena", ""),
    ])
    def test_login_campos_vacios(self, cliente, campo, valor):
        payload = {"email": TEST_ADMIN_EMAIL, "contrasena": TEST_ADMIN_PASSWORD}
        payload[campo] = valor
        respuesta = cliente.post("/auth/login", json=payload)
        assert respuesta.status_code in (401, 422)


@pytest.mark.integracion
class TestPerfil:
    def test_perfil_con_token_valido(self, cliente, headers_admin):
        respuesta = cliente.get("/auth/me", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["email"] == TEST_ADMIN_EMAIL
        assert datos["rol"] == "admin"
        assert "usuario_id" in datos

    def test_perfil_sin_token(self, cliente):
        respuesta = cliente.get("/auth/me")
        assert respuesta.status_code in (204, 401)

    def test_perfil_token_invalido(self, cliente):
        respuesta = cliente.get(
            "/auth/me",
            headers={"Authorization": "Bearer token_falso_inventado"},
        )
        assert respuesta.status_code in (204, 401)


@pytest.mark.integracion
class TestLogout:
    def test_logout_con_token(self, cliente, headers_admin):
        respuesta = cliente.post("/auth/logout", headers=headers_admin)
        assert respuesta.status_code in (200, 204)

    def test_logout_sin_token(self, cliente):
        respuesta = cliente.post("/auth/logout")
        assert respuesta.status_code in (204, 401)
