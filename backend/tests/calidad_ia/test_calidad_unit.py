import pytest

from app.modules.calidad_ia.servicio import _nivel_desde_checks

pytestmark = pytest.mark.unitario


def test_nivel_desde_checks_error_si_hay_bloqueante():
    checks = [
        {"ok": True, "msg": "ok", "bloquea": False},
        {"ok": False, "msg": "falta propuesta", "bloquea": True},
    ]
    assert _nivel_desde_checks(checks) == "error"


def test_nivel_desde_checks_warning_si_hay_fallos_no_bloqueantes():
    checks = [
        {"ok": True, "msg": "ok", "bloquea": False},
        {"ok": False, "msg": "warning", "bloquea": False},
    ]
    assert _nivel_desde_checks(checks) == "warning"


def test_nivel_desde_checks_ok_si_todo_correcto():
    checks = [
        {"ok": True, "msg": "ok", "bloquea": False},
        {"ok": True, "msg": "ok", "bloquea": False},
    ]
    assert _nivel_desde_checks(checks) == "ok"
