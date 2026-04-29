"""
Tests del módulo Informes PDF.
Verifica solicitud, polling de estado, listado y control de acceso.
No espera a que Claude termine — solo verifica estructura y auth.
"""

import pytest

TIPOS_VALIDOS = [
    "ejecutivo_mensual",
    "analisis_comercial",
    "propuesta_cliente",
    "revision_pipeline",
]


@pytest.mark.integracion
class TestGenerarInforme:
    def test_solicitar_informe_valido(self, cliente, headers_admin):
        respuesta = cliente.post(
            "/informes/generar",
            json={"tipo": "ejecutivo_mensual", "periodo": "2025-Q4", "destinatario": "Dirección"},
            headers=headers_admin,
        )
        # 202 = aceptado con API key; 503 = sin API key configurada (entorno dev sin .env)
        assert respuesta.status_code in (202, 503)
        if respuesta.status_code == 202:
            datos = respuesta.json()
            assert "job_id" in datos

    @pytest.mark.parametrize("tipo", TIPOS_VALIDOS)
    def test_tipos_validos_aceptados(self, cliente, headers_admin, tipo):
        respuesta = cliente.post(
            "/informes/generar",
            json={"tipo": tipo},
            headers=headers_admin,
        )
        # El endpoint acepta el tipo — falla en AI solo si no hay API key configurada
        assert respuesta.status_code in (202, 503)

    def test_tipo_invalido_rechazado(self, cliente, headers_admin):
        respuesta = cliente.post(
            "/informes/generar",
            json={"tipo": "informe_inventado"},
            headers=headers_admin,
        )
        assert respuesta.status_code == 422

    def test_generar_sin_tipo_rechazado(self, cliente, headers_admin):
        respuesta = cliente.post("/informes/generar", json={}, headers=headers_admin)
        assert respuesta.status_code == 422

    def test_generar_requiere_autenticacion(self, cliente):
        respuesta = cliente.post(
            "/informes/generar",
            json={"tipo": "ejecutivo_mensual"},
        )
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestEstadoJob:
    def _iniciar_job(self, cliente, headers_admin, tipo="revision_pipeline"):
        """Devuelve job_id si la API key está configurada, sino salta el test."""
        r = cliente.post("/informes/generar", json={"tipo": tipo}, headers=headers_admin)
        if r.status_code == 503:
            pytest.skip("ANTHROPIC_API_KEY no configurada en este entorno")
        assert r.status_code == 202
        return r.json()["job_id"]

    def test_estado_job_existente(self, cliente, headers_admin):
        job_id = self._iniciar_job(cliente, headers_admin)
        respuesta = cliente.get(f"/informes/status/{job_id}", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert "job_id" in datos
        assert "estado" in datos
        assert "progreso" in datos

    def test_estado_progreso_en_rango(self, cliente, headers_admin):
        job_id = self._iniciar_job(cliente, headers_admin, "analisis_comercial")
        datos = cliente.get(f"/informes/status/{job_id}", headers=headers_admin).json()
        assert 0 <= datos["progreso"] <= 100

    def test_estado_job_inexistente(self, cliente, headers_admin):
        respuesta = cliente.get("/informes/status/job-que-no-existe", headers=headers_admin)
        assert respuesta.status_code == 404

    def test_estado_requiere_autenticacion(self, cliente, headers_admin):
        job_id = self._iniciar_job(cliente, headers_admin, "ejecutivo_mensual")
        respuesta = cliente.get(f"/informes/status/{job_id}")
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestListarInformes:
    def test_listar_retorna_lista(self, cliente, headers_admin):
        respuesta = cliente.get("/informes", headers=headers_admin)
        assert respuesta.status_code == 200
        assert isinstance(respuesta.json(), list)

    def test_listar_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/informes")
        assert respuesta.status_code == 401
