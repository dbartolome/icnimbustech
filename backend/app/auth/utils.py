"""
Utilidades de autenticación: JWT y hashing de contraseñas.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt

from app.config import configuracion


# =============================================================================
# Contraseñas
# =============================================================================

def hashear_contrasena(contrasena: str) -> str:
    sal = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(contrasena.encode(), sal).decode()


def verificar_contrasena(contrasena_plana: str, hash_almacenado: str) -> bool:
    return bcrypt.checkpw(contrasena_plana.encode(), hash_almacenado.encode())


# =============================================================================
# JWT
# =============================================================================

def crear_access_token(sub: str, rol: str, email: str) -> str:
    """Genera un access token con expiración de 15 minutos."""
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub":   sub,
        "rol":   rol,
        "email": email,
        "iat":   ahora,
        "exp":   ahora + timedelta(minutes=configuracion.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type":  "access",
    }
    return jwt.encode(payload, configuracion.SECRET_KEY, algorithm=configuracion.ALGORITHM)


def crear_refresh_token(sub: str) -> tuple[str, str]:
    """
    Genera un refresh token con expiración de 7 días.
    Devuelve (token, jti) — el jti se guarda en Redis para invalidación.
    """
    ahora = datetime.now(timezone.utc)
    jti = str(uuid4())
    payload = {
        "sub":  sub,
        "jti":  jti,
        "iat":  ahora,
        "exp":  ahora + timedelta(days=configuracion.REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
    }
    token = jwt.encode(payload, configuracion.SECRET_KEY, algorithm=configuracion.ALGORITHM)
    return token, jti


def decodificar_token(token: str) -> dict:
    """
    Decodifica y valida un JWT.
    Lanza JWTError si el token es inválido o ha expirado.
    """
    return jwt.decode(token, configuracion.SECRET_KEY, algorithms=[configuracion.ALGORITHM])
