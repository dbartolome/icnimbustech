"""
Tests del módulo Productos.
Win rate y análisis por norma/producto.
"""

import pytest


@pytest.mark.integracion
class TestAnalisisProductos:
    def test_analisis_retorna_lista(self, cliente, headers_admin):
        respuesta = cliente.get("/productos/analisis", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert isinstance(datos, list)
        assert len(datos) > 0

    def test_analisis_estructura_correcta(self, cliente, headers_admin):
        respuesta = cliente.get("/productos/analisis", headers=headers_admin)
        datos = respuesta.json()
        campos = ["id", "nombre", "total_oportunidades", "oportunidades_ganadas",
                  "importe_ganado", "ticket_medio", "win_rate"]
        for campo in campos:
            assert campo in datos[0], f"Campo faltante: {campo}"

    def test_win_rate_entre_0_y_100(self, cliente, headers_admin):
        respuesta = cliente.get("/productos/analisis", headers=headers_admin)
        datos = respuesta.json()
        for producto in datos:
            wr = float(producto["win_rate"])
            assert 0 <= wr <= 100, f"Win rate fuera de rango en {producto['nombre']}: {wr}"

    def test_ticket_medio_positivo(self, cliente, headers_admin):
        respuesta = cliente.get("/productos/analisis", headers=headers_admin)
        datos = respuesta.json()
        for producto in datos:
            assert float(producto["ticket_medio"]) >= 0

    def test_analisis_sin_autenticacion(self, cliente):
        respuesta = cliente.get("/productos/analisis")
        assert respuesta.status_code == 401

    def test_ordenado_por_win_rate_descendente(self, cliente, headers_admin):
        respuesta = cliente.get("/productos/analisis", headers=headers_admin)
        datos = respuesta.json()
        win_rates = [float(p["win_rate"]) for p in datos]
        assert win_rates == sorted(win_rates, reverse=True)
