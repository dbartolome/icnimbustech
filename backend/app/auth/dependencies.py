"""
Dependencias de autenticación y autorización para FastAPI.
"""

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.auth.utils import decodificar_token

esquema_bearer = HTTPBearer(auto_error=False)


class UsuarioAutenticado:
    def __init__(self, usuario_id: str, rol: str, email: str) -> None:
        self.usuario_id = usuario_id
        self.rol = rol
        self.email = email

    @property
    def es_admin(self) -> bool:
        return self.rol == "admin"

    @property
    def es_manager(self) -> bool:
        return self.rol in ("admin", "manager", "supervisor")

    @property
    def es_comercial(self) -> bool:
        return self.rol == "comercial"


async def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
) -> UsuarioAutenticado:
    """
    Extrae y valida el JWT del header Authorization: Bearer <token>.
    Lanza 401 si el token es inválido, expirado o ausente.
    """
    excepcion_no_autorizado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o sesión expirada.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credenciales:
        raise excepcion_no_autorizado

    try:
        payload = decodificar_token(credenciales.credentials)
    except JWTError:
        raise excepcion_no_autorizado

    if payload.get("type") != "access":
        raise excepcion_no_autorizado

    usuario_id = payload.get("sub")
    rol = payload.get("rol")
    email = payload.get("email")

    if not all([usuario_id, rol, email]):
        raise excepcion_no_autorizado

    return UsuarioAutenticado(usuario_id=usuario_id, rol=rol, email=email)


def requerir_rol(*roles_permitidos: str):
    """
    Dependencia de fábrica que restringe el acceso a roles específicos.

    Uso:
        @router.post("/imports/csv")
        async def importar(usuario = Depends(requerir_rol("admin", "manager"))):
            ...
    """
    async def verificar_rol(
        usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    ) -> UsuarioAutenticado:
        if usuario.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acción restringida. Roles permitidos: {', '.join(roles_permitidos)}.",
            )
        return usuario

    return verificar_rol
