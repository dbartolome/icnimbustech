"""
Skill: generar_pdf — Propuesta Comercial SGS España
Genera un informe PDF profesional de 12+ páginas con gráficas nativas de ReportLab,
análisis de pipeline, escenarios, plan de acción y argumentario extendido.
"""

import io
import json
from datetime import date
from uuid import UUID

import asyncpg
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.platypus.flowables import Flowable
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Group
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend


def _parse_jsonb(valor, default):
    if isinstance(valor, (dict, list)):
        return valor
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except (json.JSONDecodeError, ValueError):
            pass
    return default


# ── Paleta ───────────────────────────────────────────────────────────────────
ROJO_SGS      = colors.Color(0xC0/255, 0x00/255, 0x1A/255)
ROJO_CLARO    = colors.Color(0xE8/255, 0x20/255, 0x30/255)
NEGRO         = colors.Color(0x1A/255, 0x1A/255, 0x1A/255)
NEGRO_SUAVE   = colors.Color(0x1A/255, 0x1A/255, 0x2E/255)
GRIS_OSCURO   = colors.Color(0x3A/255, 0x3A/255, 0x3A/255)
GRIS_MEDIO    = colors.Color(0x88/255, 0x88/255, 0x88/255)
GRIS_CLARO    = colors.Color(0xF5/255, 0xF5/255, 0xF5/255)
GRIS_BORDE    = colors.Color(0xDD/255, 0xDD/255, 0xDD/255)
VERDE         = colors.Color(0x1A/255, 0x7A/255, 0x1A/255)
VERDE_CLARO   = colors.Color(0xE8/255, 0xF5/255, 0xE8/255)
NARANJA       = colors.Color(0xE6/255, 0x7E/255, 0x00/255)
NARANJA_CLARO = colors.Color(0xFF/255, 0xF3/255, 0xE0/255)
AZUL          = colors.Color(0x1A/255, 0x5F/255, 0x9A/255)
AZUL_CLARO    = colors.Color(0xE8/255, 0xF0/255, 0xFA/255)
AZUL_OSCURO   = colors.Color(0x0D/255, 0x3B/255, 0x6E/255)

# Paleta para gráficas (ReportLab colors — distintos de los de arriba)
_C_PES = colors.Color(0.85, 0.25, 0.25)   # rojo suave
_C_MED = colors.Color(0.90, 0.55, 0.10)   # naranja
_C_OPT = colors.Color(0.20, 0.65, 0.30)   # verde

_PALETTE = [
    colors.Color(0.75, 0.15, 0.15),
    colors.Color(0.90, 0.55, 0.10),
    colors.Color(0.20, 0.55, 0.85),
    colors.Color(0.20, 0.65, 0.30),
    colors.Color(0.60, 0.20, 0.80),
    colors.Color(0.10, 0.65, 0.65),
]

_ETAPA_LABEL = {
    "prospection":    "Prospección",
    "qualification":  "Cualificación",
    "proposal":       "Propuesta",
    "negotiation":    "Negociación",
    "value_prop":     "Propuesta de valor",
    "id_decision":    "Decisor identificado",
    "perception":     "Percepción de valor",
    "closed_won":     "Ganadas",
    "closed_lost":    "Perdidas",
    "closed_withdrawn": "Retiradas",
}


# ── Flowable: barra de progreso ───────────────────────────────────────────────
class BarraProgreso(Flowable):
    def __init__(self, pct: int, color_barra=ROJO_SGS, ancho=14*cm, alto=0.35*cm):
        super().__init__()
        self.pct = min(max(pct, 0), 100)
        self.color_barra = color_barra
        self.width = ancho
        self.height = alto

    def draw(self):
        self.canv.setFillColor(GRIS_CLARO)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        self.canv.setFillColor(self.color_barra)
        self.canv.rect(0, 0, self.width * self.pct / 100, self.height, fill=1, stroke=0)
        self.canv.setFillColor(colors.white if self.pct > 20 else GRIS_OSCURO)
        self.canv.setFont("Helvetica-Bold", 7)
        self.canv.drawString(4, 2, f"{self.pct}%")


# ── Estilos ───────────────────────────────────────────────────────────────────
def _estilos():
    s = getSampleStyleSheet()

    def add(name, **kw):
        if name not in s:
            s.add(ParagraphStyle(name, **kw))

    add("SGS_Titulo",       parent=s["Title"],    textColor=ROJO_SGS,    fontSize=26, leading=30, spaceAfter=8,  fontName="Helvetica-Bold")
    add("SGS_Subtitulo",    parent=s["Normal"],   textColor=GRIS_OSCURO, fontSize=14, spaceAfter=6)
    add("SGS_Seccion",      parent=s["Heading2"], textColor=ROJO_SGS,    fontSize=12, leading=15, spaceBefore=12, spaceAfter=7, fontName="Helvetica-Bold", keepWithNext=True)
    add("SGS_Subseccion",   parent=s["Heading3"], textColor=AZUL_OSCURO, fontSize=10, leading=13, spaceBefore=8, spaceAfter=5, fontName="Helvetica-Bold", keepWithNext=True)
    add("SGS_Cuerpo",       parent=s["Normal"],   textColor=NEGRO,       fontSize=9,  leading=14, spaceAfter=4)
    add("SGS_Cuerpo_Lg",    parent=s["Normal"],   textColor=NEGRO,       fontSize=10, leading=15, spaceAfter=5)
    add("SGS_Bullet",       parent=s["Normal"],   textColor=GRIS_OSCURO, fontSize=9,  leading=13, leftIndent=14, spaceAfter=2, firstLineIndent=-6)
    add("SGS_Cabecera",     parent=s["Normal"],   textColor=colors.white, fontSize=8, fontName="Helvetica-Bold", alignment=1)
    add("SGS_CabIzq",       parent=s["Normal"],   textColor=colors.white, fontSize=8, fontName="Helvetica-Bold")
    add("SGS_Meta",         parent=s["Normal"],   textColor=GRIS_MEDIO,  fontSize=8)
    add("SGS_KPI_Val",      parent=s["Normal"],   textColor=ROJO_SGS,    fontSize=18, fontName="Helvetica-Bold", alignment=1)
    add("SGS_KPI_Lbl",      parent=s["Normal"],   textColor=GRIS_MEDIO,  fontSize=7,  alignment=1)
    add("SGS_Pie",          parent=s["Normal"],   textColor=GRIS_MEDIO,  fontSize=7,  alignment=1)
    add("SGS_Highlight",    parent=s["Normal"],   textColor=AZUL_OSCURO, fontSize=10, fontName="Helvetica-Bold", spaceAfter=3)
    add("SGS_Indice",       parent=s["Normal"],   textColor=NEGRO,       fontSize=10, leading=18, spaceAfter=2)
    add("SGS_Conclusiones", parent=s["Normal"],   textColor=NEGRO,       fontSize=10, leading=16, spaceAfter=6, leftIndent=8)
    return s


# ── Header/footer ─────────────────────────────────────────────────────────────
def _header_footer(canvas, doc, nombre_empresa: str):
    canvas.saveState()
    ancho, alto = A4

    if doc.page > 1:
        canvas.setFillColor(ROJO_SGS)
        canvas.rect(0, alto - 0.7*cm, ancho, 0.7*cm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(colors.white)
        canvas.drawString(1.5*cm, alto - 0.49*cm, "SGS España · Propuesta Comercial Confidencial")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(ancho - 1.5*cm, alto - 0.49*cm, nombre_empresa[:55])

    canvas.setFillColor(NEGRO_SUAVE)
    canvas.rect(0, 0, ancho, 0.55*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRIS_MEDIO)
    canvas.drawString(1.5*cm, 0.15*cm, f"Documento confidencial · Uso exclusivo del equipo comercial · {date.today().strftime('%d/%m/%Y')}")
    canvas.drawRightString(ancho - 1.5*cm, 0.15*cm, f"Página {doc.page}")

    canvas.restoreState()


# ── Tabla genérica ─────────────────────────────────────────────────────────────
def _tabla(filas, col_widths, cabecera=True, alt_rows=True):
    t = Table(filas, colWidths=col_widths, repeatRows=1 if cabecera else 0)
    estilo = [
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID",     (0, 0), (-1, -1), 0.35, GRIS_BORDE),
        ("PADDING",  (0, 0), (-1, -1), 5),
        ("VALIGN",   (0, 0), (-1, -1), "MIDDLE"),
    ]
    if cabecera:
        estilo += [
            ("BACKGROUND", (0, 0), (-1, 0), ROJO_SGS),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    if alt_rows:
        estilo.append(("ROWBACKGROUNDS", (0, 1 if cabecera else 0), (-1, -1), [colors.white, GRIS_CLARO]))
    t.setStyle(TableStyle(estilo))
    return t


# ── Bloque KPI ─────────────────────────────────────────────────────────────────
def _kpi(valor: str, etiqueta: str, color_fondo=AZUL_CLARO, color_val=AZUL, ancho=4.1*cm) -> Table:
    s = _estilos()
    val_style = ParagraphStyle("kv", parent=s["SGS_KPI_Val"], textColor=color_val)
    lbl_style = s["SGS_KPI_Lbl"]
    t = Table(
        [[Paragraph(valor, val_style)], [Paragraph(etiqueta, lbl_style)]],
        colWidths=[ancho],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_fondo),
        ("PADDING",    (0, 0), (-1, -1), 7),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("BOX",        (0, 0), (-1, -1), 0.4, GRIS_BORDE),
    ]))
    return t


# ── Caja destacada ─────────────────────────────────────────────────────────────
def _caja_destacada(texto: str, color_fondo=AZUL_CLARO, color_texto=AZUL_OSCURO, ancho=16.6*cm) -> Table:
    s = _estilos()
    st = ParagraphStyle("dest", parent=s["SGS_Cuerpo_Lg"], textColor=color_texto)
    t = Table([[Paragraph(texto, st)]], colWidths=[ancho])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_fondo),
        ("PADDING",    (0, 0), (-1, -1), 10),
        ("BOX",        (0, 0), (-1, -1), 0.6, color_texto),
    ]))
    return t


# ── Gráfica: barras verticales (ReportLab nativo) ─────────────────────────────
def _grafica_barras_escenarios(pes: float, med: float, opt: float,
                                ancho_cm: float = 16.6, alto_cm: float = 5.5) -> Drawing:
    w = ancho_cm * cm
    h = alto_cm * cm
    drawing = Drawing(w, h)

    bc = VerticalBarChart()
    bc.x = 55
    bc.y = 35
    bc.width  = w - 80
    bc.height = h - 60

    bc.data = [(pes, med, opt)]
    bc.categoryAxis.categoryNames = ['Pesimista', 'Recomendado', 'Optimista']

    max_v = max(pes, med, opt, 1)
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = max_v * 1.25
    bc.valueAxis.valueStep = max_v / 4
    bc.valueAxis.labelTextFormat = lambda v: f"{v/1000:.0f}K €" if v >= 1000 else f"{v:.0f} €"
    bc.valueAxis.labels.fontSize = 7
    bc.categoryAxis.labels.fontSize = 9
    bc.categoryAxis.labels.fontName = "Helvetica-Bold"

    bc.bars[(0, 0)].fillColor = _C_PES
    bc.bars[(0, 1)].fillColor = _C_MED
    bc.bars[(0, 2)].fillColor = _C_OPT

    bc.barWidth = 0.5
    bc.groupSpacing = 30

    drawing.add(bc)
    return drawing


def _grafica_pipeline_barras(etapas: list[str], importes: list[float],
                              ancho_cm: float = 16.6, alto_cm: float = 5.5) -> Drawing:
    if not importes:
        return Drawing(1, 1)
    w = ancho_cm * cm
    h = alto_cm * cm
    drawing = Drawing(w, h)

    bc = VerticalBarChart()
    bc.x = 70
    bc.y = 40
    bc.width  = w - 90
    bc.height = h - 65

    bc.data = [tuple(importes)]
    bc.categoryAxis.categoryNames = etapas

    max_v = max(importes) or 1
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = max_v * 1.3
    bc.valueAxis.valueStep = max_v / 4
    bc.valueAxis.labelTextFormat = lambda v: f"{v/1000:.0f}K €" if v >= 1000 else f"{v:.0f} €"
    bc.valueAxis.labels.fontSize = 7
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.angle = 15 if len(etapas) > 4 else 0

    for i in range(len(importes)):
        bc.bars[(0, i)].fillColor = _PALETTE[i % len(_PALETTE)]

    drawing.add(bc)
    return drawing


def _grafica_pie_productos(nombres: list[str], valores: list[float],
                            ancho_cm: float = 8.0, alto_cm: float = 5.5) -> Drawing:
    if not valores or sum(valores) == 0:
        return Drawing(1, 1)
    w = ancho_cm * cm
    h = alto_cm * cm
    drawing = Drawing(w, h)

    pie = Pie()
    pie.x = 20
    pie.y = 30
    pie.width  = h - 50
    pie.height = h - 50
    pie.data = valores
    pie.labels = [n[:18] for n in nombres]
    pie.simpleLabels = 0
    pie.sideLabels = 1
    pie.startAngle = 90

    for i in range(len(valores)):
        pie.slices[i].fillColor = _PALETTE[i % len(_PALETTE)]
        pie.slices[i].strokeColor = colors.white
        pie.slices[i].strokeWidth = 1.5

    pie.slices.labelRadius = 1.3
    pie.slices.fontSize = 7

    drawing.add(pie)
    return drawing


# ── Función principal ─────────────────────────────────────────────────────────
async def generar_pdf_cuenta(
    cuenta_id: UUID,
    conexion: asyncpg.Connection,
) -> tuple[bytes, str]:

    fila = await conexion.fetchrow(
        """
        SELECT
            c.nombre AS nombre_cuenta,
            pc.productos_recomendados, pc.escenario_optimista,
            pc.escenario_medio, pc.escenario_pesimista,
            pc.plan_de_accion, pc.argumentario_general,
            pc.modelo_usado, pc.completado_en,
            ie.sector, ie.num_empleados, ie.facturacion_estimada,
            ie.certificaciones_actuales, ie.pain_points,
            ie.oportunidades_detectadas, ie.presencia_web,
            ie.completado_en AS investigacion_fecha
        FROM propuestas_comerciales pc
        JOIN cuentas c ON c.id = pc.cuenta_id
        LEFT JOIN investigaciones_empresa ie ON ie.id = pc.investigacion_id
        WHERE pc.cuenta_id = $1 AND pc.estado = 'completada'
        ORDER BY pc.creado_en DESC
        LIMIT 1
        """,
        cuenta_id,
    )
    if not fila:
        raise ValueError(f"Sin propuesta completada para la cuenta {cuenta_id}")

    # Pipeline activo
    ops_rows = await conexion.fetch(
        """
        SELECT
            COALESCE(etapa::TEXT, 'sin_etapa') AS etapa,
            COUNT(*) AS total_ops,
            COALESCE(SUM(importe), 0) AS importe_total
        FROM oportunidades
        WHERE cuenta_id = $1 AND eliminado_en IS NULL
          AND etapa::TEXT NOT IN ('closed_won','closed_lost','closed_withdrawn')
        GROUP BY etapa
        ORDER BY importe_total DESC
        """,
        cuenta_id,
    )

    # Productos en pipeline
    prods_pipeline = await conexion.fetch(
        """
        SELECT
            COALESCE(p.nombre, o.linea_negocio, 'Sin categoría') AS producto,
            COUNT(o.id) AS total,
            COALESCE(SUM(o.importe), 0) AS importe
        FROM oportunidades o
        LEFT JOIN productos p ON p.id = o.producto_id
        WHERE o.cuenta_id = $1 AND o.eliminado_en IS NULL
          AND o.etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
        GROUP BY COALESCE(p.nombre, o.linea_negocio, 'Sin categoría')
        ORDER BY importe DESC
        LIMIT 6
        """,
        cuenta_id,
    )

    # Totales pipeline
    total_pipeline = float(sum(r["importe_total"] for r in ops_rows))
    total_ops = int(sum(r["total_ops"] for r in ops_rows))

    # Parse
    nombre    = fila["nombre_cuenta"]
    est       = _estilos()
    productos = _parse_jsonb(fila["productos_recomendados"], [])
    esc_opt   = _parse_jsonb(fila["escenario_optimista"], {})
    esc_med   = _parse_jsonb(fila["escenario_medio"], {})
    esc_pes   = _parse_jsonb(fila["escenario_pesimista"], {})
    plan      = _parse_jsonb(fila["plan_de_accion"], [])
    pain      = _parse_jsonb(fila["pain_points"], [])
    oport_ia  = _parse_jsonb(fila["oportunidades_detectadas"], [])
    certs     = _parse_jsonb(fila["certificaciones_actuales"], [])

    importe_opt = float(esc_opt.get("importe", 0) or 0)
    importe_med = float(esc_med.get("importe", 0) or 0)
    importe_pes = float(esc_pes.get("importe", 0) or 0)

    el = []  # story

    # ════════════════════════════════════════════════════════════════
    # PORTADA
    # ════════════════════════════════════════════════════════════════
    el.append(Spacer(1, 1.2*cm))

    # Banda lateral + header de portada
    banda = Table([["", ""]], colWidths=[0.45*cm, 16.15*cm])
    banda.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), ROJO_SGS),
        ("BACKGROUND", (1, 0), (1, 0), NEGRO_SUAVE),
        ("ROWHEIGHT",  (0, 0), (-1, -1), 2.2*cm),
    ]))
    el.append(banda)
    el.append(Spacer(1, 0.6*cm))

    el.append(Paragraph("SGS España", ParagraphStyle("logo", fontSize=34, textColor=ROJO_SGS, fontName="Helvetica-Bold")))
    el.append(Paragraph("Inteligencia Comercial — Sistema IC", ParagraphStyle("sub", fontSize=13, textColor=GRIS_MEDIO)))
    el.append(Spacer(1, 0.8*cm))
    el.append(HRFlowable(width="100%", thickness=1.5, color=ROJO_SGS))
    el.append(Spacer(1, 0.5*cm))
    el.append(Paragraph("PROPUESTA COMERCIAL ESTRATÉGICA", ParagraphStyle("tipo", fontSize=11, textColor=GRIS_MEDIO, fontName="Helvetica-Bold")))
    el.append(Paragraph(nombre, est["SGS_Titulo"]))
    el.append(Spacer(1, 0.25*cm))
    el.append(Paragraph(
        f"Sector: <b>{fila['sector'] or 'N/D'}</b>  ·  Generado el {date.today().strftime('%d de %B de %Y')}  ·  Documento confidencial",
        est["SGS_Meta"],
    ))
    el.append(Spacer(1, 0.9*cm))

    # KPIs portada (2 filas)
    kpi_row1 = [
        _kpi(f"{importe_med:,.0f} €",   "Escenario recomendado",    AZUL_CLARO,   AZUL),
        _kpi(f"{importe_opt:,.0f} €",   "Escenario optimista",      VERDE_CLARO,  VERDE),
        _kpi(f"{importe_pes:,.0f} €",   "Escenario pesimista",      NARANJA_CLARO, NARANJA),
        _kpi(f"{esc_med.get('probabilidad', 0)}%", "Probabilidad media", GRIS_CLARO, ROJO_SGS),
    ]
    kpi_row2 = [
        _kpi(f"{len(productos)}",        "Productos recomendados",   GRIS_CLARO,   NEGRO),
        _kpi(f"{total_ops}",             "Oportunidades activas",    AZUL_CLARO,   AZUL_OSCURO),
        _kpi(f"{total_pipeline:,.0f} €", "Pipeline total activo",    VERDE_CLARO,  VERDE),
        _kpi(f"{esc_med.get('plazo_meses', '?')} m", "Plazo estimado", GRIS_CLARO, GRIS_OSCURO),
    ]
    for row in [kpi_row1, kpi_row2]:
        t = Table([row], colWidths=[4.1*cm]*4, hAlign="LEFT")
        t.setStyle(TableStyle([("PADDING", (0, 0), (-1, -1), 3)]))
        el.append(t)
        el.append(Spacer(1, 0.3*cm))

    el.append(Spacer(1, 0.5*cm))
    el.append(Paragraph(
        f"Este documento ha sido generado automáticamente por el sistema IC de SGS España a partir del análisis "
        f"de datos reales de {nombre}. Incluye análisis de pipeline activo, estudio de fit de productos, "
        f"proyección de escenarios económicos, plan de acción priorizado y argumentario comercial detallado. "
        f"Contiene información confidencial destinada exclusivamente al equipo comercial.",
        est["SGS_Cuerpo"],
    ))
    el.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    # ÍNDICE
    # ════════════════════════════════════════════════════════════════
    el.append(Spacer(1, 0.5*cm))
    el.append(Paragraph("Índice de Contenidos", est["SGS_Seccion"]))
    el.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDE))
    el.append(Spacer(1, 0.4*cm))

    indice_items = [
        ("Resumen Ejecutivo",                     "Síntesis ejecutiva de hallazgos, valor potencial y recomendación principal"),
        ("1. Contexto Empresarial",               "Ficha, pain points, certificaciones y presencia digital"),
        ("2. Pipeline y Actividad Comercial",     "Análisis de oportunidades activas por etapa, importe y distribución por producto"),
        ("3. Análisis de Fit — Productos SGS",    "Score de adecuación por producto con indicadores visuales y argumentario"),
        ("4. Escenarios de Venta",                "Comparativa económica pesimista / recomendado / optimista con gráfica"),
        ("5. Plan de Acción Priorizado",          "Acciones ordenadas por prioridad con tipo, plazo e impacto estimado"),
        ("6. Argumentario Comercial",             "Mensajes clave por producto y estrategia de presentación"),
        ("7. ROI y Proyección de Valor",          "Análisis de retorno esperado, esperanza de ingreso y valor anualizado"),
        ("8. Análisis de Cross-Selling",          "Oportunidades de negocio adicional detectadas por IA y brechas de certificación"),
        ("9. Hoja de Ruta Ejecutiva",             "Timeline visual de ejecución con hitos y compromisos"),
        ("10. Conclusiones y Recomendaciones",    "Síntesis estratégica y call to action inmediato"),
    ]
    for titulo, desc in indice_items:
        row_t = Table(
            [[Paragraph(f"<b>{titulo}</b>", est["SGS_Indice"]), Paragraph(desc, est["SGS_Meta"])]],
            colWidths=[5.5*cm, 11*cm],
        )
        row_t.setStyle(TableStyle([
            ("PADDING",      (0, 0), (-1, -1), 5),
            ("LINEBELOW",    (0, 0), (-1, -1), 0.3, GRIS_BORDE),
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ]))
        el.append(row_t)

    el.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    # RESUMEN EJECUTIVO
    # ════════════════════════════════════════════════════════════════
    el.append(Spacer(1, 0.3*cm))
    el.append(Paragraph("Resumen Ejecutivo", est["SGS_Seccion"]))
    el.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDE))
    el.append(Spacer(1, 0.4*cm))

    mejor_producto = max(productos, key=lambda p: p.get("score_fit", 0), default={})
    accion_0 = plan[0].get("accion", "Contactar con el cliente") if plan else "Contactar con el cliente"

    resumen_texto = (
        f"<b>{nombre}</b> presenta un perfil comercial con <b>{total_ops} oportunidad{'es' if total_ops != 1 else ''} activa{'s' if total_ops != 1 else ''}</b> "
        f"en pipeline por un valor total de <b>{total_pipeline:,.0f} €</b>. "
        f"El análisis de inteligencia comercial identifica <b>{len(productos)} producto{'s' if len(productos) != 1 else ''}</b> "
        f"de SGS con alto grado de adecuación, siendo "
        f"<b>{mejor_producto.get('producto', 'el producto principal')}</b> la opción con mayor score de fit "
        f"({mejor_producto.get('score_fit', 0)}%). "
        f"El escenario comercial recomendado sitúa el potencial de cierre en "
        f"<b>{importe_med:,.0f} €</b> con una probabilidad estimada del "
        f"<b>{esc_med.get('probabilidad', 0)}%</b> y un plazo de "
        f"<b>{esc_med.get('plazo_meses', '?')} meses</b>."
    )
    el.append(Paragraph(resumen_texto, est["SGS_Cuerpo_Lg"]))
    el.append(Spacer(1, 0.5*cm))

    # 3 cajas de insights
    insight_rows = [
        [
            _caja_destacada(
                f"🏆 Mayor oportunidad\n{mejor_producto.get('producto', '—')}\nScore fit: {mejor_producto.get('score_fit', 0)}%",
                AZUL_CLARO, AZUL_OSCURO, 5.3*cm
            ),
            _caja_destacada(
                f"💰 Potencial recomendado\n{importe_med:,.0f} €\nEscenario medio — {esc_med.get('probabilidad', 0)}% probabilidad",
                VERDE_CLARO, VERDE, 5.3*cm
            ),
            _caja_destacada(
                f"⚡ Acción prioritaria\n{accion_0[:60]}{'…' if len(accion_0) > 60 else ''}",
                NARANJA_CLARO, NARANJA, 5.3*cm
            ),
        ]
    ]
    t_ins = Table(insight_rows, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    t_ins.setStyle(TableStyle([("PADDING", (0, 0), (-1, -1), 4)]))
    el.append(t_ins)
    el.append(Spacer(1, 0.5*cm))

    # Pain points en resumen (breve)
    if pain:
        el.append(Paragraph("<b>Necesidades críticas identificadas por la IA:</b>", est["SGS_Cuerpo"]))
        for p in pain[:3]:
            el.append(Paragraph(f"▸ {p}", est["SGS_Bullet"]))
        el.append(Spacer(1, 0.3*cm))

    if oport_ia and isinstance(oport_ia, list):
        el.append(Paragraph("<b>Oportunidades de negocio detectadas:</b>", est["SGS_Cuerpo"]))
        for o in oport_ia[:3]:
            texto_o = o if isinstance(o, str) else str(o)
            el.append(Paragraph(f"▸ {texto_o}", est["SGS_Bullet"]))

    el.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    # 1. CONTEXTO EMPRESARIAL
    # ════════════════════════════════════════════════════════════════
    el.append(Paragraph("1. Contexto Empresarial", est["SGS_Seccion"]))
    el.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDE))
    el.append(Spacer(1, 0.3*cm))

    # Ficha
    el.append(Paragraph("1.1 Ficha de la Empresa", est["SGS_Subseccion"]))
    ficha_datos = [
        [Paragraph("<b>Campo</b>", est["SGS_CabIzq"]), Paragraph("<b>Dato</b>", est["SGS_CabIzq"])],
        ["Razón social / Nombre comercial",  nombre],
        ["Sector de actividad",               fila["sector"] or "No identificado"],
        ["Número de empleados (estimado)",    str(fila["num_empleados"] or "No disponible")],
        ["Facturación estimada",              fila["facturacion_estimada"] or "No disponible"],
        ["Presencia web / Digital",           fila["presencia_web"] or "No encontrada"],
        ["Certificaciones actuales",          ", ".join(certs) if certs else "Ninguna detectada"],
        ["Fecha de investigación IA",
         str(fila["investigacion_fecha"])[:10] if fila["investigacion_fecha"] else "N/D"],
        ["Modelo IA utilizado",               fila["modelo_usado"] or "IC Sistema SGS"],
    ]
    el.append(_tabla(ficha_datos, [6*cm, 10.5*cm]))
    el.append(Spacer(1, 0.5*cm))

    # Pain points extendido
    if pain:
        el.append(Paragraph("1.2 Pain Points y Necesidades Detectadas", est["SGS_Subseccion"]))
        el.append(Paragraph(
            "La investigación de inteligencia artificial ha identificado los siguientes problemas "
            "críticos en la operativa de la empresa, que representan la principal palanca de entrada comercial:",
            est["SGS_Cuerpo"],
        ))
        pain_filas = [[
            Paragraph("<b>#</b>", est["SGS_Cabecera"]),
            Paragraph("<b>Problema / Necesidad identificada</b>", est["SGS_CabIzq"]),
            Paragraph("<b>Urgencia</b>", est["SGS_Cabecera"]),
        ]]
        for i, p in enumerate(pain[:8], 1):
            urgencia = "Alta" if i <= 2 else ("Media" if i <= 5 else "Baja")
            col_urg = ROJO_SGS if urgencia == "Alta" else (NARANJA if urgencia == "Media" else VERDE)
            pain_filas.append([
                str(i),
                str(p),
                Paragraph(f"<b>{urgencia}</b>", ParagraphStyle(
                    f"u{i}", fontSize=7, textColor=col_urg, fontName="Helvetica-Bold", alignment=1,
                )),
            ])
        el.append(_tabla(pain_filas, [0.8*cm, 13.5*cm, 1.8*cm]))
        el.append(Spacer(1, 0.4*cm))

    # Oportunidades IA
    if oport_ia and isinstance(oport_ia, list) and len(oport_ia) > 0:
        el.append(Paragraph("1.3 Oportunidades Estratégicas Detectadas por IA", est["SGS_Subseccion"]))
        el.append(Paragraph(
            "Las siguientes oportunidades han sido identificadas mediante análisis automático del perfil empresarial "
            "y pueden ser utilizadas como argumentos de apertura en la conversación comercial:",
            est["SGS_Cuerpo"],
        ))
        op_filas = [[
            Paragraph("<b>#</b>", est["SGS_Cabecera"]),
            Paragraph("<b>Oportunidad estratégica</b>", est["SGS_CabIzq"]),
        ]]
        for i, o in enumerate((oport_ia if isinstance(oport_ia, list) else [oport_ia])[:8], 1):
            op_filas.append([str(i), str(o)])
        el.append(_tabla(op_filas, [0.8*cm, 15.8*cm]))

    el.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    # 2. PIPELINE Y ACTIVIDAD COMERCIAL
    # ════════════════════════════════════════════════════════════════
    el.append(Paragraph("2. Pipeline y Actividad Comercial", est["SGS_Seccion"]))
    el.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDE))
    el.append(Spacer(1, 0.3*cm))

    if ops_rows:
        # KPIs de pipeline
        kpi_pipe = [
            _kpi(f"{total_ops}", "Oportunidades activas", AZUL_CLARO, AZUL),
            _kpi(f"{total_pipeline:,.0f} €", "Pipeline total", VERDE_CLARO, VERDE),
            _kpi(f"{len(ops_rows)}", "Etapas con actividad", GRIS_CLARO, NEGRO),
            _kpi(
                f"{total_pipeline/total_ops:,.0f} €" if total_ops else "—",
                "Importe medio/oport.",
                NARANJA_CLARO, NARANJA
            ),
        ]
        t_kpipe = Table([kpi_pipe], colWidths=[4.1*cm]*4, hAlign="LEFT")
        t_kpipe.setStyle(TableStyle([("PADDING", (0, 0), (-1, -1), 3)]))
        el.append(t_kpipe)
        el.append(Spacer(1, 0.4*cm))

        el.append(Paragraph("2.1 Distribución del Pipeline por Etapa", est["SGS_Subseccion"]))
        el.append(Paragraph(
            "El siguiente gráfico muestra la distribución del importe de pipeline activo "
            "según etapa comercial. Las oportunidades cerradas (ganadas, perdidas, retiradas) se excluyen del análisis.",
            est["SGS_Cuerpo"],
        ))

        # Gráfica pipeline
        etapas_labels = [_ETAPA_LABEL.get(r["etapa"], r["etapa"].replace("_", " ").title()) for r in ops_rows]
        etapas_importes = [float(r["importe_total"]) for r in ops_rows]
        el.append(Spacer(1, 0.2*cm))
        el.append(_grafica_pipeline_barras(etapas_labels, etapas_importes))
        el.append(Spacer(1, 0.3*cm))

        # Tabla detalle
        pipe_cab = [
            Paragraph("<b>Etapa</b>", est["SGS_CabIzq"]),
            Paragraph("<b>Nº Ops</b>", est["SGS_Cabecera"]),
            Paragraph("<b>Importe total (€)</b>", est["SGS_Cabecera"]),
            Paragraph("<b>% del pipeline</b>", est["SGS_Cabecera"]),
        ]
        pipe_filas = [pipe_cab]
        for r in ops_rows:
            etapa_label = _ETAPA_LABEL.get(r["etapa"], r["etapa"].replace("_", " ").title())
            pct = (float(r["importe_total"]) / total_pipeline * 100) if total_pipeline else 0
            pipe_filas.append([
                etapa_label,
                str(r["total_ops"]),
                f"{float(r['importe_total']):,.0f} €",
                f"{pct:.1f}%",
            ])
        # Fila total
        pipe_filas.append([
            Paragraph("<b>TOTAL</b>", ParagraphStyle("tot", fontSize=8, fontName="Helvetica-Bold")),
            Paragraph(f"<b>{total_ops}</b>", ParagraphStyle("tot2", fontSize=8, fontName="Helvetica-Bold", alignment=1)),
            Paragraph(f"<b>{total_pipeline:,.0f} €</b>", ParagraphStyle("tot3", fontSize=8, fontName="Helvetica-Bold", alignment=1)),
            Paragraph("<b>100%</b>", ParagraphStyle("tot4", fontSize=8, fontName="Helvetica-Bold", alignment=1)),
        ])
        t_pipe = _tabla(pipe_filas, [7*cm, 2.2*cm, 4.5*cm, 2.8*cm])
        t_pipe.setStyle(TableStyle([
            ("BACKGROUND", (0, -1), (-1, -1), NEGRO_SUAVE),
            ("TEXTCOLOR",  (0, -1), (-1, -1), colors.white),
        ]))
        el.append(t_pipe)
        el.append(Spacer(1, 0.4*cm))

    # Productos en pipeline
    if prods_pipeline:
        el.append(Paragraph("2.2 Productos más Activos en el Pipeline", est["SGS_Subseccion"]))
        el.append(Paragraph(
            "Distribución de las oportunidades activas por producto/línea de negocio, "
            "ordenadas por importe total acumulado en pipeline:",
            est["SGS_Cuerpo"],
        ))
        prod_pipe_cab = [
            Paragraph("<b>Producto / Línea de negocio</b>", est["SGS_CabIzq"]),
            Paragraph("<b>Nº ops</b>", est["SGS_Cabecera"]),
            Paragraph("<b>Importe pipeline (€)</b>", est["SGS_Cabecera"]),
            Paragraph("<b>% del total</b>", est["SGS_Cabecera"]),
        ]
        prod_pipe_filas = [prod_pipe_cab]
        for r in prods_pipeline:
            pct = (float(r["importe"]) / total_pipeline * 100) if total_pipeline else 0
            prod_pipe_filas.append([
                str(r["producto"]),
                str(r["total"]),
                f"{float(r['importe']):,.0f} €",
                f"{pct:.1f}%",
            ])
        el.append(_tabla(prod_pipe_filas, [8*cm, 1.5*cm, 4.5*cm, 2.5*cm]))
    else:
        el.append(_caja_destacada(
            "No se han encontrado oportunidades activas en el pipeline para esta cuenta. "
            "Esta situación representa una oportunidad de apertura para los productos SGS identificados.",
            NARANJA_CLARO, NARANJA,
        ))

    el.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    # 3. ANÁLISIS DE FIT — PRODUCTOS SGS
    # ════════════════════════════════════════════════════════════════
    if productos:
        el.append(Paragraph("3. Análisis de Fit — Productos SGS Recomendados", est["SGS_Seccion"]))
        el.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDE))
        el.append(Spacer(1, 0.3*cm))

        el.append(Paragraph(
            f"El sistema IC ha evaluado el grado de adecuación de <b>{len(productos)} productos SGS</b> "
            f"frente al perfil comercial de {nombre}. El score de fit pondera sector, pain points, "
            f"certificaciones existentes, tamaño de la empresa y datos de pipeline histórico.",
            est["SGS_Cuerpo"],
        ))
        el.append(Spacer(1, 0.3*cm))

        # Tabla de productos con barra visual
        prod_cabecera = [
            Paragraph("<b>Producto / Servicio SGS</b>", est["SGS_CabIzq"]),
            Paragraph("<b>Score Fit</b>", est["SGS_Cabecera"]),
            Paragraph("<b>Indicador visual</b>", est["SGS_Cabecera"]),
            Paragraph("<b>Argumentario comercial clave</b>", est["SGS_CabIzq"]),
        ]
        prod_filas = [prod_cabecera]
        for p in sorted(productos, key=lambda x: -x.get("score_fit", 0))[:8]:
            score = int(p.get("score_fit", 0))
            col_b = VERDE if score >= 80 else (NARANJA if score >= 60 else ROJO_SGS)
            prod_filas.append([
                Paragraph(f"<b>{p.get('producto', '')}</b>", est["SGS_Cuerpo"]),
                Paragraph(
                    f"<b>{score}%</b>",
                    ParagraphStyle("sc", fontSize=11, textColor=col_b, fontName="Helvetica-Bold", alignment=1),
                ),
                BarraProgreso(score, col_b, ancho=3.8*cm),
                Paragraph(p.get("argumentario", "")[:180], est["SGS_Cuerpo"]),
            ])
        t_prod = Table(prod_filas, colWidths=[4*cm, 1.5*cm, 4.2*cm, 6.8*cm], repeatRows=1)
        t_prod.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), ROJO_SGS),
            ("TEXTCOLOR",      (0, 0), (-1, 0), colors.white),
            ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",       (0, 0), (-1, -1), 8),
            ("GRID",           (0, 0), (-1, -1), 0.35, GRIS_BORDE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLARO]),
            ("PADDING",        (0, 0), (-1, -1), 5),
            ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ]))
        el.append(t_prod)
        el.append(Spacer(1, 0.4*cm))

        # Gráfica pie de distribución + leyenda de scores
        el.append(Paragraph("3.1 Distribución del Potencial por Producto", est["SGS_Subseccion"]))
        el.append(Paragraph(
            "El siguiente diagrama muestra la distribución del score de fit acumulado por producto, "
            "representando el peso relativo de cada opción en la estrategia comercial recomendada:",
            est["SGS_Cuerpo"],
        ))
        el.append(Spacer(1, 0.2*cm))

        nombres_pie = [p.get("producto", "")[:20] for p in sorted(productos, key=lambda x: -x.get("score_fit", 0))[:6]]
        valores_pie  = [float(p.get("score_fit", 0)) for p in sorted(productos, key=lambda x: -x.get("score_fit", 0))[:6]]

        # Pie chart + tabla de leyenda lado a lado
        pie_draw = _grafica_pie_productos(nombres_pie, valores_pie, ancho_cm=8.5, alto_cm=5.5)
        leyenda_filas = [[
            Paragraph("<b>Producto</b>", est["SGS_CabIzq"]),
            Paragraph("<b>Score</b>", est["SGS_Cabecera"]),
            Paragraph("<b>Prioridad</b>", est["SGS_Cabecera"]),
        ]]
        for i, (n, v) in enumerate(zip(nombres_pie, valores_pie)):
            prio = "Alta" if v >= 80 else ("Media" if v >= 60 else "Normal")
            leyenda_filas.append([n, f"{v:.0f}%", prio])
        t_ley = _tabla(leyenda_filas, [5*cm, 1.5*cm, 2*cm])

        combo = Table([[pie_draw, t_ley]], colWidths=[9.5*cm, 7*cm])
        combo.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 3)]))
        el.append(combo)
        el.append(Spacer(1, 0.4*cm))

        # Leyenda de colores
        el.append(Paragraph(
            "<b>Criterio de score:</b>  "
            "<font color='#1A7A1A'><b>≥ 80% → Alta afinidad</b></font>  ·  "
            "<font color='#E67E00'><b>≥ 60% → Afinidad media</b></font>  ·  "
            "<font color='#C0001A'><b>< 60% → Afinidad baja</b></font>",
            est["SGS_Cuerpo"],
        ))

    el.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    # 4. ESCENARIOS DE VENTA
    # ════════════════════════════════════════════════════════════════
    el.append(Paragraph("4. Escenarios de Venta — Análisis Económico Comparado", est["SGS_Seccion"]))
    el.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDE))
    el.append(Spacer(1, 0.3*cm))

    el.append(Paragraph(
        f"El sistema IC ha modelado tres escenarios de cierre comercial para {nombre}, "
        f"calibrados según el pipeline activo ({total_pipeline:,.0f} €), la probabilidad de conversión "
        f"y el plazo de ciclo de venta esperado. A continuación se presenta la comparativa y el análisis detallado:",
        est["SGS_Cuerpo"],
    ))
    el.append(Spacer(1, 0.3*cm))

    # Tabla comparativa
    esc_header = [
        Paragraph("<b>Métrica</b>", est["SGS_CabIzq"]),
        Paragraph("<b>🔴 Pesimista</b>", est["SGS_Cabecera"]),
        Paragraph("<b>🟡 Recomendado</b>", est["SGS_Cabecera"]),
        Paragraph("<b>🟢 Optimista</b>", est["SGS_Cabecera"]),
    ]
    esc_filas = [esc_header,
        ["Importe estimado (€)",
         f"{importe_pes:,.0f} €", f"{importe_med:,.0f} €", f"{importe_opt:,.0f} €"],
        ["Probabilidad de cierre",
         f"{esc_pes.get('probabilidad', 0)}%", f"{esc_med.get('probabilidad', 0)}%", f"{esc_opt.get('probabilidad', 0)}%"],
        ["Plazo estimado (meses)",
         f"{esc_pes.get('plazo_meses', '?')} meses", f"{esc_med.get('plazo_meses', '?')} meses", f"{esc_opt.get('plazo_meses', '?')} meses"],
        ["Productos principales",
         ", ".join(esc_pes.get("productos", [])[:2]) or "—",
         ", ".join(esc_med.get("productos", [])[:2]) or "—",
         ", ".join(esc_opt.get("productos", [])[:2]) or "—"],
        ["Importe ponderado (esperanza)",
         f"{importe_pes * esc_pes.get('probabilidad', 0) / 100:,.0f} €",
         f"{importe_med * esc_med.get('probabilidad', 0) / 100:,.0f} €",
         f"{importe_opt * esc_opt.get('probabilidad', 0) / 100:,.0f} €"],
    ]
    t_esc = Table(esc_filas, colWidths=[4.5*cm, 3.8*cm, 4*cm, 4.3*cm], repeatRows=1)
    t_esc.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), ROJO_SGS),
        ("BACKGROUND",  (1, 1), (1, -1), colors.Color(1.0, 0.94, 0.94)),
        ("BACKGROUND",  (2, 1), (2, -1), colors.Color(1.0, 0.97, 0.88)),
        ("BACKGROUND",  (3, 1), (3, -1), colors.Color(0.90, 0.98, 0.90)),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",    (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("GRID",        (0, 0), (-1, -1), 0.35, GRIS_BORDE),
        ("PADDING",     (0, 0), (-1, -1), 6),
        ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]))
    el.append(t_esc)
    el.append(Spacer(1, 0.4*cm))

    # Gráfica de barras de escenarios (ReportLab nativo)
    el.append(Paragraph("4.1 Comparativa Visual de Importes por Escenario", est["SGS_Subseccion"]))
    el.append(Paragraph(
        "La siguiente gráfica compara los importes estimados de los tres escenarios de venta:",
        est["SGS_Cuerpo"],
    ))
    el.append(Spacer(1, 0.2*cm))
    el.append(_grafica_barras_escenarios(importe_pes, importe_med, importe_opt))
    el.append(Spacer(1, 0.4*cm))

    # Detalle por escenario
    el.append(Paragraph("4.2 Detalle de Cada Escenario", est["SGS_Subseccion"]))
    for nombre_esc, esc_data, color_bg, emoji in [
        ("Escenario Recomendado (Medio)", esc_med, NARANJA_CLARO, "🟡"),
        ("Escenario Optimista",           esc_opt, VERDE_CLARO,  "🟢"),
        ("Escenario Pesimista",           esc_pes, colors.Color(1.0, 0.93, 0.93), "🔴"),
    ]:
        if esc_data.get("descripcion"):
            el.append(KeepTogether([
                _caja_destacada(
                    f"{emoji} <b>{nombre_esc}:</b> {esc_data['descripcion']}",
                    color_bg, GRIS_OSCURO,
                ),
                Spacer(1, 0.25*cm),
            ]))

    el.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    # 5. PLAN DE ACCIÓN
    # ════════════════════════════════════════════════════════════════
    if plan:
        el.append(Paragraph("5. Plan de Acción Priorizado", est["SGS_Seccion"]))
        el.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDE))
        el.append(Spacer(1, 0.3*cm))

        el.append(Paragraph(
            f"A continuación se presentan las {len(plan)} acciones comerciales recomendadas para {nombre}, "
            f"ordenadas por prioridad de ejecución. El plazo indicado es una estimación desde la fecha "
            f"de aprobación de la propuesta.",
            est["SGS_Cuerpo"],
        ))
        el.append(Spacer(1, 0.3*cm))

        plan_cab = [
            Paragraph("<b>P.</b>",       est["SGS_Cabecera"]),
            Paragraph("<b>Acción</b>",   est["SGS_CabIzq"]),
            Paragraph("<b>Tipo</b>",     est["SGS_Cabecera"]),
            Paragraph("<b>Plazo</b>",    est["SGS_Cabecera"]),
            Paragraph("<b>Impacto</b>",  est["SGS_Cabecera"]),
        ]
        plan_filas = [plan_cab]
        COLORES_TIPO = {"nuevo": VERDE_CLARO, "renovacion": NARANJA_CLARO, "upselling": AZUL_CLARO}
        for accion in sorted(plan, key=lambda x: x.get("prioridad", 99)):
            impacto = str(accion.get("impacto_estimado") or "").strip()[:40] or "—"
            plan_filas.append([
                Paragraph(
                    f"<b>{accion.get('prioridad', '-')}</b>",
                    ParagraphStyle("pp", fontSize=9, alignment=1, fontName="Helvetica-Bold"),
                ),
                Paragraph(accion.get("accion", "")[:150], est["SGS_Cuerpo"]),
                Paragraph(
                    accion.get("tipo", "").upper()[:12],
                    ParagraphStyle("pt", fontSize=7, textColor=AZUL, fontName="Helvetica-Bold", alignment=1),
                ),
                Paragraph(
                    f"{accion.get('plazo_dias', '?')}d",
                    ParagraphStyle("ppl", fontSize=8, alignment=1),
                ),
                Paragraph(impacto, est["SGS_Meta"]),
            ])
        t_plan = Table(plan_filas, colWidths=[0.8*cm, 9.5*cm, 2*cm, 1.2*cm, 3*cm], repeatRows=1)
        t_plan.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), ROJO_SGS),
            ("TEXTCOLOR",      (0, 0), (-1, 0), colors.white),
            ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",       (0, 0), (-1, -1), 8),
            ("GRID",           (0, 0), (-1, -1), 0.35, GRIS_BORDE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLARO]),
            ("ALIGN",          (0, 0), (0, -1), "CENTER"),
            ("ALIGN",          (2, 0), (3, -1), "CENTER"),
            ("PADDING",        (0, 0), (-1, -1), 5),
            ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ]))
        el.append(t_plan)
        el.append(Spacer(1, 0.6*cm))

        # Timeline visual
        el.append(Paragraph("5.1 Timeline Estimado de Ejecución", est["SGS_Subseccion"]))
        el.append(Paragraph(
            "Secuencia temporal recomendada de las acciones priorizadas:",
            est["SGS_Cuerpo"],
        ))
        el.append(Spacer(1, 0.2*cm))
        for accion in sorted(plan, key=lambda x: x.get("prioridad", 99))[:6]:
            plazo_d = accion.get("plazo_dias", 30)
            plazo_s = f"Día {plazo_d}" if isinstance(plazo_d, int) else str(plazo_d)
            tipo = str(accion.get("tipo", "nuevo")).lower()
            c_t = VERDE if tipo == "nuevo" else (NARANJA if tipo == "renovacion" else AZUL)
            row = Table(
                [[
                    Paragraph(f"<b>{plazo_s}</b>", ParagraphStyle("ts", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white, alignment=1)),
                    Paragraph(accion.get("accion", "")[:100], ParagraphStyle("ta", fontSize=8, textColor=NEGRO)),
                    Paragraph(tipo.upper(), ParagraphStyle("tt", fontSize=7, fontName="Helvetica-Bold", textColor=c_t)),
                ]],
                colWidths=[1.8*cm, 12*cm, 2.5*cm],
            )
            row.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), c_t),
                ("BACKGROUND", (1, 0), (-1, 0), GRIS_CLARO),
                ("PADDING",    (0, 0), (-1, -1), 5),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW",  (0, 0), (-1, -1), 0.3, GRIS_BORDE),
            ]))
            el.append(row)

    el.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    # 6. ARGUMENTARIO COMERCIAL
    # ════════════════════════════════════════════════════════════════
    if fila["argumentario_general"]:
        el.append(Paragraph("6. Argumentario Comercial para el Equipo de Ventas", est["SGS_Seccion"]))
        el.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDE))
        el.append(Spacer(1, 0.3*cm))

        el.append(Paragraph(
            f"El siguiente argumentario ha sido generado específicamente para la conversación comercial con {nombre}. "
            f"Incluye los mensajes clave, objeciones anticipadas y estrategia de posicionamiento. "
            f"Úsalo como guía de referencia antes de cada reunión:",
            est["SGS_Cuerpo"],
        ))
        el.append(Spacer(1, 0.3*cm))

        for parrafo in fila["argumentario_general"].split("\n\n"):
            parrafo = parrafo.strip()
            if not parrafo:
                continue
            if parrafo.startswith("#") or parrafo.isupper() or len(parrafo) < 50:
                el.append(Paragraph(parrafo.lstrip("#").strip(), est["SGS_Subseccion"]))
            elif parrafo.startswith("-") or parrafo.startswith("•"):
                for linea in parrafo.split("\n"):
                    if linea.strip():
                        el.append(Paragraph(f"▸ {linea.lstrip('-•').strip()}", est["SGS_Bullet"]))
            else:
                el.append(Paragraph(parrafo, est["SGS_Cuerpo"]))

        el.append(Spacer(1, 0.4*cm))

    # Argumentario por producto
    if productos:
        el.append(Paragraph("6.1 Argumentario Específico por Producto", est["SGS_Subseccion"]))
        el.append(Paragraph(
            "Mensajes clave adaptados a cada producto recomendado para esta cuenta:",
            est["SGS_Cuerpo"],
        ))
        for p in sorted(productos, key=lambda x: -x.get("score_fit", 0))[:5]:
            score = int(p.get("score_fit", 0))
            col_b = VERDE if score >= 80 else (NARANJA if score >= 60 else ROJO_SGS)
            t_arg = Table([
                [
                    Paragraph(
                        f"<b>{p.get('producto', '')}</b> — Score: {score}%",
                        ParagraphStyle("pa", fontSize=9, fontName="Helvetica-Bold", textColor=colors.white),
                    ),
                    Paragraph(
                        p.get("argumentario", "—"),
                        ParagraphStyle("pb", fontSize=8, textColor=NEGRO),
                    ),
                ]
            ], colWidths=[4.5*cm, 12*cm])
            t_arg.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), col_b),
                ("BACKGROUND", (1, 0), (1, 0), GRIS_CLARO),
                ("PADDING",    (0, 0), (-1, -1), 7),
                ("VALIGN",     (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW",  (0, 0), (-1, -1), 0.4, GRIS_BORDE),
            ]))
            el.append(t_arg)
            el.append(Spacer(1, 0.1*cm))

    el.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    # 7. ROI Y PROYECCIÓN DE VALOR
    # ════════════════════════════════════════════════════════════════
    el.append(Paragraph("7. ROI y Proyección de Valor Comercial", est["SGS_Seccion"]))
    el.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDE))
    el.append(Spacer(1, 0.3*cm))

    meses_med = max(int(esc_med.get("plazo_meses") or 12), 1)
    meses_pes = max(int(esc_pes.get("plazo_meses") or 18), 1)
    meses_opt = max(int(esc_opt.get("plazo_meses") or 9), 1)
    pond_pes  = importe_pes * esc_pes.get("probabilidad", 0) / 100
    pond_med  = importe_med * esc_med.get("probabilidad", 0) / 100
    pond_opt  = importe_opt * esc_opt.get("probabilidad", 0) / 100
    val_anual_med = importe_med / meses_med * 12

    el.append(Paragraph(
        f"La siguiente tabla cuantifica el valor esperado del acuerdo comercial con {nombre} "
        f"bajo cada escenario de cierre, integrando probabilidad, plazo y valor anualizado estimado. "
        f"El escenario recomendado proyecta un ingreso esperado (ponderado) de "
        f"<b>{pond_med:,.0f} €</b> con un ciclo de venta de <b>{meses_med} meses</b>.",
        est["SGS_Cuerpo"],
    ))
    el.append(Spacer(1, 0.4*cm))

    # Tabla ROI comparada
    roi_header = [
        Paragraph("<b>Métrica</b>", est["SGS_CabIzq"]),
        Paragraph("<b>🔴 Pesimista</b>", est["SGS_Cabecera"]),
        Paragraph("<b>🟡 Recomendado</b>", est["SGS_Cabecera"]),
        Paragraph("<b>🟢 Optimista</b>", est["SGS_Cabecera"]),
    ]
    roi_filas = [roi_header,
        ["Importe bruto estimado",
         f"{importe_pes:,.0f} €", f"{importe_med:,.0f} €", f"{importe_opt:,.0f} €"],
        ["Probabilidad de cierre",
         f"{esc_pes.get('probabilidad', 0)}%", f"{esc_med.get('probabilidad', 0)}%", f"{esc_opt.get('probabilidad', 0)}%"],
        ["Plazo de ciclo de venta",
         f"{meses_pes} meses", f"{meses_med} meses", f"{meses_opt} meses"],
        [Paragraph("<b>Ingreso esperado ponderado</b>", est["SGS_Cuerpo"]),
         Paragraph(f"<b>{pond_pes:,.0f} €</b>", ParagraphStyle("pp", fontSize=9, fontName="Helvetica-Bold", textColor=ROJO_SGS, alignment=1)),
         Paragraph(f"<b>{pond_med:,.0f} €</b>", ParagraphStyle("pm", fontSize=9, fontName="Helvetica-Bold", textColor=NARANJA, alignment=1)),
         Paragraph(f"<b>{pond_opt:,.0f} €</b>", ParagraphStyle("po", fontSize=9, fontName="Helvetica-Bold", textColor=VERDE, alignment=1))],
        ["Valor anualizado estimado",
         f"{importe_pes / meses_pes * 12:,.0f} €/año",
         f"{val_anual_med:,.0f} €/año",
         f"{importe_opt / meses_opt * 12:,.0f} €/año"],
    ]
    t_roi = Table(roi_filas, colWidths=[5.5*cm, 3.3*cm, 4.0*cm, 3.8*cm], repeatRows=1)
    t_roi.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), ROJO_SGS),
        ("BACKGROUND",  (1, 1), (1, -1), colors.Color(1.0, 0.94, 0.94)),
        ("BACKGROUND",  (2, 1), (2, -1), colors.Color(1.0, 0.97, 0.88)),
        ("BACKGROUND",  (3, 1), (3, -1), colors.Color(0.90, 0.98, 0.90)),
        ("BACKGROUND",  (1, 4), (3, 4), colors.Color(0.97, 0.97, 0.97)),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",    (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("GRID",        (0, 0), (-1, -1), 0.35, GRIS_BORDE),
        ("PADDING",     (0, 0), (-1, -1), 6),
        ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]))
    el.append(t_roi)
    el.append(Spacer(1, 0.5*cm))

    # Gráfica de ingreso ponderado
    el.append(Paragraph("7.1 Comparativa de Ingreso Esperado por Escenario", est["SGS_Subseccion"]))
    el.append(Paragraph(
        "El ingreso esperado ponderado representa la esperanza matemática de ingreso real: "
        "importe estimado × probabilidad de cierre. Es el indicador más fiable para priorización comercial.",
        est["SGS_Cuerpo"],
    ))
    el.append(Spacer(1, 0.2*cm))
    el.append(_grafica_barras_escenarios(pond_pes, pond_med, pond_opt))
    el.append(Spacer(1, 0.3*cm))

    # Cajas de insight de valor
    valor_insights = [
        (f"El acuerdo representa <b>{val_anual_med:,.0f} € anualizados</b> de valor potencial "
         f"en el escenario recomendado, con un ciclo de {meses_med} meses.",
         AZUL_CLARO, AZUL_OSCURO),
        (f"La concentración del pipeline activo ({total_pipeline:,.0f} €) refuerza la viabilidad "
         f"del cierre. Tasa de conversión implícita: {esc_med.get('probabilidad', 0)}%.",
         VERDE_CLARO, VERDE),
    ]
    for txt, c_bg, c_txt in valor_insights:
        el.append(_caja_destacada(txt, c_bg, c_txt))
        el.append(Spacer(1, 0.2*cm))

    el.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    # 8. ANÁLISIS DE CROSS-SELLING
    # ════════════════════════════════════════════════════════════════
    el.append(Paragraph("8. Análisis de Cross-Selling y Brechas de Certificación", est["SGS_Seccion"]))
    el.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDE))
    el.append(Spacer(1, 0.3*cm))

    el.append(Paragraph(
        f"El análisis de inteligencia comercial ha identificado oportunidades de venta cruzada "
        f"para {nombre} basadas en las necesidades detectadas, las brechas de certificación existentes "
        f"y las líneas de negocio SGS con mayor potencial de entrada.",
        est["SGS_Cuerpo"],
    ))
    el.append(Spacer(1, 0.3*cm))

    # Oportunidades de cross-selling desde oport_ia
    if oport_ia and isinstance(oport_ia, list) and len(oport_ia) > 0:
        el.append(Paragraph("8.1 Oportunidades de Negocio Identificadas por IA", est["SGS_Subseccion"]))
        op_filas_cs = [[
            Paragraph("<b>#</b>", est["SGS_Cabecera"]),
            Paragraph("<b>Oportunidad de cross-selling</b>", est["SGS_CabIzq"]),
            Paragraph("<b>Potencial</b>", est["SGS_Cabecera"]),
        ]]
        for i, o in enumerate(oport_ia[:8], 1):
            pot = "Alto" if i <= 3 else ("Medio" if i <= 6 else "Bajo")
            c_pot = VERDE if pot == "Alto" else (NARANJA if pot == "Medio" else GRIS_MEDIO)
            op_filas_cs.append([
                str(i),
                str(o) if isinstance(o, str) else str(o),
                Paragraph(f"<b>{pot}</b>", ParagraphStyle(f"cp{i}", fontSize=8, textColor=c_pot,
                          fontName="Helvetica-Bold", alignment=1)),
            ])
        el.append(_tabla(op_filas_cs, [0.8*cm, 13.5*cm, 2.3*cm]))
        el.append(Spacer(1, 0.4*cm))

    # Brechas de certificación
    el.append(Paragraph("8.2 Análisis de Brechas de Certificación", est["SGS_Subseccion"]))
    el.append(Paragraph(
        "Las brechas de certificación representan las áreas donde la empresa no cuenta con "
        "certificaciones SGS activas, lo que genera oportunidades directas de entrada comercial:",
        est["SGS_Cuerpo"],
    ))
    el.append(Spacer(1, 0.2*cm))

    # Productos recomendados vs certificaciones actuales
    prods_recomendados = sorted(productos, key=lambda x: -x.get("score_fit", 0))[:6]
    brechas_filas = [[
        Paragraph("<b>Producto / Certificación SGS</b>", est["SGS_CabIzq"]),
        Paragraph("<b>Score fit</b>", est["SGS_Cabecera"]),
        Paragraph("<b>Estado actual</b>", est["SGS_Cabecera"]),
        Paragraph("<b>Acción recomendada</b>", est["SGS_CabIzq"]),
    ]]
    certs_nombres = [str(c).lower() for c in certs] if certs else []
    for prod in prods_recomendados:
        nombre_prod = str(prod.get("producto", ""))
        score_p     = int(prod.get("score_fit", 0))
        tiene_cert  = any(nombre_prod.lower()[:10] in c for c in certs_nombres)
        estado      = "Activa" if tiene_cert else "Sin certificación"
        c_estado    = VERDE if tiene_cert else ROJO_SGS
        accion      = ("Renovar / ampliar alcance" if tiene_cert else "Iniciar proceso de certificación")
        brechas_filas.append([
            nombre_prod[:45],
            Paragraph(f"<b>{score_p}%</b>", ParagraphStyle(f"bs{score_p}", fontSize=9,
                      textColor=VERDE if score_p >= 80 else (NARANJA if score_p >= 60 else ROJO_SGS),
                      fontName="Helvetica-Bold", alignment=1)),
            Paragraph(f"<b>{estado}</b>", ParagraphStyle(f"est_{score_p}", fontSize=8,
                      textColor=c_estado, fontName="Helvetica-Bold", alignment=1)),
            accion,
        ])
    el.append(_tabla(brechas_filas, [5.5*cm, 2.0*cm, 3.5*cm, 5.6*cm]))

    el.append(Spacer(1, 0.4*cm))
    el.append(_caja_destacada(
        f"<b>Resumen:</b> {len([p for p in prods_recomendados if p.get('score_fit', 0) >= 70])} de {len(prods_recomendados)} "
        f"productos recomendados tienen score ≥ 70%, lo que indica un potencial de cross-selling "
        f"superior a la media del sector. La prioridad debe ser iniciar con el producto de mayor score de fit.",
        AZUL_CLARO, AZUL_OSCURO,
    ))

    el.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    # 9. HOJA DE RUTA EJECUTIVA
    # ════════════════════════════════════════════════════════════════
    el.append(Paragraph("9. Hoja de Ruta Ejecutiva", est["SGS_Seccion"]))
    el.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDE))
    el.append(Spacer(1, 0.3*cm))

    el.append(Paragraph(
        f"La siguiente hoja de ruta resume las fases de ejecución del plan comercial con {nombre}, "
        f"desde la acción inicial hasta el cierre del acuerdo. Cada fase incluye los entregables "
        f"clave y los hitos de seguimiento recomendados.",
        est["SGS_Cuerpo"],
    ))
    el.append(Spacer(1, 0.4*cm))

    # Fases de la hoja de ruta
    fases = [
        ("Fase 1 — Apertura", "Semana 1–2", ROJO_SGS,
         plan[0].get("accion", "Contacto inicial") if plan else "Contacto inicial con decisor",
         "Presentar propuesta · Validar necesidades · Calificar decisores"),
        ("Fase 2 — Propuesta", "Semana 2–4", NARANJA,
         plan[1].get("accion", "Propuesta formal") if len(plan) > 1 else "Propuesta técnica y económica",
         "Propuesta formal · Demostración técnica · Resolución de objeciones"),
        ("Fase 3 — Negociación", "Mes 1–2", AZUL,
         plan[2].get("accion", "Negociación") if len(plan) > 2 else "Negociación de condiciones y pricing",
         "Negociación precio · Condiciones SLA · Ajuste de alcance"),
        ("Fase 4 — Cierre", f"Mes {meses_med}", VERDE,
         "Firma del acuerdo comercial y arranque de onboarding SGS",
         "Contrato firmado · Kick-off proyecto · Onboarding SGS · KPIs definidos"),
    ]
    for fase, plazo, color, accion, entregables in fases:
        bloque_fase = Table([
            [
                Paragraph(f"<b>{fase}</b>", ParagraphStyle("ff", fontSize=10, fontName="Helvetica-Bold",
                          textColor=colors.white)),
                Paragraph(f"<b>{plazo}</b>", ParagraphStyle("fp", fontSize=9, fontName="Helvetica-Bold",
                          textColor=colors.white, alignment=2)),
            ],
            [
                Paragraph(accion[:80], ParagraphStyle("fa", fontSize=9, textColor=colors.Color(0.15, 0.15, 0.15))),
                "",
            ],
            [
                Paragraph(f"<font color='#555555'>Entregables:</font> {entregables}",
                         ParagraphStyle("fe", fontSize=8, textColor=colors.Color(0.35, 0.35, 0.35))),
                "",
            ],
        ], colWidths=[12*cm, 4.6*cm])
        bloque_fase.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), color),
            ("BACKGROUND",  (0, 1), (-1, 2), GRIS_CLARO),
            ("SPAN",        (0, 1), (1, 1)),
            ("SPAN",        (0, 2), (1, 2)),
            ("PADDING",     (0, 0), (-1, -1), 7),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ("BOX",         (0, 0), (-1, -1), 0.5, GRIS_BORDE),
            ("LINEBELOW",   (0, 0), (-1, 0), 0.5, colors.white),
        ]))
        el.append(bloque_fase)
        el.append(Spacer(1, 0.3*cm))

    el.append(Spacer(1, 0.3*cm))

    # Indicadores de seguimiento
    el.append(Paragraph("9.1 Indicadores Clave de Seguimiento (KPIs de Proceso)", est["SGS_Subseccion"]))
    el.append(Paragraph(
        "Para asegurar el progreso del ciclo de venta, se recomienda hacer seguimiento de los "
        "siguientes indicadores en cada revisión de pipeline:",
        est["SGS_Cuerpo"],
    ))
    el.append(Spacer(1, 0.2*cm))

    kpi_seguimiento = [
        [Paragraph("<b>KPI</b>", est["SGS_CabIzq"]),
         Paragraph("<b>Objetivo</b>", est["SGS_Cabecera"]),
         Paragraph("<b>Frecuencia</b>", est["SGS_Cabecera"]),
         Paragraph("<b>Responsable</b>", est["SGS_Cabecera"])],
        ["Reuniones celebradas con decisores", "≥ 2 / mes", "Semanal", "Comercial asignado"],
        ["Propuestas enviadas y revisadas", "≥ 1 formal enviada", "Quincenal", "Comercial + Manager"],
        ["Avance de etapa en CRM", f"Cerrar en {meses_med} meses", "Mensual", "Manager comercial"],
        ["Probabilidad de cierre actualizada", f"≥ {esc_med.get('probabilidad', 0)}%", "Mensual", "Comercial asignado"],
        ["Feedback del cliente recogido", "Respuesta documentada", "Post-reunión", "Comercial asignado"],
    ]
    el.append(_tabla(kpi_seguimiento, [6.5*cm, 3.5*cm, 2.5*cm, 4.1*cm]))

    el.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    # 10. CONCLUSIONES Y RECOMENDACIONES (renumerado)
    # ════════════════════════════════════════════════════════════════
    el.append(Paragraph("10. Conclusiones y Recomendaciones", est["SGS_Seccion"]))
    el.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDE))
    el.append(Spacer(1, 0.3*cm))

    el.append(Paragraph(
        f"A la vista del análisis de inteligencia comercial realizado sobre {nombre}, "
        f"el sistema IC de SGS España formula las siguientes conclusiones estratégicas:",
        est["SGS_Cuerpo"],
    ))
    el.append(Spacer(1, 0.3*cm))

    mejor_producto_final = max(productos, key=lambda p: p.get("score_fit", 0), default={})
    accion_0_final = plan[0].get("accion", "Contactar con el cliente") if plan else "Contactar con el cliente"

    conclusiones_final = [
        (
            "Potencial comercial confirmado",
            f"La cuenta {nombre} presenta {total_ops} oportunidades activas en pipeline "
            f"por un valor total de {total_pipeline:,.0f} €. El escenario comercial recomendado "
            f"proyecta un cierre de {importe_med:,.0f} € con probabilidad del {esc_med.get('probabilidad', 0)}%.",
        ),
        (
            "Producto prioritario de entrada",
            f"El producto '{mejor_producto_final.get('producto', '—')}' obtiene el mayor score de fit "
            f"({mejor_producto_final.get('score_fit', 0)}%) y debe ser el punto de entrada comercial. "
            f"Permite abrir la conversación y posteriormente ampliar con otras soluciones SGS.",
        ),
        (
            "Necesidades identificadas como palanca",
            f"Se han identificado {len(pain)} necesidades críticas que deben ser el eje del discurso comercial. "
            f"El argumentario generado proporciona los mensajes clave adaptados a cada una de ellas.",
        ),
        (
            "Cross-selling y brechas certificación",
            f"El análisis de brechas detecta oportunidades de venta cruzada en {len(prods_recomendados)} "
            f"líneas de negocio SGS. La estrategia recomendada es entrada por el producto de mayor fit "
            f"y expansión progresiva hacia los de media-alta afinidad.",
        ),
        (
            "Plan de acción inmediata",
            f"La acción prioritaria es: «{accion_0_final}». "
            f"Se recomienda ejecutarla en los próximos {plan[0].get('plazo_dias', 30) if plan else 30} días "
            f"para no perder el momentum identificado en el análisis.",
        ),
        (
            "Horizonte temporal",
            f"El escenario medio estima un plazo de {esc_med.get('plazo_meses', '?')} meses "
            f"para el cierre comercial. El ingreso esperado ponderado asciende a {pond_med:,.0f} €, "
            f"equivalente a {val_anual_med:,.0f} €/año anualizados.",
        ),
    ]

    for i, (titulo, texto) in enumerate(conclusiones_final, 1):
        bloque = Table([
            [
                Paragraph(f"<b>{i}</b>",
                    ParagraphStyle(f"cn{i}", fontSize=14, fontName="Helvetica-Bold",
                                   textColor=colors.white, alignment=1)),
                Paragraph(f"<b>{titulo}:</b> {texto}",
                    ParagraphStyle(f"ct{i}", fontSize=9, textColor=NEGRO, leading=13)),
            ]
        ], colWidths=[0.85*cm, 15.7*cm])
        bloque.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), ROJO_SGS),
            ("BACKGROUND", (1, 0), (1, 0), GRIS_CLARO if i % 2 == 0 else colors.white),
            ("PADDING",    (0, 0), (-1, -1), 8),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("BOX",        (0, 0), (-1, -1), 0.4, GRIS_BORDE),
        ]))
        el.append(bloque)
        el.append(Spacer(1, 0.2*cm))

    el.append(Spacer(1, 0.5*cm))
    el.append(HRFlowable(width="100%", thickness=1.5, color=ROJO_SGS))
    el.append(Spacer(1, 0.4*cm))

    # Caja call-to-action final
    el.append(_caja_destacada(
        f"<b>CALL TO ACTION:</b> La acción inmediata acordada es «{accion_0_final}». "
        f"Plazo de ejecución: {plan[0].get('plazo_dias', 30) if plan else 30} días. "
        f"Objetivo: avanzar hacia escenario recomendado ({importe_med:,.0f} €, {esc_med.get('probabilidad', 0)}% probabilidad).",
        ROJO_SGS, colors.white,
    ))
    el.append(Spacer(1, 0.4*cm))
    el.append(Paragraph(
        f"Documento generado por el Sistema IC de SGS España · "
        f"{date.today().strftime('%d de %B de %Y')} · Confidencial · No distribuir.",
        est["SGS_Pie"],
    ))

    # ── Build ─────────────────────────────────────────────────────────────────
    nombre_archivo = f"propuesta_{str(cuenta_id)[:8]}_{date.today().isoformat()}.pdf"
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.8*cm,
        leftMargin=1.8*cm,
        topMargin=2.0*cm,
        bottomMargin=1.2*cm,
    )
    doc.build(
        el,
        onFirstPage=lambda c, d: _header_footer(c, d, nombre),
        onLaterPages=lambda c, d: _header_footer(c, d, nombre),
    )
    return buffer.getvalue(), nombre_archivo
