"""
Tests del módulo Mi Perfil.
Verifica obtención, actualización de datos, estadísticas y objetivos.
"""

import pytest
import os

TEST_ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@sgs-dev.com")


@pytest.mark.integracion
class TestObtenerPerfil:
    def test_perfil_retorna_datos(self, cliente, headers_admin):
        respuesta = cliente.get("/perfil/me", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        for campo in ["usuario_id", "email", "nombre_completo", "rol"]:
            assert campo in datos, f"Campo faltante: {campo}"

    def test_perfil_email_correcto(self, cliente, headers_admin):
        datos = cliente.get("/perfil/me", headers=headers_admin).json()
        assert datos["email"] == TEST_ADMIN_EMAIL

    def test_perfil_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/perfil/me")
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestActualizarPerfil:
    def test_actualizar_telefono(self, cliente, headers_admin):
        respuesta = cliente.put(
            "/perfil/me",
            json={"telefono": "+34 600 000 001"},
            headers=headers_admin,
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["telefono"] == "+34 600 000 001"

    def test_actualizar_zona(self, cliente, headers_admin):
        respuesta = cliente.put(
            "/perfil/me",
            json={"zona": "Madrid Norte"},
            headers=headers_admin,
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["zona"] == "Madrid Norte"

    def test_actualizar_requiere_autenticacion(self, cliente):
        respuesta = cliente.put("/perfil/me", json={"telefono": "123"})
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestEstadisticasPerfil:
    def test_stats_retorna_estructura(self, cliente, headers_admin):
        respuesta = cliente.get("/perfil/me/stats", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        for campo in ["pipeline_activo", "win_rate", "oportunidades_abiertas"]:
            assert campo in datos, f"Campo faltante: {campo}"

    def test_stats_win_rate_en_rango(self, cliente, headers_admin):
        datos = cliente.get("/perfil/me/stats", headers=headers_admin).json()
        wr = float(datos["win_rate"])
        assert 0 <= wr <= 100

    def test_stats_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/perfil/me/stats")
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestObjetivos:
    def test_listar_objetivos(self, cliente, headers_admin):
        respuesta = cliente.get("/perfil/me/objetivos", headers=headers_admin)
        assert respuesta.status_code == 200
        assert isinstance(respuesta.json(), list)

    def test_crear_objetivo(self, cliente, headers_admin):
        payload = {
            "nombre": "Objetivo Test",
            "valor_meta": 100000,
            "valor_actual": 0,
            "unidad": "EUR",   # enum: EUR | PCT | OPS | CUENTAS
            "periodo": "2026-Q1",
        }
        respuesta = cliente.post("/perfil/me/objetivos", json=payload, headers=headers_admin)
        assert respuesta.status_code == 201
        datos = respuesta.json()
        assert datos["nombre"] == "Objetivo Test"
        assert "id" in datos
        # Limpieza
        cliente.delete(f"/perfil/me/objetivos/{datos['id']}", headers=headers_admin)

    def test_crear_objetivo_requiere_autenticacion(self, cliente):
        respuesta = cliente.post("/perfil/me/objetivos", json={"nombre": "Test"})
        assert respuesta.status_code == 401
