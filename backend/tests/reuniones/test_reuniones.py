"""
Tests de integración del módulo Reuniones 360.
"""

import pytest


def _obtener_primera_cuenta_id(cliente, headers_admin) -> str | None:
    respuesta = cliente.get("/cuentas/global?pagina=1&por_pagina=1", headers=headers_admin)
    if respuesta.status_code != 200:
        return None
    datos = respuesta.json().get("datos", [])
    if not datos:
        return None
    return datos[0].get("id")


@pytest.mark.integracion
class TestReuniones:
    def test_preparar_ficha_360(self, cliente, headers_admin):
        cuenta_id = _obtener_primera_cuenta_id(cliente, headers_admin)
        if not cuenta_id:
            pytest.skip("Sin cuentas disponibles para prueba")

        respuesta = cliente.get(f"/reuniones/preparar/{cuenta_id}", headers=headers_admin)
        assert respuesta.status_code == 200
        data = respuesta.json()
        for campo in ["cuenta", "investigacion", "propuesta", "pipeline", "seguimientos", "score_medio", "materiales"]:
            assert campo in data, f"Campo faltante: {campo}"

    def test_generar_preguntas(self, cliente, headers_admin):
        cuenta_id = _obtener_primera_cuenta_id(cliente, headers_admin)
        if not cuenta_id:
            pytest.skip("Sin cuentas disponibles para prueba")

        respuesta = cliente.post(f"/reuniones/preguntas/{cuenta_id}", headers=headers_admin)
        # Si falta API key de Anthropic el endpoint responde 503.
        assert respuesta.status_code in (200, 503)
        if respuesta.status_code == 200:
            data = respuesta.json()
            assert "preguntas" in data
            assert isinstance(data["preguntas"], list)

    def test_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/reuniones/preparar/00000000-0000-0000-0000-000000000000")
        assert respuesta.status_code == 401
