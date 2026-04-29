"""
Tests del módulo Importación CSV.
Valida el ETL, manejo de errores y control de acceso.
"""

import io
import pytest


CSV_MINIMO_VALIDO = """Opportunity Name,Strategic Business Unit,Business Line,Product Name,Short Description,Account Name,Canal de Venta,Opportunity Owner,Amount,Created Date,Stage,Decision Date,Type,Opportunity ID
Test Oportunidad,BA,Certification,ISO 9001:2015,Desc,Empresa Test,Directo,Ana María Silva Camayo,5000,2024-01-15,Closed Won,2024-03-01,New Business,TEST-001
Test Pipeline,BA,Certification,ISO 14001:2015,Desc,Empresa B,Indirecto,Rocio Carolina Garcia,3000,2024-02-01,Estimation Sent to Client,,New Business,TEST-002
"""

CSV_ETAPA_DESCONOCIDA = """Opportunity Name,Strategic Business Unit,Business Line,Product Name,Short Description,Account Name,Canal de Venta,Opportunity Owner,Amount,Created Date,Stage,Decision Date,Type,Opportunity ID
Opp Invalida,BA,Cert,ISO 9001:2015,Desc,Empresa,Directo,Ana María Silva Camayo,1000,2024-01-01,Etapa Inexistente XYZ,,New Business,TEST-ERR-001
"""

CSV_SIN_COLUMNAS = """Nombre,Importe
Opp 1,1000
"""


@pytest.mark.integracion
class TestImportacionAcceso:
    def test_importar_requiere_autenticacion(self, cliente):
        csv_bytes = CSV_MINIMO_VALIDO.encode()
        respuesta = cliente.post(
            "/importacion/csv",
            files={"archivo": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
            data={"modo": "upsert"},
        )
        assert respuesta.status_code == 401

    def test_historial_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/importacion/historial")
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestImportacionCsv:
    def test_importar_csv_valido_upsert(self, cliente, headers_admin):
        csv_bytes = CSV_MINIMO_VALIDO.encode()
        respuesta = cliente.post(
            "/importacion/csv",
            files={"archivo": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
            data={"modo": "upsert"},
            headers=headers_admin,
        )
        assert respuesta.status_code == 202
        datos = respuesta.json()
        assert datos["estado"] == "completado"
        assert datos["filas_error"] == 0

    def test_importar_etapa_desconocida_genera_error_de_fila(self, cliente, headers_admin):
        csv_bytes = CSV_ETAPA_DESCONOCIDA.encode()
        respuesta = cliente.post(
            "/importacion/csv",
            files={"archivo": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
            data={"modo": "upsert"},
            headers=headers_admin,
        )
        assert respuesta.status_code == 202
        datos = respuesta.json()
        assert datos["filas_error"] == 1

    def test_importar_sin_columnas_requeridas(self, cliente, headers_admin):
        csv_bytes = CSV_SIN_COLUMNAS.encode()
        respuesta = cliente.post(
            "/importacion/csv",
            files={"archivo": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
            data={"modo": "upsert"},
            headers=headers_admin,
        )
        assert respuesta.status_code == 202
        datos = respuesta.json()
        assert datos["estado"] == "error"

    def test_importar_archivo_no_csv(self, cliente, headers_admin):
        respuesta = cliente.post(
            "/importacion/csv",
            files={"archivo": ("datos.xlsx", io.BytesIO(b"datos"), "application/octet-stream")},
            data={"modo": "upsert"},
            headers=headers_admin,
        )
        assert respuesta.status_code == 422

    @pytest.mark.parametrize("modo", ["append", "upsert"])
    def test_modos_validos(self, cliente, headers_admin, modo):
        csv_bytes = CSV_MINIMO_VALIDO.encode()
        respuesta = cliente.post(
            "/importacion/csv",
            files={"archivo": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
            data={"modo": modo},
            headers=headers_admin,
        )
        assert respuesta.status_code == 202

    def test_modo_invalido(self, cliente, headers_admin):
        csv_bytes = CSV_MINIMO_VALIDO.encode()
        respuesta = cliente.post(
            "/importacion/csv",
            files={"archivo": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
            data={"modo": "borrar_todo"},
            headers=headers_admin,
        )
        assert respuesta.status_code == 422
