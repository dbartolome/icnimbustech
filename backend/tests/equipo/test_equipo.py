"""
Tests del módulo Equipo.
Verifica ranking, estadísticas individuales y pipeline por comercial.
"""

import pytest


@pytest.mark.integracion
class TestRanking:
    def test_ranking_retorna_lista(self, cliente, headers_admin):
        respuesta = cliente.get("/equipo/ranking", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert isinstance(datos, list)
        assert len(datos) > 0

    def test_ranking_estructura_correcta(self, cliente, headers_admin):
        respuesta = cliente.get("/equipo/ranking", headers=headers_admin)
        datos = respuesta.json()
        campos = ["propietario_id", "nombre_completo", "total_oportunidades",
                  "oportunidades_ganadas", "importe_ganado", "pipeline_abierto", "win_rate"]
        for comercial in datos[:3]:
            for campo in campos:
                assert campo in comercial, f"Campo faltante: {campo}"

    def test_ranking_ordenado_por_importe_desc(self, cliente, headers_admin):
        respuesta = cliente.get("/equipo/ranking", headers=headers_admin)
        datos = respuesta.json()
        importes = [float(c["importe_ganado"]) for c in datos]
        assert importes == sorted(importes, reverse=True)

    def test_ranking_win_rate_en_rango(self, cliente, headers_admin):
        respuesta = cliente.get("/equipo/ranking", headers=headers_admin)
        datos = respuesta.json()
        for comercial in datos:
            wr = float(comercial["win_rate"])
            assert 0 <= wr <= 100, f"Win rate fuera de rango: {wr}"

    def test_ranking_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/equipo/ranking")
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestEstadisticas:
    def test_estadisticas_comercial_valido(self, cliente, headers_admin):
        ranking = cliente.get("/equipo/ranking", headers=headers_admin).json()
        propietario_id = ranking[0]["propietario_id"]
        respuesta = cliente.get(f"/equipo/{propietario_id}/estadisticas", headers=headers_admin)
        assert respuesta.status_code == 200

    def test_estadisticas_estructura_correcta(self, cliente, headers_admin):
        ranking = cliente.get("/equipo/ranking", headers=headers_admin).json()
        propietario_id = ranking[0]["propietario_id"]
        datos = cliente.get(f"/equipo/{propietario_id}/estadisticas", headers=headers_admin).json()
        for campo in ["nombre_completo", "importe_ganado", "win_rate",
                      "total_oportunidades", "oportunidades_ganadas"]:
            assert campo in datos, f"Campo faltante: {campo}"

    def test_estadisticas_id_inexistente(self, cliente, headers_admin):
        respuesta = cliente.get(
            "/equipo/00000000-0000-0000-0000-000000000000/estadisticas",
            headers=headers_admin,
        )
        assert respuesta.status_code in (200, 404)

    def test_estadisticas_requiere_autenticacion(self, cliente, headers_admin):
        ranking = cliente.get("/equipo/ranking", headers=headers_admin).json()
        propietario_id = ranking[0]["propietario_id"]
        respuesta = cliente.get(f"/equipo/{propietario_id}/estadisticas")
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestPipelineComercial:
    def test_pipeline_comercial_retorna_lista(self, cliente, headers_admin):
        ranking = cliente.get("/equipo/ranking", headers=headers_admin).json()
        propietario_id = ranking[0]["propietario_id"]
        respuesta = cliente.get(f"/equipo/{propietario_id}/pipeline", headers=headers_admin)
        assert respuesta.status_code == 200
        assert isinstance(respuesta.json(), list)

    def test_pipeline_comercial_estructura(self, cliente, headers_admin):
        ranking = cliente.get("/equipo/ranking", headers=headers_admin).json()
        propietario_id = ranking[0]["propietario_id"]
        datos = cliente.get(f"/equipo/{propietario_id}/pipeline", headers=headers_admin).json()
        if datos:
            opp = datos[0]
            for campo in ["id", "nombre", "importe", "etapa"]:
                assert campo in opp, f"Campo faltante: {campo}"

    def test_pipeline_requiere_autenticacion(self, cliente, headers_admin):
        ranking = cliente.get("/equipo/ranking", headers=headers_admin).json()
        propietario_id = ranking[0]["propietario_id"]
        respuesta = cliente.get(f"/equipo/{propietario_id}/pipeline")
        assert respuesta.status_code == 401
