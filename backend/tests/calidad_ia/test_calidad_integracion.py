"""
Tests de integración del módulo Calidad IA.
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
class TestCalidadIa:
    def test_validar_pdf(self, cliente, headers_admin):
        cuenta_id = _obtener_primera_cuenta_id(cliente, headers_admin)
        if not cuenta_id:
            pytest.skip("Sin cuentas disponibles para prueba")

        respuesta = cliente.get(f"/calidad/validar/{cuenta_id}?tipo=pdf", headers=headers_admin)
        assert respuesta.status_code == 200
        data = respuesta.json()
        for campo in ["cuenta_id", "tipo_entregable", "valido", "nivel", "checks"]:
            assert campo in data, f"Campo faltante: {campo}"
        assert data["nivel"] in ("ok", "warning", "error")
        assert isinstance(data["checks"], list)

    def test_historial_validaciones(self, cliente, headers_admin):
        cuenta_id = _obtener_primera_cuenta_id(cliente, headers_admin)
        if not cuenta_id:
            pytest.skip("Sin cuentas disponibles para prueba")

        respuesta = cliente.get(f"/calidad/historial/{cuenta_id}", headers=headers_admin)
        assert respuesta.status_code == 200
        assert isinstance(respuesta.json(), list)

    def test_forzar_exportacion(self, cliente, headers_admin):
        cuenta_id = _obtener_primera_cuenta_id(cliente, headers_admin)
        if not cuenta_id:
            pytest.skip("Sin cuentas disponibles para prueba")

        respuesta = cliente.post(
            f"/calidad/forzar/{cuenta_id}",
            headers=headers_admin,
            json={"tipo_entregable": "pdf", "motivo": "Test integración"},
        )
        assert respuesta.status_code == 200
        data = respuesta.json()
        assert data["forzado"] is True
        assert data["nivel"] == "warning"

    def test_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/calidad/validar/00000000-0000-0000-0000-000000000000?tipo=pdf")
        assert respuesta.status_code == 401
