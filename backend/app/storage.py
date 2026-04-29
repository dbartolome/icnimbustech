"""
Wrapper de almacenamiento de ficheros sobre MinIO (S3-compatible).

Todas las operaciones de boto3 son síncronas — se ejecutan en threadpool
para no bloquear el event loop de asyncio.
"""

import asyncio
import logging
from functools import partial

import boto3
from botocore.exceptions import ClientError

from app.config import configuracion

logger = logging.getLogger(__name__)

# =============================================================================
# Cliente singleton (se crea una vez al importar)
# =============================================================================

def _crear_cliente():
    return boto3.client(
        "s3",
        endpoint_url=configuracion.MINIO_URL,
        aws_access_key_id=configuracion.MINIO_ACCESS_KEY,
        aws_secret_access_key=configuracion.MINIO_SECRET_KEY,
        region_name="us-east-1",  # MinIO ignora la región pero boto3 la exige
    )


def _asegurar_bucket(client) -> None:
    """Crea el bucket si no existe. Idempotente."""
    try:
        client.head_bucket(Bucket=configuracion.MINIO_BUCKET)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchBucket"):
            client.create_bucket(Bucket=configuracion.MINIO_BUCKET)
            logger.info("Bucket '%s' creado.", configuracion.MINIO_BUCKET)
        else:
            raise


# =============================================================================
# API pública (async)
# =============================================================================

async def subir_fichero(key: str, contenido: bytes, content_type: str) -> str:
    """
    Sube bytes a MinIO con la clave dada.
    Devuelve la misma key para persistir en DB.
    """
    def _subir():
        client = _crear_cliente()
        _asegurar_bucket(client)
        client.put_object(
            Bucket=configuracion.MINIO_BUCKET,
            Key=key,
            Body=contenido,
            ContentType=content_type,
        )
    await asyncio.to_thread(_subir)
    return key


async def obtener_url_descarga(key: str, expires: int = 3600) -> str:
    """
    Genera una URL prefirmada válida `expires` segundos.
    Usa MINIO_PUBLIC_URL como base si está configurada, para que el
    navegador pueda acceder desde fuera de la red Docker.
    """
    def _presign():
        # Para presigned URLs usamos la URL pública si está configurada
        url_publica = configuracion.MINIO_PUBLIC_URL or configuracion.MINIO_URL
        client_publico = boto3.client(
            "s3",
            endpoint_url=url_publica,
            aws_access_key_id=configuracion.MINIO_ACCESS_KEY,
            aws_secret_access_key=configuracion.MINIO_SECRET_KEY,
            region_name="us-east-1",
        )
        return client_publico.generate_presigned_url(
            "get_object",
            Params={"Bucket": configuracion.MINIO_BUCKET, "Key": key},
            ExpiresIn=expires,
        )
    return await asyncio.to_thread(_presign)


async def descargar_fichero(key: str) -> bytes:
    """Descarga un objeto de MinIO y devuelve sus bytes."""
    def _descargar():
        client = _crear_cliente()
        resp = client.get_object(Bucket=configuracion.MINIO_BUCKET, Key=key)
        return resp["Body"].read()
    return await asyncio.to_thread(_descargar)


async def eliminar_fichero(key: str) -> None:
    """Elimina un objeto de MinIO. No lanza si no existe."""
    def _eliminar():
        client = _crear_cliente()
        try:
            client.delete_object(Bucket=configuracion.MINIO_BUCKET, Key=key)
        except ClientError:
            pass  # Si ya no existe, no es un error
    await asyncio.to_thread(_eliminar)
