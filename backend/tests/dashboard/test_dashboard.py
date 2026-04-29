"""
Tests del módulo Dashboard.
Verifica KPIs, evolución mensual y breakdown por SBU.
"""

import pytest


@pytest.mark.integracion
class TestKpis:
    def test_kpis_retorna_todos_los_campos(self, cliente, headers_admin):
        respuesta = cliente.get("/dashboard/kpis", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()

        campos_requeridos = [
            "total_oportunidades", "oportunidades_activas", "oportunidades_ganadas",
            "oportunidades_perdidas", "pipeline_total", "pipeline_activo",
            "importe_ganado", "win_rate_global", "ticket_medio_ganado", "calculado_en",
        ]
        for campo in campos_requeridos:
            assert campo in datos, f"Campo faltante: {campo}"

    def test_kpis_valores_coherentes(self, cliente, headers_admin):
        respuesta = cliente.get("/dashboard/kpis", headers=headers_admin)
        datos = respuesta.json()

        assert datos["total_oportunidades"] > 0
        assert datos["oportunidades_activas"] >= 0
        assert datos["win_rate_global"] >= 0
        assert datos["win_rate_global"] <= 100
        assert float(datos["pipeline_total"]) >= float(datos["pipeline_activo"])
        assert float(datos["importe_ganado"]) >= 0

    def test_kpis_sin_autenticacion(self, cliente):
        respuesta = cliente.get("/dashboard/kpis")
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestEvolucion:
    def test_evolucion_retorna_lista(self, cliente, headers_admin):
        respuesta = cliente.get("/dashboard/evolucion", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert isinstance(datos, list)
        assert len(datos) > 0

    def test_evolucion_estructura_correcta(self, cliente, headers_admin):
        respuesta = cliente.get("/dashboard/evolucion", headers=headers_admin)
        datos = respuesta.json()
        for punto in datos[:3]:
            assert "mes" in punto
            assert "total_creadas" in punto
            assert "ganadas" in punto


@pytest.mark.integracion
class TestSbu:
    def test_sbu_retorna_6_unidades(self, cliente, headers_admin):
        respuesta = cliente.get("/dashboard/sbu", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert isinstance(datos, list)
        assert len(datos) == 6

    def test_sbu_estructura_correcta(self, cliente, headers_admin):
        respuesta = cliente.get("/dashboard/sbu", headers=headers_admin)
        datos = respuesta.json()
        for sbu in datos:
            assert "sbu" in sbu
            assert "pipeline_activo" in sbu
            assert "win_rate" in sbu
