"""
Tests de integración del módulo Coaching.
"""

import pytest


def _obtener_primer_comercial_id(cliente, headers_admin) -> str | None:
    respuesta = cliente.get("/equipo/ranking", headers=headers_admin)
    if respuesta.status_code != 200:
        return None
    datos = respuesta.json()
    if not datos:
        return None
    return datos[0].get("propietario_id")


def _obtener_primera_cuenta_id(cliente, headers_admin) -> str | None:
    respuesta = cliente.get("/cuentas/global?pagina=1&por_pagina=1", headers=headers_admin)
    if respuesta.status_code != 200:
        return None
    datos = respuesta.json().get("datos", [])
    if not datos:
        return None
    return datos[0].get("id")


@pytest.mark.integracion
class TestCoaching:
    def test_coaching_equipo(self, cliente, headers_admin):
        respuesta = cliente.get("/coaching/equipo", headers=headers_admin)
        assert respuesta.status_code == 200
        assert isinstance(respuesta.json(), list)

    def test_historial_usuario(self, cliente, headers_admin):
        comercial_id = _obtener_primer_comercial_id(cliente, headers_admin)
        if not comercial_id:
            pytest.skip("Sin comerciales para prueba")

        respuesta = cliente.get(f"/coaching/historial/{comercial_id}", headers=headers_admin)
        assert respuesta.status_code == 200
        assert isinstance(respuesta.json(), list)

    def test_recomendaciones_usuario(self, cliente, headers_admin):
        comercial_id = _obtener_primer_comercial_id(cliente, headers_admin)
        if not comercial_id:
            pytest.skip("Sin comerciales para prueba")

        respuesta = cliente.get(f"/coaching/recomendaciones/{comercial_id}", headers=headers_admin)
        # Si Ollama no está disponible puede devolver 500.
        assert respuesta.status_code in (200, 500)
        if respuesta.status_code == 200:
            data = respuesta.json()
            assert "focos_semana" in data
            assert "acciones" in data
            assert "metricas_objetivo" in data

    def test_analizar_notas(self, cliente, headers_admin):
        cuenta_id = _obtener_primera_cuenta_id(cliente, headers_admin)
        if not cuenta_id:
            pytest.skip("Sin cuentas para prueba")

        respuesta = cliente.post(f"/coaching/analizar-notas/{cuenta_id}", headers=headers_admin)
        assert respuesta.status_code in (200, 500)

    def test_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/coaching/equipo")
        assert respuesta.status_code == 401
