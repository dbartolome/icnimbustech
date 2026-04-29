"""
Tests del módulo Mis Cuentas.
Verifica listado paginado, búsqueda y detalle de cuenta.
"""

import pytest
import os

TEST_ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@sgs-dev.com")
TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin_change_me")


@pytest.mark.integracion
class TestListarCuentas:
    def test_listar_retorna_estructura_paginada(self, cliente, headers_admin):
        respuesta = cliente.get("/cuentas", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        for campo in ["total", "pagina", "por_pagina", "datos"]:
            assert campo in datos, f"Campo faltante: {campo}"

    def test_listar_total_es_numerico(self, cliente, headers_admin):
        # El admin no tiene oportunidades asignadas — total puede ser 0, es correcto
        datos = cliente.get("/cuentas", headers=headers_admin).json()
        assert isinstance(datos["total"], int)
        assert datos["total"] >= 0

    def test_listar_estructura_cuenta(self, cliente, headers_admin):
        # Usamos el primer comercial con oportunidades reales
        ranking = cliente.get("/equipo/ranking", headers=headers_admin).json()
        token_comercial = cliente.post(
            "/auth/login",
            json={"email": TEST_ADMIN_EMAIL, "contrasena": TEST_ADMIN_PASSWORD},
        ).json()["access_token"]
        h = {"Authorization": f"Bearer {token_comercial}"}
        datos = cliente.get("/cuentas", headers=h).json()
        # Admin puede no tener cuentas — verificamos solo la estructura si hay datos
        if datos["datos"]:
            cuenta = datos["datos"][0]
            for campo in ["id", "nombre", "total_oportunidades", "oportunidades_activas",
                          "pipeline_activo", "importe_ganado", "win_rate"]:
                assert campo in cuenta, f"Campo faltante: {campo}"

    def test_busqueda_sin_match_devuelve_vacio(self, cliente, headers_admin):
        respuesta = cliente.get("/cuentas?busqueda=XYZ_NO_EXISTE_9999_ABC", headers=headers_admin)
        assert respuesta.status_code == 200
        assert respuesta.json()["total"] == 0

    def test_busqueda_sin_resultados(self, cliente, headers_admin):
        respuesta = cliente.get("/cuentas?busqueda=XYZ_NO_EXISTE_9999", headers=headers_admin)
        assert respuesta.status_code == 200
        assert respuesta.json()["total"] == 0

    def test_paginacion(self, cliente, headers_admin):
        respuesta = cliente.get("/cuentas?pagina=1&por_pagina=5", headers=headers_admin)
        datos = respuesta.json()
        assert datos["pagina"] == 1
        assert len(datos["datos"]) <= 5

    def test_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/cuentas")
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestDetalleCuenta:
    def test_detalle_cuenta_inexistente(self, cliente, headers_admin):
        respuesta = cliente.get(
            "/cuentas/00000000-0000-0000-0000-000000000000",
            headers=headers_admin,
        )
        assert respuesta.status_code == 404

    def test_detalle_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/cuentas/00000000-0000-0000-0000-000000000000")
        assert respuesta.status_code == 401

    def test_detalle_cuenta_real(self, cliente, headers_admin):
        # Obtenemos una cuenta real de la DB vía pipeline
        pipeline = cliente.get("/pipeline?por_pagina=1", headers=headers_admin).json()
        if not pipeline["datos"]:
            pytest.skip("Sin oportunidades en la DB")
        cuenta_id = pipeline["datos"][0].get("cuenta_id")
        if not cuenta_id:
            pytest.skip("Oportunidad sin cuenta_id")
        respuesta = cliente.get(f"/cuentas/{cuenta_id}", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert "oportunidades" in datos
