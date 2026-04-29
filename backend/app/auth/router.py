"""
Endpoints de autenticación: login, refresh, logout y perfil.
"""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from jose import JWTError
from pydantic import BaseModel, EmailStr

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.auth.utils import (
    crear_access_token,
    crear_refresh_token,
    decodificar_token,
    verificar_contrasena,
)
from app.config import configuracion
from app.database import obtener_conexion
from app.modules.usuarios.servicio import calcular_permisos, _sbus_del_usuario

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_REFRESH = "refresh_token"
_COOKIE_OPCIONES = {
    "httponly": True,
    "samesite": "lax",
    "secure": configuracion.ENVIRONMENT == "production",
    "max_age": configuracion.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
}


# =============================================================================
# Schemas
# =============================================================================

class CredencialesLogin(BaseModel):
    email: EmailStr
    contrasena: str


class RespuestaToken(BaseModel):
    access_token: str
    tipo_token: str = "bearer"


class RespuestaPerfil(BaseModel):
    usuario_id: str
    email: str
    nombre_completo: str
    rol: str
    sbus_asignados: list[str]
    permisos: dict


# =============================================================================
# POST /auth/login
# =============================================================================

@router.post("/login", response_model=RespuestaToken)
async def login(
    credenciales: CredencialesLogin,
    respuesta: Response,
    conexion=Depends(obtener_conexion),
):
    # Mensaje genérico para evitar enumeración de usuarios
    excepcion_generica = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales incorrectas.",
    )

    fila = await conexion.fetchrow(
        "SELECT id, hash_contrasena, rol, email FROM usuarios WHERE email = $1 AND eliminado_en IS NULL",
        credenciales.email,
    )

    if not fila:
        raise excepcion_generica

    if not verificar_contrasena(credenciales.contrasena, fila["hash_contrasena"]):
        raise excepcion_generica

    usuario_id = str(fila["id"])
    access_token = crear_access_token(
        sub=usuario_id,
        rol=fila["rol"],
        email=fila["email"],
    )
    refresh_token, _ = crear_refresh_token(sub=usuario_id)

    respuesta.set_cookie(key=_COOKIE_REFRESH, value=refresh_token, **_COOKIE_OPCIONES)

    return RespuestaToken(access_token=access_token)


# =============================================================================
# POST /auth/refresh
# =============================================================================

@router.post("/refresh", response_model=RespuestaToken)
async def refresh(
    respuesta: Response,
    refresh_token: str | None = Cookie(default=None, alias=_COOKIE_REFRESH),
    conexion=Depends(obtener_conexion),
):
    excepcion = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión expirada. Inicia sesión de nuevo.",
    )

    if not refresh_token:
        raise excepcion

    try:
        payload = decodificar_token(refresh_token)
    except JWTError:
        raise excepcion

    if payload.get("type") != "refresh":
        raise excepcion

    usuario_id = payload.get("sub")
    fila = await conexion.fetchrow(
        "SELECT id, rol, email FROM usuarios WHERE id = $1 AND eliminado_en IS NULL",
        usuario_id,
    )

    if not fila:
        raise excepcion

    # Rotation: nuevo par de tokens
    nuevo_access = crear_access_token(
        sub=str(fila["id"]),
        rol=fila["rol"],
        email=fila["email"],
    )
    nuevo_refresh, _ = crear_refresh_token(sub=str(fila["id"]))

    respuesta.set_cookie(key=_COOKIE_REFRESH, value=nuevo_refresh, **_COOKIE_OPCIONES)

    return RespuestaToken(access_token=nuevo_access)


# =============================================================================
# POST /auth/logout
# =============================================================================

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(respuesta: Response):
    respuesta.delete_cookie(key=_COOKIE_REFRESH)


# =============================================================================
# GET /auth/me
# =============================================================================

@router.get("/me", response_model=RespuestaPerfil)
async def perfil(
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion=Depends(obtener_conexion),
):
    fila = await conexion.fetchrow(
        "SELECT nombre_completo FROM usuarios WHERE id = $1",
        usuario.usuario_id,
    )
    nombre_completo = fila["nombre_completo"] if fila else usuario.email
    sbus = await _sbus_del_usuario(conexion, usuario.usuario_id)
    permisos = calcular_permisos(usuario.rol)

    return RespuestaPerfil(
        usuario_id=usuario.usuario_id,
        email=usuario.email,
        nombre_completo=nombre_completo,
        rol=usuario.rol,
        sbus_asignados=sbus,
        permisos=permisos.model_dump(),
    )
