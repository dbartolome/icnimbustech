"""
Endpoints del módulo Pipeline.
"""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual, requerir_rol
from app.database import obtener_conexion
from app.modules.ia.servicio import ConfigIA, llamar_ia
from app.modules.pipeline import servicio
from app.modules.importacion.servicio import LINEAS_NEGOCIO_VALIDAS, CANALES_VENTA_VALIDOS
from app.shared.modelos import OportunidadActualizar, OportunidadCrear

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("")
async def listar(
    propietario_id: UUID | None = Query(default=None),
    etapa: str | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=50, ge=1, le=200),
    sort_by: str = Query(default="fecha_creacion"),
    sort_dir: str = Query(default="desc"),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion=Depends(obtener_conexion),
):
    propietario_filtro = UUID(usuario.usuario_id) if usuario.es_comercial else propietario_id
    return await servicio.listar_oportunidades(
        conexion,
        propietario_filtro,
        etapa,
        pagina,
        por_pagina,
        sort_by,
        sort_dir,
    )


@router.get("/funnel")
async def funnel(
    propietario_id: UUID | None = Query(default=None),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion=Depends(obtener_conexion),
):
    propietario_filtro = UUID(usuario.usuario_id) if usuario.es_comercial else propietario_id
    return await servicio.obtener_funnel(conexion, propietario_filtro)


@router.get("/{oportunidad_id}")
async def detalle(
    oportunidad_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion=Depends(obtener_conexion),
):
    propietario_scope = UUID(usuario.usuario_id) if usuario.es_comercial else None
    oportunidad = await servicio.obtener_oportunidad(conexion, oportunidad_id, propietario_scope)
    if not oportunidad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidad no encontrada.")
    return oportunidad


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear(
    datos: OportunidadCrear,
    usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager")),
    conexion=Depends(obtener_conexion),
):
    return await servicio.crear_oportunidad(conexion, datos, UUID(usuario.usuario_id))


@router.put("/{oportunidad_id}")
async def actualizar(
    oportunidad_id: UUID,
    datos: OportunidadActualizar,
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager")),
    conexion=Depends(obtener_conexion),
):
    oportunidad = await servicio.actualizar_oportunidad(conexion, oportunidad_id, datos)
    if not oportunidad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidad no encontrada.")
    return oportunidad


@router.delete("/{oportunidad_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar(
    oportunidad_id: UUID,
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin")),
    conexion=Depends(obtener_conexion),
):
    eliminado = await servicio.eliminar_oportunidad(conexion, oportunidad_id)
    if not eliminado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidad no encontrada.")


# =============================================================================
# AI Autocomplete — sugerencia de Business Line y Canal de Venta
# =============================================================================

class SolicitudSugerencia(BaseModel):
    nombre_oportunidad: str
    cuenta: str | None = None
    producto: str | None = None
    sbu: str | None = None


class RespuestaSugerencia(BaseModel):
    linea_negocio: str
    canal_venta: str
    confianza: float
    razonamiento: str


@router.post("/suggest-fields", response_model=RespuestaSugerencia)
async def sugerir_campos(
    datos: SolicitudSugerencia,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """
    Usa Claude para inferir Business Line y Canal de Venta a partir del nombre
    de la oportunidad, cuenta y producto. Devuelve sugerencia con nivel de confianza.
    """
    lineas = sorted(LINEAS_NEGOCIO_VALIDAS)
    canales = sorted(CANALES_VENTA_VALIDOS)

    prompt = f"""Eres un experto en el portfolio comercial de SGS España (certificación, inspección, ensayos, ESG, formación, ciberseguridad).

Dado el siguiente registro de oportunidad comercial, infiere:
1. Business Line — elige EXACTAMENTE uno de: {lineas}
2. Canal de Venta — elige EXACTAMENTE uno de: {canales}
3. Confianza — número entre 0.0 y 1.0
4. Razonamiento — 1 frase breve explicando tu elección

Datos de la oportunidad:
- Nombre: {datos.nombre_oportunidad}
- Cuenta: {datos.cuenta or "No especificada"}
- Producto/servicio: {datos.producto or "No especificado"}
- SBU: {datos.sbu or "No especificada"}

Guía rápida de Business Lines:
- Certification → ISO 9001/14001/45001/27001/50001/22301, sistemas de gestión
- ESG Solutions → huella carbono, sostenibilidad, CSRD, reporting ESG
- Second Party → auditorías de proveedores, supply chain, RBS
- Testing → ensayos de laboratorio, microbiología, materiales
- Inspection → inspecciones reglamentarias, NDT, RIPCI, activos
- Training & Qualification → formación, cursos, SGS Academy
- Product Certification → marcado CE, CPR, certificación de producto
- Customized Assurance → aseguramiento a medida, verificación de declaraciones
- Digital Trust → ISO 27001/27701, ciberseguridad, pentest, TISAX
- Healthcare → farma, GxP, ISO 13485, MDR, dispositivos médicos
- Food & Retail → ISO 22000, FSSC, BRCGS, IFS, alimentación
- Technical Advisory → consultoría técnica, IDI Proyectos, ingeniería
- Government & Sustainability → sector público, concesiones, ESG normativo

Responde ÚNICAMENTE con JSON válido:
{{"linea_negocio": "...", "canal_venta": "...", "confianza": 0.0, "razonamiento": "..."}}"""

    try:
        texto = await llamar_ia(
            mensajes=[{"role": "user", "content": prompt}],
            system="Responde siempre en JSON válido, sin markdown.",
            config=ConfigIA(proveedor="ollama"),
            max_tokens=220,
        )
        texto = texto.strip()
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        resultado = json.loads(texto.strip())

        # Validar que los valores devueltos son válidos
        linea = resultado.get("linea_negocio", "")
        canal = resultado.get("canal_venta", "Directo")
        if linea not in LINEAS_NEGOCIO_VALIDAS:
            linea = "Certification"
        if canal not in CANALES_VENTA_VALIDOS:
            canal = "Directo"

        return RespuestaSugerencia(
            linea_negocio=linea,
            canal_venta=canal,
            confianza=float(resultado.get("confianza", 0.5)),
            razonamiento=resultado.get("razonamiento", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar sugerencia: {str(e)}")
