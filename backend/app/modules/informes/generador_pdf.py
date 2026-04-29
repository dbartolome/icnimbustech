"""
Generador de PDF con ReportLab para informes SGS España.
Diseño corporativo: portada roja, páginas blancas con banda roja, watermark confidencial.
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import HRFlowable

# =============================================================================
# Colores corporativos SGS
# =============================================================================

SGS_ROJO = colors.HexColor("#C0001A")
SGS_NEGRO = colors.HexColor("#1A1A1A")
SGS_GRIS_CLARO = colors.HexColor("#F5F5F5")
SGS_GRIS = colors.HexColor("#888888")
BLANCO = colors.white

ANCHO, ALTO = A4
MARGEN = 2 * cm

# =============================================================================
# Estilos de párrafo
# =============================================================================

def _estilos() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo_portada": ParagraphStyle(
            "titulo_portada",
            fontName="Helvetica-Bold",
            fontSize=26,
            textColor=BLANCO,
            alignment=TA_LEFT,
            leading=32,
        ),
        "subtitulo_portada": ParagraphStyle(
            "subtitulo_portada",
            fontName="Helvetica",
            fontSize=14,
            textColor=BLANCO,
            alignment=TA_LEFT,
            leading=20,
        ),
        "meta_portada": ParagraphStyle(
            "meta_portada",
            fontName="Helvetica",
            fontSize=11,
            textColor=colors.HexColor("#FFCCCC"),
            alignment=TA_LEFT,
            leading=16,
        ),
        "titulo_seccion": ParagraphStyle(
            "titulo_seccion",
            fontName="Helvetica-Bold",
            fontSize=15,
            textColor=SGS_ROJO,
            spaceBefore=14,
            spaceAfter=6,
            leading=20,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo",
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=SGS_NEGRO,
            spaceBefore=10,
            spaceAfter=4,
            leading=16,
        ),
        "cuerpo": ParagraphStyle(
            "cuerpo",
            fontName="Helvetica",
            fontSize=10,
            textColor=SGS_NEGRO,
            spaceAfter=6,
            leading=14,
            alignment=TA_LEFT,
        ),
        "pie": ParagraphStyle(
            "pie",
            fontName="Helvetica",
            fontSize=8,
            textColor=SGS_GRIS,
            alignment=TA_CENTER,
        ),
        "numero_pagina": ParagraphStyle(
            "numero_pagina",
            fontName="Helvetica",
            fontSize=8,
            textColor=SGS_GRIS,
            alignment=TA_RIGHT,
        ),
    }


# =============================================================================
# Watermark + decoración de páginas
# =============================================================================

def _dibujar_portada(canvas, doc):
    canvas.saveState()
    # Fondo rojo completo
    canvas.setFillColor(SGS_ROJO)
    canvas.rect(0, 0, ANCHO, ALTO, fill=True, stroke=False)
    # Banda blanca inferior decorativa
    canvas.setFillColor(BLANCO)
    canvas.setFillAlpha(0.08)
    canvas.rect(0, 0, ANCHO, 4 * cm, fill=True, stroke=False)
    canvas.setFillAlpha(1)
    # Texto SGS en esquina superior derecha (logo)
    canvas.setFillColor(BLANCO)
    canvas.setFont("Helvetica-Bold", 28)
    canvas.drawRightString(ANCHO - MARGEN, ALTO - 1.5 * cm, "SGS")
    canvas.setFont("Helvetica", 10)
    canvas.drawRightString(ANCHO - MARGEN, ALTO - 2.1 * cm, "When You Need To Be Sure")
    canvas.restoreState()


def _dibujar_interior(canvas, doc):
    canvas.saveState()
    # Banda lateral roja izquierda
    canvas.setFillColor(SGS_ROJO)
    canvas.rect(0, 0, 0.6 * cm, ALTO, fill=True, stroke=False)
    # Logo SGS derecha
    canvas.setFillColor(SGS_ROJO)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawRightString(ANCHO - MARGEN, ALTO - 1.2 * cm, "SGS")
    # Línea divisoria superior
    canvas.setStrokeColor(SGS_GRIS_CLARO)
    canvas.setLineWidth(0.5)
    canvas.line(MARGEN + 0.6 * cm, ALTO - 1.8 * cm, ANCHO - MARGEN, ALTO - 1.8 * cm)
    # Pie de página
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(SGS_GRIS)
    pie_texto = f"SGS España Intelligence · Generado el {datetime.now().strftime('%d/%m/%Y')} · CONFIDENCIAL"
    canvas.drawCentredString(ANCHO / 2, 0.8 * cm, pie_texto)
    # Número de página
    canvas.drawRightString(ANCHO - MARGEN, 0.8 * cm, f"Pág. {canvas.getPageNumber() - 1}")
    # Watermark diagonal
    canvas.saveState()
    canvas.setFillColor(SGS_GRIS_CLARO)
    canvas.setFont("Helvetica-Bold", 48)
    canvas.translate(ANCHO / 2, ALTO / 2)
    canvas.rotate(45)
    canvas.setFillAlpha(0.06)
    canvas.drawCentredString(0, 0, "CONFIDENCIAL")
    canvas.restoreState()
    canvas.restoreState()


# =============================================================================
# Función principal: generar PDF en memoria
# =============================================================================

def generar_pdf(
    titulo: str,
    tipo_label: str,
    comercial: str,
    periodo: str | None,
    secciones: list[dict],  # [{"titulo": str, "contenido": str}]
    kpis: dict | None = None,
) -> bytes:
    """
    Genera el PDF completo en memoria y devuelve bytes.
    secciones: lista de dicts con 'titulo' y 'contenido'
    kpis: dict con métricas opcionales para la portada
    """
    buf = io.BytesIO()
    estilos = _estilos()

    # ── Templates de página ──────────────────────────────────────────────────
    frame_portada = Frame(
        MARGEN, MARGEN, ANCHO - 2 * MARGEN, ALTO - 2 * MARGEN,
        id="portada", showBoundary=False,
    )
    frame_interior = Frame(
        MARGEN + 0.8 * cm, 1.8 * cm,
        ANCHO - 2 * MARGEN - 0.8 * cm, ALTO - 3.5 * cm,
        id="interior", showBoundary=False,
    )

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGEN,
        rightMargin=MARGEN,
        topMargin=MARGEN,
        bottomMargin=MARGEN,
        title=titulo,
        author="SGS España Intelligence",
    )

    doc.addPageTemplates([
        PageTemplate(id="portada", frames=[frame_portada], onPage=_dibujar_portada),
        PageTemplate(id="interior", frames=[frame_interior], onPage=_dibujar_interior),
    ])

    # ── Contenido ────────────────────────────────────────────────────────────
    story = []

    # Portada
    story.append(Spacer(1, 6 * cm))
    story.append(Paragraph(tipo_label.upper(), estilos["meta_portada"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(titulo, estilos["titulo_portada"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(f"Preparado para: {comercial}", estilos["subtitulo_portada"]))
    if periodo:
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(f"Periodo: {periodo}", estilos["meta_portada"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(f"Fecha: {datetime.now().strftime('%d de %B de %Y')}", estilos["meta_portada"]))

    # KPIs en portada (tabla 2 col)
    if kpis:
        story.append(Spacer(1, 1.5 * cm))
        kpi_data = [[k, v] for k, v in kpis.items()]
        t = Table(kpi_data, colWidths=[9 * cm, 5 * cm])
        t.setStyle(TableStyle([
            ("TEXTCOLOR", (0, 0), (-1, -1), BLANCO),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#A0001488"), colors.HexColor("#80001488")]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t)

    # Cambiar a template interior
    story.append(NextPageTemplate("interior"))
    story.append(PageBreak())

    # Secciones de contenido
    for seccion in secciones:
        story.append(Paragraph(seccion["titulo"], estilos["titulo_seccion"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=SGS_ROJO, spaceAfter=8))

        # Dividir el contenido en párrafos por saltos de línea
        for linea in seccion["contenido"].split("\n"):
            linea = linea.strip()
            if not linea:
                story.append(Spacer(1, 4))
                continue
            if linea.startswith("**") and linea.endswith("**"):
                story.append(Paragraph(linea[2:-2], estilos["subtitulo"]))
            else:
                story.append(Paragraph(linea, estilos["cuerpo"]))

        story.append(Spacer(1, 0.5 * cm))

    doc.build(story)
    buf.seek(0)
    return buf.read()
