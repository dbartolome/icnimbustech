"""
Tests del módulo Notas de Voz.
Verifica creación, listado, búsqueda y eliminación.
"""

import pytest

NOTA_VALIDA = {
    "titulo": "Test nota de voz",
    "transcripcion": "Esta es una nota de prueba generada por el test suite.",
    "duracion_seg": 45,
}


@pytest.mark.integracion
class TestCrearNota:
    def test_crear_nota_valida(self, cliente, headers_admin):
        respuesta = cliente.post("/notas", json=NOTA_VALIDA, headers=headers_admin)
        assert respuesta.status_code == 201
        datos = respuesta.json()
        assert datos["titulo"] == NOTA_VALIDA["titulo"]
        assert datos["transcripcion"] == NOTA_VALIDA["transcripcion"]
        assert "id" in datos

    def test_crear_nota_sin_duracion(self, cliente, headers_admin):
        payload = {"titulo": "Sin duración", "transcripcion": "Texto de prueba"}
        respuesta = cliente.post("/notas", json=payload, headers=headers_admin)
        assert respuesta.status_code == 201

    def test_crear_nota_sin_titulo_falla(self, cliente, headers_admin):
        respuesta = cliente.post(
            "/notas",
            json={"transcripcion": "Texto sin título"},
            headers=headers_admin,
        )
        assert respuesta.status_code == 422

    def test_crear_nota_sin_transcripcion_falla(self, cliente, headers_admin):
        respuesta = cliente.post(
            "/notas",
            json={"titulo": "Título sin texto"},
            headers=headers_admin,
        )
        assert respuesta.status_code == 422

    def test_crear_requiere_autenticacion(self, cliente):
        respuesta = cliente.post("/notas", json=NOTA_VALIDA)
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestListarNotas:
    def test_listar_retorna_estructura_paginada(self, cliente, headers_admin):
        respuesta = cliente.get("/notas", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        for campo in ["total", "pagina", "por_pagina", "datos"]:
            assert campo in datos, f"Campo faltante: {campo}"

    def test_listar_estructura_nota(self, cliente, headers_admin):
        # Creamos una nota para asegurarnos de que hay al menos una
        cliente.post("/notas", json=NOTA_VALIDA, headers=headers_admin)
        datos = cliente.get("/notas", headers=headers_admin).json()
        if datos["datos"]:
            nota = datos["datos"][0]
            for campo in ["id", "titulo", "transcripcion", "creado_en"]:
                assert campo in nota, f"Campo faltante: {campo}"

    def test_busqueda_por_titulo(self, cliente, headers_admin):
        cliente.post("/notas", json={**NOTA_VALIDA, "titulo": "Nota búsqueda única XYZ"}, headers=headers_admin)
        respuesta = cliente.get("/notas?busqueda=búsqueda única XYZ", headers=headers_admin)
        assert respuesta.status_code == 200

    def test_listar_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/notas")
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestEliminarNota:
    def test_eliminar_nota_existente(self, cliente, headers_admin):
        nota_id = cliente.post("/notas", json=NOTA_VALIDA, headers=headers_admin).json()["id"]
        respuesta = cliente.delete(f"/notas/{nota_id}", headers=headers_admin)
        assert respuesta.status_code == 204

    def test_eliminar_nota_inexistente(self, cliente, headers_admin):
        respuesta = cliente.delete(
            "/notas/00000000-0000-0000-0000-000000000000",
            headers=headers_admin,
        )
        assert respuesta.status_code == 404

    def test_eliminar_requiere_autenticacion(self, cliente, headers_admin):
        nota_id = cliente.post("/notas", json=NOTA_VALIDA, headers=headers_admin).json()["id"]
        respuesta = cliente.delete(f"/notas/{nota_id}")
        assert respuesta.status_code == 401
