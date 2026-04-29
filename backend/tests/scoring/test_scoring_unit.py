from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.modules.scoring.servicio import _normalizar_factores_jsonb, calcular_score

pytestmark = pytest.mark.unitario


def test_calcular_score_suma_factores_positivos_y_negativos():
    oportunidad = {
        "etapa": "propose",
        "importe": Decimal("120000"),
        "fecha_decision": date.today() + timedelta(days=10),
        "tiene_propuesta": True,
        "tipo": "renovacion",
        "tiene_seguimiento_pendiente": False,
    }

    resultado = calcular_score(oportunidad, Decimal("60000"))

    assert resultado["score"] == 70
    assert resultado["factores"]["etapa"] == 30
    assert resultado["factores"]["importe"] == 20
    assert resultado["factores"]["fecha_decision"] == 15
    assert resultado["factores"]["propuesta_ia"] == 15
    assert resultado["factores"]["tipo"] == 10
    assert resultado["factores"]["sin_seguimiento"] == -20


def test_calcular_score_no_aplica_fecha_pasada():
    oportunidad = {
        "etapa": "discover",
        "importe": Decimal("1000"),
        "fecha_decision": date.today() - timedelta(days=1),
        "tiene_propuesta": False,
        "tipo": "nueva",
        "tiene_seguimiento_pendiente": True,
    }

    resultado = calcular_score(oportunidad, Decimal("9000"))

    assert "fecha_decision" not in resultado["factores"]
    assert resultado["score"] == 0


def test_normalizar_factores_jsonb_desde_dict():
    factores = {"score_anterior": 75, "etapa": 30}
    assert _normalizar_factores_jsonb(factores) == factores


def test_normalizar_factores_jsonb_desde_json_string():
    factores = _normalizar_factores_jsonb('{"score_anterior": 80, "importe": 20}')
    assert factores["score_anterior"] == 80
    assert factores["importe"] == 20


def test_normalizar_factores_jsonb_desde_valor_invalido():
    assert _normalizar_factores_jsonb("no-es-json") == {}
    assert _normalizar_factores_jsonb(None) == {}
