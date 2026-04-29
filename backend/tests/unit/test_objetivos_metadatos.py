"""Tests unitarios para normalización de metadatos en objetivos."""

from app.modules.objetivos.servicio import _normalizar_metadatos


def test_normalizar_metadatos_dict():
    valor = {"origen": "ia", "confidence": 0.87}
    assert _normalizar_metadatos(valor) == valor


def test_normalizar_metadatos_json_string_dict():
    valor = '{"origen":"ia","confidence":0.87}'
    assert _normalizar_metadatos(valor) == {"origen": "ia", "confidence": 0.87}


def test_normalizar_metadatos_json_string_no_dict():
    valor = "[1,2,3]"
    assert _normalizar_metadatos(valor) == {}


def test_normalizar_metadatos_texto_invalido():
    valor = "no-es-json"
    assert _normalizar_metadatos(valor) == {}


def test_normalizar_metadatos_none():
    assert _normalizar_metadatos(None) == {}

