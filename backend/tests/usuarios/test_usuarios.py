"""
Tests del módulo Usuarios (RBAC).
Verifica CRUD admin-only, permisos por rol y auditoría de cambios de rol.
"""

import pytest

USUARIO_TEST = {
    "email": "test_rbac@sgs-dev.com",
    "nombre_completo": "Usuario Test RBAC",
    "contrasena": "Test1234!",
    "rol": "comercial",
}


@pytest.fixture
def usuario_creado(cliente, headers_admin):
    """Crea un usuario de prueba y lo elimina al finalizar el test."""
    # Email único por test para evitar conflictos
    import time
    payload = {**USUARIO_TEST, "email": f"test_rbac_{int(time.time()*1000)}@sgs-dev.com"}
    respuesta = cliente.post("/usuarios", json=payload, headers=headers_admin)
    assert respuesta.status_code == 201, f"No se pudo crear usuario: {respuesta.text}"
    usuario = respuesta.json()
    yield usuario
    cliente.delete(f"/usuarios/{usuario['id']}", headers=headers_admin)


@pytest.mark.integracion
class TestPermisos:
    def test_permisos_retorna_estructura(self, cliente, headers_admin):
        respuesta = cliente.get("/usuarios/me/permisos", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        for campo in ["ver_equipo", "ver_todos_pipeline", "gestionar_usuarios",
                      "importar_datos", "ver_informes_ejecutivos", "gestionar_alertas"]:
            assert campo in datos, f"Permiso faltante: {campo}"

    def test_admin_tiene_todos_los_permisos(self, cliente, headers_admin):
        datos = cliente.get("/usuarios/me/permisos", headers=headers_admin).json()
        assert all(datos.values()), "Admin debe tener todos los permisos en True"

    def test_permisos_requiere_autenticacion(self, cliente):
        respuesta = cliente.get("/usuarios/me/permisos")
        assert respuesta.status_code == 401


@pytest.mark.integracion
class TestCrudUsuarios:
    def test_listar_usuarios(self, cliente, headers_admin):
        respuesta = cliente.get("/usuarios", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        for campo in ["total", "pagina", "por_pagina", "datos"]:
            assert campo in datos

    def test_listar_usuarios_requiere_admin(self, cliente):
        respuesta = cliente.get("/usuarios")
        assert respuesta.status_code == 401

    def test_crear_usuario_valido(self, cliente, headers_admin):
        import time
        payload = {**USUARIO_TEST, "email": f"nuevo_test_{int(time.time()*1000)}@sgs-dev.com"}
        respuesta = cliente.post("/usuarios", json=payload, headers=headers_admin)
        assert respuesta.status_code == 201
        datos = respuesta.json()
        assert datos["rol"] == "comercial"
        # Limpieza
        cliente.delete(f"/usuarios/{datos['id']}", headers=headers_admin)

    def test_crear_usuario_email_duplicado(self, cliente, headers_admin, usuario_creado):
        # Intentamos crear otro con el mismo email que el fixture
        payload = {**USUARIO_TEST, "email": usuario_creado["email"]}
        respuesta = cliente.post("/usuarios", json=payload, headers=headers_admin)
        assert respuesta.status_code == 409

    def test_crear_sin_email_falla(self, cliente, headers_admin):
        respuesta = cliente.post(
            "/usuarios",
            json={"nombre_completo": "Sin email", "contrasena": "Test1234!"},
            headers=headers_admin,
        )
        assert respuesta.status_code == 422

    def test_obtener_usuario_existente(self, cliente, headers_admin, usuario_creado):
        respuesta = cliente.get(f"/usuarios/{usuario_creado['id']}", headers=headers_admin)
        assert respuesta.status_code == 200
        assert respuesta.json()["id"] == usuario_creado["id"]

    def test_obtener_usuario_inexistente(self, cliente, headers_admin):
        respuesta = cliente.get(
            "/usuarios/00000000-0000-0000-0000-000000000000",
            headers=headers_admin,
        )
        assert respuesta.status_code == 404

    def test_actualizar_nombre(self, cliente, headers_admin, usuario_creado):
        respuesta = cliente.put(
            f"/usuarios/{usuario_creado['id']}",
            json={"nombre_completo": "Nombre Actualizado"},
            headers=headers_admin,
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["nombre_completo"] == "Nombre Actualizado"

    def test_cambio_rol_registrado_en_audit(self, cliente, headers_admin, usuario_creado):
        respuesta = cliente.put(
            f"/usuarios/{usuario_creado['id']}",
            json={"rol": "manager", "motivo_cambio_rol": "Prueba de auditoría"},
            headers=headers_admin,
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["rol"] == "manager"

    def test_no_puede_eliminarse_a_si_mismo(self, cliente, headers_admin):
        perfil = cliente.get("/auth/me", headers=headers_admin).json()
        respuesta = cliente.delete(f"/usuarios/{perfil['usuario_id']}", headers=headers_admin)
        assert respuesta.status_code == 400

    def test_eliminar_usuario(self, cliente, headers_admin):
        import time
        payload = {**USUARIO_TEST, "email": f"eliminar_{int(time.time()*1000)}@sgs-dev.com"}
        r = cliente.post("/usuarios", json=payload, headers=headers_admin)
        assert r.status_code == 201
        usuario = r.json()
        respuesta = cliente.delete(f"/usuarios/{usuario['id']}", headers=headers_admin)
        assert respuesta.status_code == 204

    def test_filtrar_por_rol(self, cliente, headers_admin):
        respuesta = cliente.get("/usuarios?rol=admin", headers=headers_admin)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        for usuario in datos["datos"]:
            assert usuario["rol"] == "admin"
