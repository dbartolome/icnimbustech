"""
Lógica de negocio del módulo Forecast.
Modelo de predicción a 3 meses con datos reales del pipeline SGS España.
"""

import statistics
from datetime import date
from uuid import UUID

import asyncpg

# Win rates reales calculados del dataset (4317 ops)
SBU_WIN_RATES: dict[str, float] = {
    "Certification":               0.816,
    "Technical Consulting":        0.869,
    "Training":                    0.858,
    "Responsible Business Services": 0.860,
    "ESG Solutions":               0.657,
    "Second Party":                0.923,
}

# Etapas consideradas "pipeline maduro" (avanzadas, alta probabilidad)
ETAPAS_MADURAS = (
    "technically_approved",
    "estimation_sent",
    "contract_offer_sent",
    "estimation_accepted",
)

# Etapas cerradas
ETAPAS_CERRADAS = ("closed_won", "closed_lost", "closed_withdrawn")

# Distribución mensual en rampa (no lineal): 20% / 35% / 45%
RAMPA = (0.20, 0.35, 0.45)


def _es_error_esquema(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            asyncpg.exceptions.UndefinedTableError,
            asyncpg.exceptions.UndefinedColumnError,
        ),
    )


def _meses_siguientes() -> tuple[str, str, str]:
    """Retorna los 3 meses próximos en formato YYYY-MM."""
    hoy = date.today()
    resultado = []
    for i in range(1, 4):
        total_meses = hoy.month - 1 + i
        anio = hoy.year + total_meses // 12
        mes = total_meses % 12 + 1
        resultado.append(f"{anio}-{mes:02d}")
    return tuple(resultado)  # type: ignore[return-value]


def _calcular_escenario(base_total: float, maduro: float, pipe_pct: float, xsell_mult: float = 1.0) -> dict:
    pipe_won = maduro * pipe_pct * xsell_mult
    total = base_total + pipe_won
    return {
        "m1":    round(total * RAMPA[0], 2),
        "m2":    round(total * RAMPA[1], 2),
        "m3":    round(total * RAMPA[2], 2),
        "total": round(total, 2),
    }


# =============================================================================
# Forecast
# =============================================================================

async def calcular_forecast(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    es_global: bool = False,
) -> dict:
    """
    Calcula forecast a 3 meses para un usuario.
    es_global=True → sin filtro de propietario (admin/manager ven todo el equipo).
    """
    filtro = "" if es_global else "AND o.propietario_id = $1"
    args: list = [] if es_global else [usuario_id]

    # 1. Baseline: mediana mensual de importe ganado en últimos 12 meses
    hist = await conexion.fetch(f"""
        SELECT
            TO_CHAR(fecha_decision, 'YYYY-MM') AS mes,
            SUM(importe) AS total
        FROM oportunidades o
        WHERE o.etapa = 'closed_won'
          AND o.importe > 0
          AND o.eliminado_en IS NULL
          AND o.fecha_decision >= CURRENT_DATE - INTERVAL '12 months'
          {filtro}
        GROUP BY mes
        ORDER BY mes
    """, *args)

    importes_mensuales = [float(r["total"]) for r in hist if r["total"]]
    baseline = statistics.median(importes_mensuales) if importes_mensuales else 0.0

    # 2. Pipeline activo total y maduro
    if es_global:
        pipe = await conexion.fetchrow("""
            SELECT
                COALESCE(SUM(importe), 0) AS total,
                COALESCE(SUM(importe) FILTER (WHERE etapa = ANY($1)), 0) AS maduro
            FROM oportunidades o
            WHERE o.etapa NOT IN ('closed_won', 'closed_lost', 'closed_withdrawn')
              AND o.importe > 0
              AND o.eliminado_en IS NULL
        """, list(ETAPAS_MADURAS))
    else:
        pipe = await conexion.fetchrow("""
            SELECT
                COALESCE(SUM(importe), 0) AS total,
                COALESCE(SUM(importe) FILTER (WHERE etapa = ANY($2)), 0) AS maduro
            FROM oportunidades o
            WHERE o.etapa NOT IN ('closed_won', 'closed_lost', 'closed_withdrawn')
              AND o.importe > 0
              AND o.eliminado_en IS NULL
              AND o.propietario_id = $1
        """, usuario_id, list(ETAPAS_MADURAS))

    pipeline_total = float(pipe["total"] or 0)
    pipeline_maduro = float(pipe["maduro"] or 0)

    # 3. SBU dominante en pipeline abierto
    sbu_row = await conexion.fetchrow(f"""
        SELECT s.nombre, COUNT(o.id) AS cnt
        FROM oportunidades o
        JOIN sbu s ON s.id = o.sbu_id
        WHERE o.etapa NOT IN ('closed_won', 'closed_lost', 'closed_withdrawn')
          AND o.eliminado_en IS NULL
          {filtro}
        GROUP BY s.nombre
        ORDER BY cnt DESC
        LIMIT 1
    """, *args)

    sbu_dominante = sbu_row["nombre"] if sbu_row else "Certification"
    wr_sbu = SBU_WIN_RATES.get(sbu_dominante, 0.816) * 100

    # 4. Nombre del usuario
    usuario_row = await conexion.fetchrow(
        "SELECT nombre_completo FROM usuarios WHERE id = $1", usuario_id
    )
    usuario_nombre = usuario_row["nombre_completo"] if usuario_row else str(usuario_id)

    # 5. Escenarios
    base_total = baseline * 3
    mes_1, mes_2, mes_3 = _meses_siguientes()

    return {
        "usuario_id":       str(usuario_id),
        "usuario_nombre":   usuario_nombre,
        "mes_1": mes_1, "mes_2": mes_2, "mes_3": mes_3,
        "pipeline_total":   pipeline_total,
        "pipeline_maduro":  pipeline_maduro,
        "baseline_mediana": round(baseline, 2),
        "sbu_dominante":    sbu_dominante,
        "wr_sbu":           wr_sbu,
        "pesimista": _calcular_escenario(base_total, pipeline_maduro, 0.00),
        "base":      _calcular_escenario(base_total, pipeline_maduro, 0.10),
        "optimista": _calcular_escenario(base_total, pipeline_maduro, 0.20, xsell_mult=1.15),
    }


async def guardar_snapshot(conexion: asyncpg.Connection, forecast: dict) -> str:
    """Persiste un forecast calculado como snapshot. Retorna el ID."""
    p = forecast["pesimista"]
    b = forecast["base"]
    o = forecast["optimista"]

    try:
        fila = await conexion.fetchrow("""
            INSERT INTO forecast_snapshots (
                usuario_id, usuario_nombre,
                mes_1, mes_2, mes_3,
                pipeline_total, pipeline_maduro, baseline_mediana,
                sbu_dominante, wr_sbu,
                pesimista_m1, pesimista_m2, pesimista_m3, pesimista_total,
                base_m1, base_m2, base_m3, base_total,
                optimista_m1, optimista_m2, optimista_m3, optimista_total
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,
                $11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22
            ) RETURNING id::TEXT
        """,
            UUID(forecast["usuario_id"]), forecast["usuario_nombre"],
            forecast["mes_1"], forecast["mes_2"], forecast["mes_3"],
            forecast["pipeline_total"], forecast["pipeline_maduro"],
            forecast["baseline_mediana"], forecast["sbu_dominante"], forecast["wr_sbu"],
            p["m1"], p["m2"], p["m3"], p["total"],
            b["m1"], b["m2"], b["m3"], b["total"],
            o["m1"], o["m2"], o["m3"], o["total"],
        )
    except Exception as exc:
        if _es_error_esquema(exc):
            return ""
        raise
    return fila["id"] if fila else ""


async def obtener_snapshot_reciente(
    conexion: asyncpg.Connection, usuario_id: UUID, max_dias: int = 7
) -> dict | None:
    try:
        fila = await conexion.fetchrow("""
            SELECT id, usuario_id, usuario_nombre,
                   snapshot_date::TEXT AS snapshot_date,
                   mes_1, mes_2, mes_3,
                   pipeline_total, pipeline_maduro, baseline_mediana,
                   sbu_dominante, wr_sbu,
                   pesimista_m1, pesimista_m2, pesimista_m3, pesimista_total,
                   base_m1, base_m2, base_m3, base_total,
                   optimista_m1, optimista_m2, optimista_m3, optimista_total,
                   real_m1, real_m2, real_m3,
                   creado_en::TEXT AS creado_en
            FROM forecast_snapshots
            WHERE usuario_id = $1
              AND snapshot_date >= CURRENT_DATE - ($2 * INTERVAL '1 day')
            ORDER BY snapshot_date DESC
            LIMIT 1
        """, usuario_id, max_dias)
    except Exception as exc:
        if _es_error_esquema(exc):
            return None
        raise
    return dict(fila) if fila else None


async def listar_snapshots(conexion: asyncpg.Connection, usuario_id: UUID) -> list[dict]:
    try:
        filas = await conexion.fetch("""
            SELECT id, usuario_id, usuario_nombre,
                   snapshot_date::TEXT AS snapshot_date,
                   mes_1, mes_2, mes_3,
                   pipeline_total, pipeline_maduro, baseline_mediana,
                   sbu_dominante, wr_sbu,
                   pesimista_m1, pesimista_m2, pesimista_m3, pesimista_total,
                   base_m1, base_m2, base_m3, base_total,
                   optimista_m1, optimista_m2, optimista_m3, optimista_total,
                   real_m1, real_m2, real_m3,
                   creado_en::TEXT AS creado_en
            FROM forecast_snapshots
            WHERE usuario_id = $1
            ORDER BY snapshot_date DESC
            LIMIT 12
        """, usuario_id)
    except Exception as exc:
        if _es_error_esquema(exc):
            return []
        raise
    return [dict(f) for f in filas]


async def actualizar_real(
    conexion: asyncpg.Connection,
    snapshot_id: UUID,
    usuario_id: UUID,
    mes: str,
    importe: float,
) -> bool:
    if mes not in ("m1", "m2", "m3"):
        return False
    col = f"real_{mes}"
    try:
        resultado = await conexion.execute(
            f"UPDATE forecast_snapshots SET {col} = $1 WHERE id = $2 AND usuario_id = $3",
            importe, snapshot_id, usuario_id,
        )
    except Exception as exc:
        if _es_error_esquema(exc):
            return False
        raise
    return resultado == "UPDATE 1"


# =============================================================================
# Forecast de equipo (admin/manager)
# =============================================================================

async def calcular_forecast_equipo(
    conexion: asyncpg.Connection,
    usuario_ids: list[UUID],
) -> dict:
    """Forecast consolidado para una lista de usuarios."""
    comerciales = []
    for uid in usuario_ids:
        f = await calcular_forecast(conexion, uid)
        comerciales.append({
            "usuario_nombre":   f["usuario_nombre"],
            "pipeline_maduro":  f["pipeline_maduro"],
            "baseline_mediana": f["baseline_mediana"],
            "sbu_dominante":    f["sbu_dominante"],
            "pesimista_total":  f["pesimista"]["total"],
            "base_total":       f["base"]["total"],
            "optimista_total":  f["optimista"]["total"],
        })

    comerciales.sort(key=lambda x: -x["base_total"])

    return {
        "comerciales":       comerciales,
        "totales_pesimista": round(sum(c["pesimista_total"] for c in comerciales), 2),
        "totales_base":      round(sum(c["base_total"] for c in comerciales), 2),
        "totales_optimista": round(sum(c["optimista_total"] for c in comerciales), 2),
    }


# =============================================================================
# Cola de cross-sell por comercial
# =============================================================================

async def build_cross_sell_queue(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
) -> list[dict]:
    """
    Encuentra las cuentas del comercial con Won en 1 sola SBU
    y las puntúa por potencial de cross-sell.
    Score = (ops_abiertas × 10) + (pipeline_abierto / 1000) + (en_top50 × 50)
    """
    # Cuentas donde el comercial tiene Won con 1 sola SBU
    cuentas_won = await conexion.fetch("""
        SELECT
            c.nombre AS cuenta_nombre,
            COUNT(DISTINCT s.nombre)               AS n_sbus,
            STRING_AGG(DISTINCT p.nombre, ', ')    AS productos_won,
            MAX(s.nombre)                          AS sbu_actual
        FROM oportunidades o
        JOIN cuentas c ON c.id = o.cuenta_id
        JOIN sbu s     ON s.id = o.sbu_id
        LEFT JOIN productos p ON p.id = o.producto_id
        WHERE o.propietario_id = $1
          AND o.etapa = 'closed_won'
          AND o.eliminado_en IS NULL
        GROUP BY c.nombre
        HAVING COUNT(DISTINCT s.nombre) = 1
    """, usuario_id)

    if not cuentas_won:
        return []

    resultado = []
    semana = date.today().strftime("%Y-W%W")

    for cuenta in cuentas_won:
        cuenta_nombre = cuenta["cuenta_nombre"]

        # Pipeline abierto en esa cuenta (de cualquier propietario)
        open_data = await conexion.fetchrow("""
            SELECT
                COUNT(o.id)               AS ops,
                COALESCE(SUM(o.importe), 0) AS amt
            FROM oportunidades o
            JOIN cuentas c ON c.id = o.cuenta_id
            WHERE c.nombre = $1
              AND o.etapa NOT IN ('closed_won', 'closed_lost', 'closed_withdrawn')
              AND o.importe > 0
              AND o.eliminado_en IS NULL
        """, cuenta_nombre)

        # Enriquecer con cross_selling_intelligence si existe
        try:
            intel = await conexion.fetchrow("""
                SELECT oportunidades_top, mensaje_comercial, preguntas_discovery, confianza
                FROM cross_selling_intelligence
                WHERE account_name ILIKE $1
                LIMIT 1
            """, f"%{cuenta_nombre[:25]}%")
        except Exception as exc:
            if _es_error_esquema(exc):
                intel = None
            else:
                raise

        ops_abiertas = int(open_data["ops"] or 0)
        pipeline_abierto = float(open_data["amt"] or 0)
        score = (ops_abiertas * 10) + (pipeline_abierto / 1000) + (50 if intel else 0)

        resultado.append({
            "cuenta_nombre":      cuenta_nombre,
            "sbu_actual":         cuenta["sbu_actual"],
            "productos_won":      cuenta["productos_won"],
            "ops_abiertas":       ops_abiertas,
            "pipeline_abierto":   pipeline_abierto,
            "oportunidades_top":  intel["oportunidades_top"] if intel else None,
            "mensaje_comercial":  intel["mensaje_comercial"] if intel else None,
            "preguntas_discovery": intel["preguntas_discovery"] if intel else None,
            "confianza":          intel["confianza"] if intel else None,
            "score":              round(score, 2),
        })

    return sorted(resultado, key=lambda x: -x["score"])


async def obtener_queue_semana(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    limit: int = 10,
) -> list[dict]:
    """Retorna la cola de cross-sell en caché para la semana actual."""
    semana = date.today().strftime("%Y-W%W")
    try:
        filas = await conexion.fetch("""
            SELECT id, cuenta_nombre, sbu_actual, productos_won,
                   ops_abiertas, pipeline_abierto, oportunidades_top,
                   mensaje_comercial, preguntas_discovery, confianza, score
            FROM owner_cross_sell_queue
            WHERE usuario_id = $1 AND semana = $2
            ORDER BY score DESC
            LIMIT $3
        """, usuario_id, semana, limit)
    except Exception as exc:
        if _es_error_esquema(exc):
            return []
        raise
    return [dict(f) for f in filas]


async def guardar_queue(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    usuario_nombre: str,
    queue: list[dict],
) -> None:
    semana = date.today().strftime("%Y-W%W")
    # Borrar caché anterior de esta semana
    try:
        await conexion.execute(
            "DELETE FROM owner_cross_sell_queue WHERE usuario_id = $1 AND semana = $2",
            usuario_id, semana,
        )
    except Exception as exc:
        if _es_error_esquema(exc):
            return
        raise
    if not queue:
        return
    for item in queue[:20]:
        try:
            await conexion.execute("""
                INSERT INTO owner_cross_sell_queue (
                    usuario_id, usuario_nombre, cuenta_nombre, sbu_actual,
                    productos_won, ops_abiertas, pipeline_abierto,
                    oportunidades_top, mensaje_comercial, preguntas_discovery,
                    confianza, score, semana
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
            """,
                usuario_id, usuario_nombre, item["cuenta_nombre"], item["sbu_actual"],
                item["productos_won"], item["ops_abiertas"], item["pipeline_abierto"],
                item["oportunidades_top"], item["mensaje_comercial"],
                item["preguntas_discovery"], item["confianza"], item["score"], semana,
            )
        except Exception as exc:
            if _es_error_esquema(exc):
                return
            raise
