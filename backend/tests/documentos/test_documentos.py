"""
Tests del módulo Documentos.
Verifica subida, listado, descarga y eliminación con control de acceso.
"""

import io
import pytest

CONTENIDO_PDF = b"%PDF-1.4 contenido de prueba para test suite SGS"
CONTENIDO_TXT = b"Contenido de texto plano para pruebas."


@pytest.mark.integracion
class TestSubirDocumento:
    def test_subir_pdf_valido(self, cliente, headers_admin):
        respuesta = cliente.post(
            "/documentos/subir",
            files={"archivo": ("informe_test.pdf", io.BytesIO(CONTENIDO_PDF), "application/pdf")},
            headers=headers_admin,
        )
        assert respuesta.status_code == 201
        datos = respuesta.json()
        assert "id" in datos
        assert datos["nombre_original"] == "informe_test.pdf"

    def test_subir_txt_valido(self, cliente, headers_admin):
        respuesta = cliente.post(
            "/documentos/subir",
            files={"archivo": ("notas.txt", io.BytesIO(CONTENIDO_TXT), "text/plain")},
            headers=headers_admin,
        )
        assert respuesta.status_code == 201

    def test_subir_ejecutable_rechazado(self, cliente, headers_admin):
        respuesta = cliente.post(
            "/documentos/subir",
            files={"archivo": ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
            headers=headers_admin,
        )
        assert respuesta.status_code in (400, 422)

    def test_subir_requiere_autenticacion(self, cliente):
        respuesta = cliente.post(
            "/documentos/subir",
            files={"archivo": ("test.pdf", io.BytesIO(CONTENIDO_PDF), "application/pdf")},
        )
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestListarDocumentos:
    def test_listar_retorna_estructura_paginada(self, cliente, headers_admin):
        respuesta = cliente.get("/documentos", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        for campo in ["total", "pagina", "por_pagina", "datos"]:
            assert campo in datos, f"Campo faltante: {campo}"

    def test_listar_estructura_documento(self, cliente, headers_admin):
        # Subimos uno para garantizar que hay datos
        cliente.post(
            "/documentos/subir",
            files={"archivo": ("lista_test.pdf", io.BytesIO(CONTENIDO_PDF), "application/pdf")},
            headers=headers_admin,
        )
        datos = cliente.get("/documentos", headers=headers_admin).json()
        if datos["datos"]:
            doc = datos["datos"][0]
            for campo in ["id", "nombre_original", "creado_en"]:
                assert campo in doc, f"Campo faltante: {campo}"

    def test_busqueda_por_nombre(self, cliente, headers_admin):
        cliente.post(
            "/documentos/subir",
            files={"archivo": ("busqueda_unica_xyz.pdf", io.BytesIO(CONTENIDO_PDF), "application/pdf")},
            headers=headers_admin,
        )
        respuesta = cliente.get("/documentos?busqueda=busqueda_unica_xyz", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["total"] >= 1

    def test_listar_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/documentos")
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestEliminarDocumento:
    def test_eliminar_documento_existente(self, cliente, headers_admin):
        doc_id = cliente.post(
            "/documentos/subir",
            files={"archivo": ("eliminar_test.pdf", io.BytesIO(CONTENIDO_PDF), "application/pdf")},
            headers=headers_admin,
        ).json()["id"]

        respuesta = cliente.delete(f"/documentos/{doc_id}", headers=headers_admin)
        assert respuesta.status_code == 204

    def test_eliminar_documento_inexistente(self, cliente, headers_admin):
        respuesta = cliente.delete(
            "/documentos/00000000-0000-0000-0000-000000000000",
            headers=headers_admin,
        )
        assert respuesta.status_code == 404

    def test_eliminar_requiere_autenticacion(self, cliente, headers_admin):
        doc_id = cliente.post(
            "/documentos/subir",
            files={"archivo": ("auth_test.pdf", io.BytesIO(CONTENIDO_PDF), "application/pdf")},
            headers=headers_admin,
        ).json()["id"]

        respuesta = cliente.delete(f"/documentos/{doc_id}")
        assert respuesta.status_code == 401
