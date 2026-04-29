"""
Skill: extraer_texto

Extrae texto legible de documentos subidos (PDF, DOCX, TXT, CSV).
Usa PyMuPDF (fitz) para PDF/DOCX. Solo información de archivo local — sin red.
"""

from pathlib import Path

MAX_CHARS = 24_000  # ~6k tokens — suficiente para contexto de chat


def extraer_texto(contenido: bytes, nombre: str, mime_type: str | None = None) -> str:
    """
    Devuelve el texto plano extraído del documento.
    Devuelve "" si el tipo no es soportado o falla la extracción.
    """
    ext = Path(nombre).suffix.lower()

    # PDF
    if ext == ".pdf" or (mime_type and "pdf" in mime_type):
        return _fitz(contenido, "pdf")

    # DOCX / DOC — MuPDF soporta DOCX desde v1.23
    if ext in (".docx", ".doc"):
        return _fitz(contenido, "docx")

    # Texto plano, CSV, Markdown
    if ext in (".txt", ".csv", ".md", ".tsv"):
        try:
            return contenido.decode("utf-8", errors="replace")[:MAX_CHARS]
        except Exception:
            return ""

    return ""


def _fitz(contenido: bytes, filetype: str) -> str:
    try:
        import fitz  # PyMuPDF

        with fitz.open(stream=contenido, filetype=filetype) as doc:
            partes = []
            for pagina in doc:
                texto = pagina.get_text()
                if texto.strip():
                    partes.append(texto)
            return "\n".join(partes)[:MAX_CHARS]
    except Exception:
        return ""
