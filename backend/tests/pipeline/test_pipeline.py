"""
Tests del módulo Pipeline.
Verifica listado paginado, funnel y control de acceso.
"""

import pytest

ETAPAS_ACTIVAS = [
    "estimation_sent", "technically_approved", "in_progress", "discover",
    "contract_offer_sent", "propose", "estimation_accepted", "negotiate",
]


@pytest.mark.integracion
class TestListadoPipeline:
    def test_listar_retorna_estructura_paginada(self, cliente, headers_admin):
        respuesta = cliente.get("/pipeline", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        for campo in ["total", "pagina", "por_pagina", "datos"]:
            assert campo in datos, f"Campo faltante: {campo}"

    def test_listar_tiene_oportunidades(self, cliente, headers_admin):
        respuesta = cliente.get("/pipeline", headers=headers_admin)
        datos = respuesta.json()
        assert datos["total"] > 0
        assert isinstance(datos["datos"], list)
        assert len(datos["datos"]) > 0

    def test_listar_estructura_oportunidad(self, cliente, headers_admin):
        respuesta = cliente.get("/pipeline", headers=headers_admin)
        opp = respuesta.json()["datos"][0]
        for campo in ["id", "nombre", "importe", "etapa", "fecha_creacion"]:
            assert campo in opp, f"Campo faltante: {campo}"

    def test_paginacion_pagina_2(self, cliente, headers_admin):
        p1 = cliente.get("/pipeline?pagina=1&por_pagina=10", headers=headers_admin).json()
        p2 = cliente.get("/pipeline?pagina=2&por_pagina=10", headers=headers_admin).json()
        assert p1["pagina"] == 1
        assert p2["pagina"] == 2
        # Las oportunidades deben ser distintas entre páginas
        ids_p1 = {o["id"] for o in p1["datos"]}
        ids_p2 = {o["id"] for o in p2["datos"]}
        assert ids_p1.isdisjoint(ids_p2)

    def test_por_pagina_respetado(self, cliente, headers_admin):
        respuesta = cliente.get("/pipeline?por_pagina=5", headers=headers_admin)
        datos = respuesta.json()
        assert len(datos["datos"]) <= 5

    def test_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/pipeline")
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestFunnel:
    def test_funnel_retorna_lista(self, cliente, headers_admin):
        respuesta = cliente.get("/pipeline/funnel", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert isinstance(datos, list)
        assert len(datos) > 0

    def test_funnel_estructura_correcta(self, cliente, headers_admin):
        datos = cliente.get("/pipeline/funnel", headers=headers_admin).json()
        for etapa in datos:
            assert "etapa" in etapa
            assert "num_oportunidades" in etapa
            assert "importe_total" in etapa

    def test_funnel_solo_etapas_activas(self, cliente, headers_admin):
        datos = cliente.get("/pipeline/funnel", headers=headers_admin).json()
        for etapa in datos:
            assert etapa["etapa"] in ETAPAS_ACTIVAS, f"Etapa cerrada en funnel: {etapa['etapa']}"

    def test_funnel_importes_positivos(self, cliente, headers_admin):
        datos = cliente.get("/pipeline/funnel", headers=headers_admin).json()
        for etapa in datos:
            assert float(etapa["importe_total"]) >= 0

    def test_funnel_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/pipeline/funnel")
        assert respuesta.status_code == 401
