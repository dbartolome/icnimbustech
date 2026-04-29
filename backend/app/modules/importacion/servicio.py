"""
ETL para importación de CSV de Salesforce al pipeline de oportunidades.

Columnas del CSV de SGS:
Opportunity Name · Strategic Business Unit · Business Line · Product Name ·
Short Description · Account Name · Canal de Venta · Opportunity Owner ·
Amount · Created Date · Stage · Decision Date · Type · Opportunity ID
"""

import io
import json
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

import asyncpg
import pandas as pd
from app.config import configuracion
from app.modules.ia.proveedores import PROVEEDOR_LOCAL, obtener_configs_operacionales

MAX_PREVIEW_FILAS = 200
MAX_PREVIEW_COLS = 40

# Mapeo de etapas del CSV (Salesforce) a slugs internos
MAPA_ETAPAS: dict[str, str] = {
    "estimation sent to client":          "estimation_sent",
    "estimation ready":                   "estimation_sent",
    "technically approved":               "technically_approved",
    "under technical approval":           "technically_approved",
    "in progress":                        "in_progress",
    "discover":                           "discover",
    "contract offer sent":                "contract_offer_sent",
    "contract offer sent to client":      "contract_offer_sent",
    "contract offer ready":               "contract_offer_sent",
    "contract offer accepted by client":  "estimation_accepted",
    "propose":                            "propose",
    "estimation accepted":                "estimation_accepted",
    "negotiate":                          "negotiate",
    "closed won":                         "closed_won",
    "closed lost":                        "closed_lost",
    "closed withdrawn":                   "closed_withdrawn",
    "client declines estimation":         "closed_lost",
    "propuesta enviada":                  "propose",
    "propuesta enviada al cliente":       "propose",
    "cualificacion":                      "discover",
    "cualificación":                      "discover",
    "qualification":                      "discover",
    "calificacion":                       "discover",
    "calificación":                       "discover",
    "negociacion":                        "negotiate",
    "negociación":                        "negotiate",
    "ganada":                             "closed_won",
    "perdida":                            "closed_lost",
    "pérdida":                            "closed_lost",
    "retirada":                           "closed_withdrawn",
    "contract offer sent to client":      "contract_offer_sent",
    "contract offer ready":               "contract_offer_sent",
    "contract offer accepted by client":  "estimation_accepted",
    "under technical approval":           "technically_approved",
}

# Columnas mínimas para procesar una oportunidad.
# El resto (SBU, producto, owner, canal, etc.) son opcionales.
COLUMNAS_REQUERIDAS = [
    "Opportunity Name",
    "Account Name",
    "Amount",
    "Created Date",
    "Stage",
    "Opportunity ID",
]

# Mapeo tolerante para cabeceras habituales en español/variantes.
ALIAS_COLUMNAS: dict[str, str] = {
    "opportunity_name": "Opportunity Name",
    "nombre_oportunidad": "Opportunity Name",
    "nombre_opportunidad": "Opportunity Name",
    "nombre": "Opportunity Name",
    "opportunity": "Opportunity Name",
    "strategic_business_unit": "Strategic Business Unit",
    "unidad_estrategica": "Strategic Business Unit",
    "sbu": "Strategic Business Unit",
    "business_line": "Business Line",
    "linea_de_negocio": "Business Line",
    "linea_negocio": "Business Line",
    "product_name": "Product Name",
    "producto": "Product Name",
    "short_description": "Short Description",
    "descripcion": "Short Description",
    "account_name": "Account Name",
    "cuenta": "Account Name",
    "canal_de_venta": "Canal de Venta",
    "canal_venta": "Canal de Venta",
    "opportunity_owner": "Opportunity Owner",
    "owner": "Opportunity Owner",
    "comercial": "Opportunity Owner",
    "amount": "Amount",
    "importe": "Amount",
    "created_date": "Created Date",
    "fecha_creacion": "Created Date",
    "stage": "Stage",
    "etapa": "Stage",
    "decision_date": "Decision Date",
    "fecha_decision": "Decision Date",
    "type": "Type",
    "opportunity_id": "Opportunity ID",
    "id_oportunidad": "Opportunity ID",
    "id": "Opportunity ID",
}

# Valores controlados para Business Line (13 líneas oficiales SGS España)
LINEAS_NEGOCIO_VALIDAS: set[str] = {
    "Certification",
    "ESG Solutions",
    "Second Party",
    "Testing",
    "Inspection",
    "Training & Qualification",
    "Product Certification",
    "Customized Assurance",
    "Digital Trust",
    "Healthcare",
    "Food & Retail",
    "Technical Advisory",
    "Government & Sustainability",
}

# Valores controlados para Canal de Venta (4 canales oficiales)
CANALES_VENTA_VALIDOS: set[str] = {
    "Directo",
    "Indirecto",
    "Alliance",
    "Online",
}


def _normalizar_linea_negocio(valor: str) -> str | None:
    """Devuelve el valor normalizado si es válido; si no, None (modo tolerante de importación)."""
    v = str(valor).strip()
    if not v:
        return None
    if v in LINEAS_NEGOCIO_VALIDAS:
        return v
    # Búsqueda case-insensitive
    for valido in LINEAS_NEGOCIO_VALIDAS:
        if valido.lower() == v.lower():
            return valido
    return None


def _normalizar_texto(valor: str) -> str:
    """Normaliza texto para matching tolerante (sin acentos, minúsculas, espacios colapsados)."""
    base = str(valor or "").strip().lower()
    if not base:
        return ""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", base)
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sin_acentos).strip()


_MAPA_ETAPAS_NORMALIZADO: dict[str, str] = {
    _normalizar_texto(clave): valor for clave, valor in MAPA_ETAPAS.items()
}


def _resolver_etapa(valor: str) -> str | None:
    """Resuelve etapa de forma robusta ante variantes en español/inglés."""
    etapa_norm = _normalizar_texto(valor)
    if not etapa_norm:
        return None

    directa = _MAPA_ETAPAS_NORMALIZADO.get(etapa_norm)
    if directa:
        return directa

    # Fallback por patrones comunes de nomenclatura CRM.
    if "cualific" in etapa_norm or "qualif" in etapa_norm:
        return "discover"
    if "propuesta" in etapa_norm or "proposal" in etapa_norm:
        return "propose"
    if "negoci" in etapa_norm:
        return "negotiate"
    if "ganad" in etapa_norm or "won" in etapa_norm:
        return "closed_won"
    if "perdid" in etapa_norm or "lost" in etapa_norm or "declines" in etapa_norm:
        return "closed_lost"
    if "withdraw" in etapa_norm or "retirad" in etapa_norm:
        return "closed_withdrawn"
    return None


def _normalizar_canal_venta(valor: str) -> str | None:
    """Devuelve el canal normalizado si es válido; si no, None (modo tolerante de importación)."""
    v = str(valor).strip()
    if not v:
        return None
    if v in CANALES_VENTA_VALIDOS:
        return v
    for valido in CANALES_VENTA_VALIDOS:
        if valido.lower() == v.lower():
            return valido
    return None


def _limpiar_importe(valor: str) -> Decimal:
    txt = str(valor or "").replace("€", "").replace("\u00a0", " ").strip()
    txt = txt.replace(" ", "")
    if not txt:
        return Decimal("0")
    # Formato europeo (1.234,56) -> 1234.56
    if "," in txt and "." in txt:
        txt = txt.replace(".", "").replace(",", ".")
    # Miles con coma (1,234) -> 1234
    elif "," in txt and "." not in txt and txt.count(",") == 1:
        entera, decimal = txt.split(",", 1)
        if decimal.isdigit() and len(decimal) <= 2:
            txt = f"{entera}.{decimal}"
        else:
            txt = txt.replace(",", "")
    # Limpiar cualquier carácter no numérico restante
    limpio = re.sub(r"[^0-9.\-]", "", txt)
    try:
        resultado = Decimal(limpio)
        return resultado if resultado >= 0 else Decimal("0")
    except InvalidOperation:
        return Decimal("0")


def _parsear_fecha(valor) -> date | None:
    if pd.isna(valor) or str(valor).strip() == "":
        return None
    try:
        dt = pd.to_datetime(valor, errors="coerce", dayfirst=False)
        if pd.isna(dt):
            dt = pd.to_datetime(valor, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            return None
        return dt.date()
    except Exception:
        return None


def _normalizar_clave_columna(nombre: str) -> str:
    """Normaliza cabeceras para mapear variantes (acentos, mayúsculas, separadores)."""
    base = unicodedata.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode("ascii")
    base = base.strip().lower()
    base = re.sub(r"[^a-z0-9]+", "_", base)
    return base.strip("_")


def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    renombres: dict[str, str] = {}
    for col in df.columns:
        clave = _normalizar_clave_columna(col)
        canonica = ALIAS_COLUMNAS.get(clave)
        if canonica:
            renombres[col] = canonica
    return df.rename(columns=renombres)


def _leer_csv_con_fallback(contenido: bytes) -> pd.DataFrame:
    """
    Lee CSV tolerando UTF-8/Latin-1 y delimitadores coma/punto y coma.
    """
    encodings = ("utf-8-sig", "utf-8", "latin-1")
    delimitadores = (None, ",", ";")
    ultimo_error: Exception | None = None
    for enc in encodings:
        for sep in delimitadores:
            try:
                kwargs = {
                    "encoding": enc,
                    "dtype": str,
                    "keep_default_na": False,
                }
                if sep is None:
                    kwargs["sep"] = None
                    kwargs["engine"] = "python"
                else:
                    kwargs["sep"] = sep
                return pd.read_csv(io.BytesIO(contenido), **kwargs)
            except Exception as e:  # pragma: no cover - controlado por fallback
                ultimo_error = e
                continue
    raise ValueError(f"No se pudo leer el CSV con codificaciones/delimitadores soportados: {ultimo_error}") from ultimo_error


def _normalizar_errores(fila_errores) -> list[dict]:
    if fila_errores is None:
        return []
    if isinstance(fila_errores, list):
        return fila_errores
    if isinstance(fila_errores, str):
        try:
            parsed = json.loads(fila_errores)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _construir_preview_df(df: pd.DataFrame) -> tuple[list[str], list[dict]]:
    """Genera una vista previa serializable del CSV para UI/chat contextual."""
    if df.empty:
        return [], []

    columnas = [str(c) for c in list(df.columns)[:MAX_PREVIEW_COLS]]
    vista = df[columnas].head(MAX_PREVIEW_FILAS).fillna("")

    # Garantiza JSON serializable y evita NaN/objetos raros.
    filas: list[dict] = []
    for _, row in vista.iterrows():
        item: dict[str, str] = {}
        for c in columnas:
            valor = row.get(c, "")
            item[c] = "" if pd.isna(valor) else str(valor)
        filas.append(item)
    return columnas, filas


def _normalizar_json_lista(valor) -> list:
    if valor is None:
        return []
    if isinstance(valor, list):
        return valor
    if isinstance(valor, str):
        try:
            parsed = json.loads(valor)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _respuesta_preview_por_tokens(
    pregunta: str,
    preview_cols: list,
    preview_rows: list,
) -> str:
    tokens = [t for t in re.split(r"\s+", (pregunta or "").lower()) if len(t) >= 3]
    if not tokens or not preview_rows:
        return ""

    halladas = 0
    ejemplos: list[str] = []
    for fila in preview_rows:
        texto_fila = " ".join(str(fila.get(c, "")) for c in preview_cols).lower()
        if all(tok in texto_fila for tok in tokens):
            halladas += 1
            if len(ejemplos) < 5:
                pares = []
                for c in preview_cols[:6]:
                    v = str(fila.get(c, "")).strip()
                    if v:
                        pares.append(f"{c}={v}")
                ejemplos.append(" | ".join(pares) if pares else "(sin datos visibles)")

    if halladas == 0:
        return ""
    return (
        f"He encontrado {halladas} filas relacionadas con tu consulta en el CSV seleccionado.\n"
        + "\n".join(f"- {e}" for e in ejemplos)
    )


async def _obtener_o_crear_cuenta(
    conexion: asyncpg.Connection,
    nombre: str,
    cache: dict,
) -> UUID | None:
    if not nombre or str(nombre).strip() == "":
        return None
    nombre = str(nombre).strip()
    if nombre in cache:
        return cache[nombre]
    fila = await conexion.fetchrow("SELECT id FROM cuentas WHERE nombre = $1", nombre)
    if fila:
        cuenta_id = fila["id"]
    else:
        cuenta_id = await conexion.fetchval(
            "INSERT INTO cuentas (nombre) VALUES ($1) RETURNING id", nombre
        )
    cache[nombre] = cuenta_id
    return cuenta_id


async def _obtener_propietario(
    conexion: asyncpg.Connection,
    nombre: str,
    cache: dict,
) -> UUID | None:
    if not nombre or str(nombre).strip() == "":
        return None
    nombre = str(nombre).strip()
    if nombre in cache:
        return cache[nombre]
    fila = await conexion.fetchrow(
        "SELECT id FROM usuarios WHERE nombre_completo ILIKE $1 AND eliminado_en IS NULL",
        f"%{nombre}%",
    )
    propietario_id = fila["id"] if fila else None
    cache[nombre] = propietario_id
    return propietario_id


async def _obtener_sbu(
    conexion: asyncpg.Connection,
    nombre: str,
    cache: dict,
) -> UUID | None:
    if not nombre or str(nombre).strip() == "":
        return None
    nombre = str(nombre).strip()
    if nombre in cache:
        return cache[nombre]
    fila = await conexion.fetchrow(
        "SELECT id FROM sbu WHERE nombre ILIKE $1", f"%{nombre}%"
    )
    sbu_id = fila["id"] if fila else None
    cache[nombre] = sbu_id
    return sbu_id


async def _obtener_producto(
    conexion: asyncpg.Connection,
    nombre: str,
    cache: dict,
) -> UUID | None:
    if not nombre or str(nombre).strip() == "":
        return None
    nombre = str(nombre).strip()
    if nombre in cache:
        return cache[nombre]
    fila = await conexion.fetchrow(
        "SELECT id FROM productos WHERE nombre ILIKE $1", f"%{nombre}%"
    )
    producto_id = fila["id"] if fila else None
    cache[nombre] = producto_id
    return producto_id


async def procesar_csv(
    conexion: asyncpg.Connection,
    importacion_id: UUID,
    contenido: bytes,
    modo: str,
    *,
    forzar_propietario_id: UUID | None = None,
) -> None:
    """
    ETL completo del CSV.
    Actualiza la tabla `importaciones` con el progreso y errores.
    """
    errores: list[dict] = []

    # --- Leer CSV ---
    df = _leer_csv_con_fallback(contenido)
    df = _normalizar_columnas(df)
    preview_columnas, preview_filas = _construir_preview_df(df)
    await conexion.execute(
        """
        UPDATE importaciones
        SET preview_columnas = $1::jsonb,
            preview_filas = $2::jsonb
        WHERE id = $3
        """,
        json.dumps(preview_columnas),
        json.dumps(preview_filas),
        importacion_id,
    )

    # --- Validar columnas requeridas ---
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        await conexion.execute(
            """UPDATE importaciones SET estado='error', errores=$1::jsonb WHERE id=$2""",
            json.dumps([{"fila": 0, "error": f"Columnas faltantes: {faltantes}"}]),
            importacion_id,
        )
        return

    total = len(df)
    await conexion.execute(
        "UPDATE importaciones SET total_filas=$1 WHERE id=$2", total, importacion_id
    )

    # Modo reset: vacía oportunidades antes de importar.
    # - admin/manager: limpia todo el pipeline.
    # - comercial: limpia solo sus oportunidades (scope por propietario).
    if modo == "reset":
        if forzar_propietario_id:
            await conexion.execute(
                "DELETE FROM oportunidades WHERE propietario_id = $1",
                forzar_propietario_id,
            )
        else:
            await conexion.execute("DELETE FROM oportunidades")

    # Caches para evitar N+1 queries
    cache_cuentas: dict = {}
    cache_propietarios: dict = {}
    cache_sbus: dict = {}
    cache_productos: dict = {}

    creadas = 0
    actualizadas = 0

    for idx, fila in df.iterrows():
        num_fila = int(idx) + 2  # +2 por header y base 1

        try:
            external_id = str(fila.get("Opportunity ID", "")).strip()
            if not external_id:
                raise ValueError("Opportunity ID vacío")

            etapa_csv = str(fila.get("Stage", "")).strip()
            etapa = _resolver_etapa(etapa_csv)
            if not etapa:
                raise ValueError(f"Etapa desconocida: '{fila.get('Stage')}'")

            importe = _limpiar_importe(fila.get("Amount", "0"))
            fecha_creacion = _parsear_fecha(fila.get("Created Date"))
            fecha_decision = _parsear_fecha(fila.get("Decision Date"))

            if not fecha_creacion:
                raise ValueError("Created Date inválida o vacía")

            cuenta_id = await _obtener_o_crear_cuenta(
                conexion, fila.get("Account Name", ""), cache_cuentas
            )
            propietario_id = (
                forzar_propietario_id
                if forzar_propietario_id
                else await _obtener_propietario(
                    conexion, fila.get("Opportunity Owner", ""), cache_propietarios
                )
            )
            sbu_id = await _obtener_sbu(
                conexion, fila.get("Strategic Business Unit", ""), cache_sbus
            )
            producto_id = await _obtener_producto(
                conexion, fila.get("Product Name", ""), cache_productos
            )

            if modo == "upsert":
                resultado = await conexion.fetchval("""
                    INSERT INTO oportunidades
                        (external_id, nombre, importe, etapa, fecha_creacion, fecha_decision,
                         linea_negocio, canal_venta, cuenta_id, propietario_id, sbu_id, producto_id)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                    ON CONFLICT (external_id) DO UPDATE SET
                        nombre          = EXCLUDED.nombre,
                        importe         = EXCLUDED.importe,
                        etapa           = EXCLUDED.etapa,
                        fecha_decision  = EXCLUDED.fecha_decision,
                        linea_negocio   = EXCLUDED.linea_negocio,
                        canal_venta     = EXCLUDED.canal_venta,
                        cuenta_id       = EXCLUDED.cuenta_id,
                        propietario_id  = EXCLUDED.propietario_id,
                        sbu_id          = EXCLUDED.sbu_id,
                        producto_id     = EXCLUDED.producto_id,
                        actualizado_en  = NOW()
                    RETURNING (xmax = 0) AS es_nueva
                """,
                    external_id,
                    str(fila.get("Opportunity Name", "")).strip(),
                    importe, etapa, fecha_creacion, fecha_decision,
                    _normalizar_linea_negocio(fila.get("Business Line", "")),
                    _normalizar_canal_venta(fila.get("Canal de Venta", "")),
                    cuenta_id, propietario_id, sbu_id, producto_id,
                )
                if resultado:
                    creadas += 1
                else:
                    actualizadas += 1
            else:
                insertado_id = await conexion.fetchval("""
                    INSERT INTO oportunidades
                        (external_id, nombre, importe, etapa, fecha_creacion, fecha_decision,
                         linea_negocio, canal_venta, cuenta_id, propietario_id, sbu_id, producto_id)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                    ON CONFLICT (external_id) DO NOTHING
                    RETURNING id
                """,
                    external_id,
                    str(fila.get("Opportunity Name", "")).strip(),
                    importe, etapa, fecha_creacion, fecha_decision,
                    _normalizar_linea_negocio(fila.get("Business Line", "")),
                    _normalizar_canal_venta(fila.get("Canal de Venta", "")),
                    cuenta_id, propietario_id, sbu_id, producto_id,
                )
                if insertado_id:
                    creadas += 1

        except Exception as e:
            errores.append({"fila": num_fila, "error": str(e)})

        # Actualizar progreso cada 100 filas
        if (int(idx) + 1) % 100 == 0:
            await conexion.execute(
                "UPDATE importaciones SET filas_procesadas=$1 WHERE id=$2",
                int(idx) + 1, importacion_id,
            )

    # Refrescar vistas materializadas (best effort: no romper importación si faltan)
    for vista in ("mv_kpis_pipeline", "mv_pipeline_por_etapa"):
        try:
            await conexion.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {vista}")
        except Exception as e:
            errores.append({"fila": 0, "error": f"No se pudo refrescar vista {vista}: {e}"})

    await conexion.execute(
        """UPDATE importaciones SET
            estado            = 'completado',
            filas_procesadas  = $1,
            filas_creadas     = $2,
            filas_actualizadas= $3,
            filas_error       = $4,
            errores           = $5::jsonb
        WHERE id = $6""",
        total, creadas, actualizadas, len(errores),
        json.dumps(errores), importacion_id,
    )


async def listar_historial(
    conexion: asyncpg.Connection,
    *,
    usuario_id: UUID | None = None,
) -> list[dict]:
    if usuario_id:
        filas = await conexion.fetch("""
        SELECT i.id, i.nombre_archivo, i.modo, i.estado,
               i.total_filas, i.filas_creadas, i.filas_actualizadas, i.filas_error,
               i.creado_en, u.nombre_completo AS usuario
        FROM importaciones i
        LEFT JOIN usuarios u ON u.id = i.usuario_id
        WHERE i.usuario_id = $1
        ORDER BY i.creado_en DESC
        LIMIT 20
    """, usuario_id)
    else:
        filas = await conexion.fetch("""
        SELECT i.id, i.nombre_archivo, i.modo, i.estado,
               i.total_filas, i.filas_creadas, i.filas_actualizadas, i.filas_error,
               i.creado_en, u.nombre_completo AS usuario
        FROM importaciones i
        LEFT JOIN usuarios u ON u.id = i.usuario_id
        ORDER BY i.creado_en DESC
        LIMIT 20
    """)
    return [dict(f) for f in filas]


async def obtener_estado(
    conexion: asyncpg.Connection,
    importacion_id: UUID,
    *,
    usuario_id: UUID | None = None,
) -> dict | None:
    if usuario_id:
        fila = await conexion.fetchrow(
            "SELECT * FROM importaciones WHERE id = $1 AND usuario_id = $2",
            importacion_id,
            usuario_id,
        )
    else:
        fila = await conexion.fetchrow(
            "SELECT * FROM importaciones WHERE id = $1",
            importacion_id,
        )
    if not fila:
        return None
    data = dict(fila)
    data["errores"] = _normalizar_errores(data.get("errores"))
    return data


async def responder_chat_csv(
    conexion: asyncpg.Connection,
    *,
    usuario_id: UUID | None = None,
    pregunta: str,
    importacion_id: UUID | None = None,
) -> dict:
    """Responde preguntas sobre el contenido del CSV seleccionado usando IC (copilot)."""
    try:
        return await _responder_chat_csv_impl(
            conexion=conexion,
            usuario_id=usuario_id,
            pregunta=pregunta,
            importacion_id=importacion_id,
        )
    except Exception:
        return {
            "respuesta": (
                "Ahora mismo no he podido procesar la consulta del CSV. "
                "Vuelve a intentarlo en unos segundos y, si persiste, reabre el CSV con 'Ver CSV'."
            ),
            "importacion_id_contexto": str(importacion_id) if importacion_id else None,
            "resumen": {"importaciones": 0, "total_filas": 0, "creadas": 0, "actualizadas": 0, "errores": 0},
        }


async def _responder_chat_csv_impl(
    conexion: asyncpg.Connection,
    *,
    usuario_id: UUID | None = None,
    pregunta: str,
    importacion_id: UUID | None = None,
) -> dict:
    """Implementación interna del chat CSV."""
    if importacion_id:
        if usuario_id:
            fila_objetivo = await conexion.fetchrow(
                """
                SELECT id, nombre_archivo, estado, modo, total_filas,
                       filas_creadas, filas_actualizadas, filas_error, creado_en,
                       preview_columnas, preview_filas
                FROM importaciones
                WHERE id = $1 AND usuario_id = $2
                """,
                importacion_id,
                usuario_id,
            )
        else:
            fila_objetivo = await conexion.fetchrow(
                """
                SELECT id, nombre_archivo, estado, modo, total_filas,
                       filas_creadas, filas_actualizadas, filas_error, creado_en,
                       preview_columnas, preview_filas
                FROM importaciones
                WHERE id = $1
                """,
                importacion_id,
            )
        if not fila_objetivo:
            return {
                "respuesta": "No encuentro esa importación en tu historial o no tienes permisos para consultarla.",
                "resumen": {"importaciones": 0, "total_filas": 0, "errores": 0},
            }
        filas = [fila_objetivo]
    else:
        if usuario_id:
            filas = await conexion.fetch(
                """
                SELECT id, nombre_archivo, estado, modo, total_filas,
                       filas_creadas, filas_actualizadas, filas_error, creado_en,
                       preview_columnas, preview_filas
                FROM importaciones
                WHERE usuario_id = $1
                ORDER BY creado_en DESC
                LIMIT 8
                """,
                usuario_id,
            )
        else:
            filas = await conexion.fetch(
                """
                SELECT id, nombre_archivo, estado, modo, total_filas,
                       filas_creadas, filas_actualizadas, filas_error, creado_en,
                       preview_columnas, preview_filas
                FROM importaciones
                ORDER BY creado_en DESC
                LIMIT 8
                """,
            )
    if not filas:
        return {
            "respuesta": "No encuentro importaciones previas para tu usuario. Sube un CSV y vuelves a consultar.",
            "resumen": {"importaciones": 0, "total_filas": 0, "errores": 0},
        }

    items = [dict(f) for f in filas]
    total_filas = sum(int(i.get("total_filas") or 0) for i in items)
    total_errores = sum(int(i.get("filas_error") or 0) for i in items)
    total_creadas = sum(int(i.get("filas_creadas") or 0) for i in items)
    total_actualizadas = sum(int(i.get("filas_actualizadas") or 0) for i in items)
    ultima = items[0]
    contexto_id = str(importacion_id or ultima.get("id"))

    preview_cols = _normalizar_json_lista(ultima.get("preview_columnas"))
    preview_rows = _normalizar_json_lista(ultima.get("preview_filas"))
    if not preview_cols or not preview_rows:
        return {
            "respuesta": (
                "No tengo vista previa del CSV seleccionado. "
                "Abre un CSV del historial (Ver CSV) o vuelve a importarlo para guardar contexto."
            ),
            "importacion_id_contexto": contexto_id,
            "resumen": {
                "importaciones": len(items),
                "total_filas": total_filas,
                "creadas": total_creadas,
                "actualizadas": total_actualizadas,
                "errores": total_errores,
            },
        }

    # Respuesta IC real sobre contenido del CSV (configuración de Copilot IC).
    try:
        from app.modules.ia.servicio import ConfigIA, llamar_ia

        columnas_txt = ", ".join(str(c) for c in preview_cols[:40])
        muestra = preview_rows[:80]
        muestra_txt = "\n".join(
            "- " + " | ".join(f"{c}={str(r.get(c, '')).strip()}" for c in preview_cols[:12])
            for r in muestra
        )

        system = (
            "Eres IC (Inteligencia Comercial). "
            "Analizas exclusivamente el contenido del CSV proporcionado por el usuario. "
            "Responde en español de España, directo y accionable. "
            "No hables de histórico de importaciones salvo que te lo pidan explícitamente. "
            "Si falta dato, dilo sin inventar."
        )
        user_prompt = (
            f"Archivo CSV: {ultima.get('nombre_archivo')}\n"
            f"Columnas disponibles: {columnas_txt}\n"
            f"Filas de contexto ({len(muestra)}):\n{muestra_txt}\n\n"
            f"Pregunta:\n{pregunta}"
        )
        texto_ia = await llamar_ia(
            mensajes=[{"role": "user", "content": user_prompt}],
            system=system,
            config=ConfigIA(
                proveedor=PROVEEDOR_LOCAL,
                ollama_url=str((obtener_configs_operacionales().get("importacion", {}) or {}).get("ollama_url") or configuracion.OLLAMA_URL),
                ollama_modelo=str((obtener_configs_operacionales().get("importacion", {}) or {}).get("ollama_modelo") or configuracion.OLLAMA_MODEL_DEFAULT),
            ),
            max_tokens=900,
            timeout_segundos=15,
        )
        respuesta = (texto_ia or "").strip()
        if not respuesta:
            raise ValueError("Respuesta vacía de IC")
    except Exception:
        respuesta_preview = _respuesta_preview_por_tokens(pregunta, preview_cols, preview_rows)
        respuesta = respuesta_preview or (
            "No he podido responder con IA ahora mismo. "
            "Prueba con una consulta sobre columnas concretas del CSV (cuenta, owner, etapa, importe, id)."
        )

    return {
        "respuesta": respuesta,
        "importacion_id_contexto": contexto_id,
        "resumen": {
            "importaciones": len(items),
            "total_filas": total_filas,
            "creadas": total_creadas,
            "actualizadas": total_actualizadas,
            "errores": total_errores,
        },
    }


async def obtener_preview_importacion(
    conexion: asyncpg.Connection,
    *,
    importacion_id: UUID,
    usuario_id: UUID | None = None,
) -> dict | None:
    if usuario_id:
        fila = await conexion.fetchrow(
            """
            SELECT id, nombre_archivo, preview_columnas, preview_filas, creado_en
            FROM importaciones
            WHERE id = $1 AND usuario_id = $2
            """,
            importacion_id,
            usuario_id,
        )
    else:
        fila = await conexion.fetchrow(
            """
            SELECT id, nombre_archivo, preview_columnas, preview_filas, creado_en
            FROM importaciones
            WHERE id = $1
            """,
            importacion_id,
        )
    if not fila:
        return None
    data = dict(fila)
    columnas = data.get("preview_columnas") or []
    filas = data.get("preview_filas") or []
    if isinstance(columnas, str):
        try:
            columnas = json.loads(columnas)
        except Exception:
            columnas = []
    if isinstance(filas, str):
        try:
            filas = json.loads(filas)
        except Exception:
            filas = []
    data["columnas"] = columnas if isinstance(columnas, list) else []
    data["filas"] = filas if isinstance(filas, list) else []
    data.pop("preview_columnas", None)
    data.pop("preview_filas", None)
    return data
