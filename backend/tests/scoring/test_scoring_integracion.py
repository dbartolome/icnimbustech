"""
Tests de integración del módulo Scoring.
"""

import pytest


def _obtener_primera_oportunidad_id(cliente, headers_admin) -> str | None:
    respuesta = cliente.get("/pipeline?por_pagina=1", headers=headers_admin)
    if respuesta.status_code != 200:
        return None
    datos = respuesta.json().get("datos", [])
    if not datos:
        return None
    return datos[0].get("id")


@pytest.mark.integracion
class TestScoring:
    def test_recalcular_pipeline(self, cliente, headers_admin):
        respuesta = cliente.post("/scoring/recalcular", headers=headers_admin)
        assert respuesta.status_code == 200
        data = respuesta.json()
        assert "total_oportunidades" in data
        assert "recalculadas" in data

    def test_obtener_score_por_oportunidad(self, cliente, headers_admin):
        oportunidad_id = _obtener_primera_oportunidad_id(cliente, headers_admin)
        if not oportunidad_id:
            pytest.skip("Sin oportunidades para probar scoring")

        respuesta = cliente.get(f"/scoring/{oportunidad_id}", headers=headers_admin)
        assert respuesta.status_code == 200
        data = respuesta.json()
        assert "oportunidad_id" in data
        assert "score" in data
        assert "factores" in data

    def test_listar_criticos(self, cliente, headers_admin):
        respuesta = cliente.get("/scoring/criticos?umbral=40", headers=headers_admin)
        assert respuesta.status_code == 200
        assert isinstance(respuesta.json(), list)

    def test_feedback_score(self, cliente, headers_admin):
        oportunidad_id = _obtener_primera_oportunidad_id(cliente, headers_admin)
        if not oportunidad_id:
            pytest.skip("Sin oportunidades para probar feedback")

        # Asegura que exista score previo
        cliente.get(f"/scoring/{oportunidad_id}", headers=headers_admin)

        respuesta = cliente.post(
            f"/scoring/{oportunidad_id}/feedback",
            headers=headers_admin,
            json={"util": True, "nota": "Ajuste correcto"},
        )
        assert respuesta.status_code == 200
        data = respuesta.json()
        assert "feedback" in data
        assert data["feedback"]["util"] is True

    def test_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/scoring/criticos")
        assert respuesta.status_code == 401
