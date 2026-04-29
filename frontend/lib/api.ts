import { downloadFromApi, getAccessToken, openFromApi, requestJson, requestRaw } from "@/lib/http-client"
import { obtenerApiBaseUrl } from "@/lib/api-base-url"

const OLLAMA_URL_DEFECTO = process.env.NEXT_PUBLIC_OLLAMA_URL ?? ""
const OLLAMA_MODELO_DEFECTO = process.env.NEXT_PUBLIC_OLLAMA_MODEL ?? ""
const PROVEEDOR_DEFECTO = "ollama"

/**
 * Alias semánticos para mantener una API estable mientras se migra
 * el código legado al nuevo cliente HTTP centralizado.
 */
const peticion = requestJson
const peticionRaw = requestRaw

/**
 * Construye una query string ignorando valores nulos/undefined.
 */
function construirQuery(params: Record<string, string | number | boolean | undefined>): string {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      qs.set(key, String(value))
    }
  })
  const serializado = qs.toString()
  return serializado ? `?${serializado}` : ""
}

type ContextoTipo = "cuenta" | "cliente" | "producto" | "oportunidad"
type ContextoGeneracion =
  | string
  | {
      contexto?: string
      contextoTipo?: ContextoTipo
      contextoId?: string
    }

function queryContexto(contexto?: ContextoGeneracion): string {
  if (!contexto) return ""
  if (typeof contexto === "string") return construirQuery({ contexto })
  return construirQuery({
    contexto: contexto.contexto,
    contexto_tipo: contexto.contextoTipo,
    contexto_id: contexto.contextoId,
  })
}

// =============================================================================
// Auth
// =============================================================================

export const api = {
  auth: {
    login: (email: string, contrasena: string) =>
      peticion<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, contrasena }),
      }),
    logout: () =>
      peticion<void>("/auth/logout", { method: "POST" }),
    perfil: () =>
      peticion<{
        usuario_id: string
        email: string
        nombre_completo: string
        rol: string
        sbus_asignados: string[]
        permisos: import("@/types").PermisosUsuario
      }>("/auth/me"),
  },

  // =============================================================================
  // Dashboard
  // =============================================================================
  dashboard: {
    kpis: (incluirFantasmas = true, propietarioId?: string) =>
      peticion<Record<string, number | string>>(
        `/dashboard/kpis${construirQuery({ incluir_fantasmas: incluirFantasmas, propietario_id: propietarioId })}`,
      ),
    evolucion: (incluirFantasmas = true, propietarioId?: string) =>
      peticion<unknown[]>(
        `/dashboard/evolucion${construirQuery({ incluir_fantasmas: incluirFantasmas, propietario_id: propietarioId })}`,
      ),
    sbu: (incluirFantasmas = true, propietarioId?: string) =>
      peticion<unknown[]>(
        `/dashboard/sbu${construirQuery({ incluir_fantasmas: incluirFantasmas, propietario_id: propietarioId })}`,
      ),
  },

  // =============================================================================
  // Pipeline
  // =============================================================================
  pipeline: {
    listar: (
      pagina = 1,
      por_pagina = 50,
      sortBy = "fecha_creacion",
      sortDir: "asc" | "desc" = "desc",
    ) =>
      peticion<unknown>(
        `/pipeline?pagina=${pagina}&por_pagina=${por_pagina}&sort_by=${encodeURIComponent(sortBy)}&sort_dir=${sortDir}`,
      ),
    obtener: (id: string) => peticion<unknown>(`/pipeline/${id}`),
    actualizar: (id: string, datos: Record<string, unknown>) =>
      peticion<unknown>(`/pipeline/${id}`, { method: "PUT", body: JSON.stringify(datos) }),
    eliminar: (id: string) => peticion<void>(`/pipeline/${id}`, { method: "DELETE" }),
    funnel: (propietarioId?: string) =>
      peticion<unknown[]>(`/pipeline/funnel${construirQuery({ propietario_id: propietarioId })}`),
    sugerirCampos: (datos: {
      nombre_oportunidad: string
      cuenta?: string
      producto?: string
      sbu?: string
    }) =>
      peticion<{
        linea_negocio: string
        canal_venta: string
        confianza: number
        razonamiento: string
      }>("/pipeline/suggest-fields", { method: "POST", body: JSON.stringify(datos) }),
  },

  // =============================================================================
  // Equipo
  // =============================================================================
  equipo: {
    ranking: () => peticion<unknown[]>("/equipo/ranking"),
    estadisticas: (id: string) => peticion<unknown>(`/equipo/${id}/estadisticas`),
    pipeline: (id: string) => peticion<unknown[]>(`/equipo/${id}/pipeline`),
  },

  // =============================================================================
  // Productos
  // =============================================================================
  productos: {
    analisis: (params?: { sort_by?: string; sort_dir?: "asc" | "desc" }) => {
      const qs = construirQuery({
        sort_by: params?.sort_by,
        sort_dir: params?.sort_dir,
      })
      return peticion<unknown[]>(`/productos/analisis${qs}`)
    },
    oportunidades: (id: string, limit = 20) =>
      peticion<unknown[]>(`/productos/${id}/oportunidades?limit=${limit}`),
  },

  // =============================================================================
  // IA Copilot
  // =============================================================================
  ia: {
    chatStream: (
      mensajes: Array<{ role: string; content: string }>,
      iaConfig?: { proveedor: string; ollamaUrl: string; ollamaModelo: string },
    ) => {
      const token = getAccessToken()
      const payload: Record<string, unknown> = { mensajes }
      // Si no llega configuración explícita, delegamos en el backend para usar su
      // configuración activa y evitar errores por configuración stale del frontend.
      if (iaConfig) {
        payload.proveedor = iaConfig.proveedor
        payload.ollama_url = iaConfig.ollamaUrl
        payload.ollama_modelo = iaConfig.ollamaModelo
      }
      const apiBaseUrl = obtenerApiBaseUrl()
      return fetch(`${apiBaseUrl}/ia/chat`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      })
    },
    chatStreamCuenta: (
      cuentaId: string,
      mensajes: Array<{ role: string; content: string }>,
      iaConfig?: { proveedor: string; ollamaUrl: string; ollamaModelo: string },
      documentoId?: string | null,
    ) => {
      const token = getAccessToken()
      const payload: Record<string, unknown> = { mensajes }
      if (iaConfig) {
        payload.proveedor = iaConfig.proveedor
        payload.ollama_url = iaConfig.ollamaUrl
        payload.ollama_modelo = iaConfig.ollamaModelo
      }
      if (documentoId) payload.documento_id = documentoId
      const apiBaseUrl = obtenerApiBaseUrl()
      return fetch(`${apiBaseUrl}/ia/chat/${cuentaId}`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      })
    },
    conversaciones: (cuentaId: string, limit = 20) =>
      peticion<Array<{ id: string; rol_usuario: string; num_mensajes: number; preview: string; creado_en: string }>>(
        `/ia/conversaciones/${cuentaId}?limit=${limit}`,
      ),
    obtenerModelosOllama: (ollamaUrl: string) =>
      peticion<{ models: Array<{ name: string; size: number }> }>("/ia/ollama/models", {
        method: "POST",
        body: JSON.stringify({ ollama_url: ollamaUrl }),
      }),
    probarOllama: (ollamaUrl: string, ollamaModelo: string) =>
      peticion<{ ok: boolean; respuesta: string }>("/ia/ollama/test", {
        method: "POST",
        body: JSON.stringify({ ollama_url: ollamaUrl, ollama_modelo: ollamaModelo }),
      }),
    estadoProveedores: () =>
      peticion<{
        research: {
          proveedor_por_defecto_env: string
          proveedor_activo: string
          modelo_por_defecto: string
          externos: Record<string, { configurado: boolean; deep_research_soportado: boolean }>
        }
        operacional: {
          proveedor_fijo: string
          ollama_url_por_defecto: string
          ollama_modelo_por_defecto: string
        }
      }>("/ia/proveedores/estado"),
    obtenerConfigResearch: () =>
      peticion<{
        proveedor_activo: string
        modelo_activo: string
        ollama_url_activa: string
        proveedores: Record<string, { configurado: boolean; deep_research_soportado: boolean; modelo_activo?: string; api_key_runtime?: boolean }>
      }>("/ia/research/config"),
    obtenerConfigOperacional: () =>
      peticion<{
        configs: Record<string, { proveedor: string; ollama_url: string; ollama_modelo: string }>
      }>("/ia/operacional/config"),
    actualizarConfigOperacional: (datos: {
      copilot: { proveedor: string; ollama_url: string; ollama_modelo: string }
      voice: { proveedor: string; ollama_url: string; ollama_modelo: string }
      informes: { proveedor: string; ollama_url: string; ollama_modelo: string }
      decks: { proveedor: string; ollama_url: string; ollama_modelo: string }
      cross_selling: { proveedor: string; ollama_url: string; ollama_modelo: string }
      importacion: { proveedor: string; ollama_url: string; ollama_modelo: string }
    }) =>
      peticion<{ ok: boolean; configs: Record<string, { proveedor: string; ollama_url: string; ollama_modelo: string }> }>(
        "/ia/operacional/config",
        {
          method: "PUT",
          body: JSON.stringify(datos),
        },
      ),
    actualizarConfigResearch: (datos: { proveedor: string; modelo?: string; api_key?: string; ollama_url?: string }) =>
      peticion<{ ok: boolean; proveedor_activo: string; modelo_activo: string }>("/ia/research/config", {
        method: "PUT",
        body: JSON.stringify(datos),
      }),
    probarResearch: (datos: { proveedor: string; modelo?: string; api_key?: string; ollama_url?: string }) =>
      peticion<{ ok: boolean; respuesta: string }>("/ia/research/test", {
        method: "POST",
        body: JSON.stringify(datos),
      }),
  },

  // =============================================================================
  // Voice Studio
  // =============================================================================
  voice: {
    briefing: (foco: string, iaConfig?: { proveedor: string; ollamaUrl: string; ollamaModelo: string }) =>
      peticion<{ script: string; foco: string }>("/voice/briefing", {
        method: "POST",
        body: JSON.stringify({
          foco,
          proveedor: iaConfig?.proveedor ?? PROVEEDOR_DEFECTO,
          ollama_url: iaConfig?.ollamaUrl ?? OLLAMA_URL_DEFECTO,
          ollama_modelo: iaConfig?.ollamaModelo ?? OLLAMA_MODELO_DEFECTO,
        }),
      }),
    briefingCuenta: (cuentaId: string) =>
      peticion<string>(`/voice/briefing/${cuentaId}`, { method: "POST" }),
    generarAudioMp3: (cuentaId: string) =>
      peticion<{ doc_id: string; nombre_fichero: string; tamano_bytes: number }>(
        `/voice/briefing/${cuentaId}/audio`,
        { method: "POST" },
      ),
  },

  // =============================================================================
  // Investigación empresa (IA web search)
  // =============================================================================
  investigacion: {
    iniciar: (cuentaId: string) =>
      peticion<{ estado: string; mensaje: string; investigacion_id?: string }>(
        `/investigacion/${cuentaId}`,
        { method: "POST" },
      ),
    estado: (cuentaId: string) =>
      peticion<{
        id: string; estado: string; sector: string | null; num_empleados: string | null;
        facturacion_estimada: string | null; certificaciones_actuales: string[];
        noticias_relevantes: string[]; pain_points: string[]; oportunidades_detectadas: string[];
        presencia_web: string | null; fuentes: string[]; error_msg: string | null;
        modelo_usado: string | null; iniciado_en: string | null; completado_en: string | null;
      }>(
        `/investigacion/${cuentaId}/estado`,
      ),
  },

  // =============================================================================
  // Propuesta comercial (IA local)
  // =============================================================================
  propuesta: {
    iniciar: (cuentaId: string) =>
      peticion<{ estado: string; mensaje: string; propuesta_id?: string }>(
        `/propuesta/${cuentaId}`,
        { method: "POST" },
      ),
    estado: (cuentaId: string) =>
      peticion<{ propuesta_id: string | null; estado: string; error_msg?: string | null; completado_en?: string | null }>(
        `/propuesta/${cuentaId}/estado`,
      ),
    pipelineCompleto: (cuentaId: string) =>
      peticion<{ estado: string; mensaje: string }>(
        `/propuesta/${cuentaId}/pipeline-completo`,
        { method: "POST" },
      ),
  },

  // =============================================================================
  // Seguimientos
  // =============================================================================
  seguimientos: {
    listar: (params?: { oportunidad_id?: string; cuenta_id?: string; estado?: "pendiente" | "completado" | "cancelado" }) => {
      const query = construirQuery({
        oportunidad_id: params?.oportunidad_id,
        cuenta_id: params?.cuenta_id,
        estado: params?.estado,
      })
      return peticion<{ datos: import("@/types").Seguimiento[] }>(`/seguimientos${query}`)
    },
    crear: (datos: {
      oportunidad_id?: string
      cuenta_id?: string
      tipo?: "recordatorio" | "proximo_paso" | "cadencia"
      titulo: string
      descripcion?: string
      fecha_vencimiento: string
    }) => peticion<import("@/types").Seguimiento>("/seguimientos", {
      method: "POST",
      body: JSON.stringify(datos),
    }),
    completar: (id: string) => peticion<void>(`/seguimientos/${id}/completar`, { method: "PUT" }),
    actualizar: (
      id: string,
      datos: Partial<{
        tipo: "recordatorio" | "proximo_paso" | "cadencia"
        titulo: string
        descripcion: string
        fecha_vencimiento: string
        estado: "pendiente" | "completado" | "cancelado"
      }>,
    ) => peticion<import("@/types").Seguimiento>(`/seguimientos/${id}`, {
      method: "PUT",
      body: JSON.stringify(datos),
    }),
    eliminar: (id: string) => peticion<void>(`/seguimientos/${id}`, { method: "DELETE" }),
  },

  // =============================================================================
  // Scoring
  // =============================================================================
  scoring: {
    obtener: (oportunidadId: string) =>
      peticion<import("@/types").ScoringOportunidad>(`/scoring/${oportunidadId}`),
    criticos: (umbral = 40) =>
      peticion<Array<{
        oportunidad_id: string
        nombre: string
        cuenta_nombre: string | null
        score: number
        etapa: string
        importe: number
      }>>(`/scoring/criticos?umbral=${umbral}`),
    recalcular: () => peticion<{ total_oportunidades: number; recalculadas: number }>("/scoring/recalcular", { method: "POST" }),
  },

  // =============================================================================
  // Reuniones 360
  // =============================================================================
  reuniones: {
    preparar: (cuentaId: string) =>
      peticion<import("@/types").FichaReunion>(`/reuniones/preparar/${cuentaId}`),
    preguntas: (cuentaId: string) =>
      peticion<{ preguntas: string[] }>(`/reuniones/preguntas/${cuentaId}`, { method: "POST" }),
  },

  // =============================================================================
  // Coaching comercial
  // =============================================================================
  coaching: {
    analizarNotas: (cuentaId: string) =>
      peticion<import("@/types").CoachingSesion>(`/coaching/analizar-notas/${cuentaId}`, { method: "POST" }),
    recomendaciones: (usuarioId: string) =>
      peticion<{ focos_semana: string[]; acciones: string[]; metricas_objetivo: Record<string, unknown> }>(
        `/coaching/recomendaciones/${usuarioId}`,
      ),
    equipo: () => peticion<Array<Record<string, unknown>>>("/coaching/equipo"),
    historial: (usuarioId: string) =>
      peticion<import("@/types").CoachingSesion[]>(`/coaching/historial/${usuarioId}`),
  },

  // =============================================================================
  // Calidad IA (validación pre-exportación)
  // =============================================================================
  calidad: {
    validar: (cuentaId: string, tipo: "pdf" | "pptx" | "deck" | "briefing") =>
      peticion<import("@/types").ValidacionCalidad>(`/calidad/validar/${cuentaId}?tipo=${tipo}`),
    historial: (cuentaId: string) =>
      peticion<Array<Record<string, unknown>>>(`/calidad/historial/${cuentaId}`),
    forzar: (cuentaId: string, tipo: "pdf" | "pptx" | "deck" | "briefing", motivo?: string) =>
      peticion<Record<string, unknown>>(`/calidad/forzar/${cuentaId}`, {
        method: "POST",
        body: JSON.stringify({ tipo_entregable: tipo, motivo }),
      }),
  },

  // =============================================================================
  // Alertas
  // =============================================================================
  alertas: {
    listar: (incluirResueltas = false) =>
      peticion<unknown[]>(`/alertas?incluir_resueltas=${incluirResueltas}`),
    crear: (datos: { titulo: string; descripcion?: string; nivel: string }) =>
      peticion<unknown>("/alertas", { method: "POST", body: JSON.stringify(datos) }),
    resolver: (id: string) =>
      peticion<void>(`/alertas/${id}/resolver`, { method: "PUT" }),
    eliminar: (id: string) =>
      peticion<void>(`/alertas/${id}`, { method: "DELETE" }),
  },

  // =============================================================================
  // Informes PDF
  // =============================================================================
  informes: {
    generar: (
      datos: { tipo: string; periodo?: string; destinatario?: string; contexto?: string },
      iaConfig?: { proveedor: string; ollamaUrl: string; ollamaModelo: string },
    ) =>
      peticion<{ job_id: string; estado: string; mensaje: string }>("/informes/generar", {
        method: "POST",
        body: JSON.stringify({
          ...datos,
          proveedor: iaConfig?.proveedor ?? PROVEEDOR_DEFECTO,
          ollama_url: iaConfig?.ollamaUrl ?? OLLAMA_URL_DEFECTO,
          ollama_modelo: iaConfig?.ollamaModelo ?? OLLAMA_MODELO_DEFECTO,
        }),
      }),
    estado: (jobId: string) => peticion<unknown>(`/informes/status/${jobId}`),
    listar: () => peticion<unknown[]>("/informes"),
    descargar: (id: string, titulo: string) => downloadFromApi(`/informes/${id}/descargar`, `${titulo}.pdf`),
    eliminar: (id: string) => peticion<void>(`/informes/${id}`, { method: "DELETE" }),
    pdfCuenta: (cuentaId: string, contexto?: ContextoGeneracion) =>
      downloadFromApi(
        `/informes/cuenta/${cuentaId}/pdf${queryContexto(contexto)}`,
        `propuesta_${cuentaId.slice(0, 8)}.pdf`,
        { method: "POST" },
      ),
    pptxCuenta: (cuentaId: string, contexto?: ContextoGeneracion) =>
      downloadFromApi(
        `/informes/cuenta/${cuentaId}/pptx${queryContexto(contexto)}`,
        `deck_${cuentaId.slice(0, 8)}.pptx`,
        { method: "POST" },
      ),
  },

  // =============================================================================
  // Jobs de documentos de cuenta (PDF, PPTX, Briefing, Estudio IA)
  // =============================================================================
  documentosJobs: {
    generarPdf: (cuentaId: string, contexto?: ContextoGeneracion) =>
      peticion<{ job_id: string; estado: string }>(`/cuentas/${cuentaId}/pdf/generar${queryContexto(contexto)}`, { method: "POST" }),
    generarPptx: (cuentaId: string, contexto?: ContextoGeneracion) =>
      peticion<{ job_id: string; estado: string }>(`/cuentas/${cuentaId}/pptx/generar${queryContexto(contexto)}`, { method: "POST" }),
    generarBriefing: (cuentaId: string, contexto?: ContextoGeneracion) =>
      peticion<{ job_id: string; estado: string }>(`/cuentas/${cuentaId}/briefing/generar${queryContexto(contexto)}`, { method: "POST" }),
    generarEstudioIa: (cuentaId: string) =>
      peticion<{ job_id: string; estado: string }>(`/cuentas/${cuentaId}/estudio-ia/generar`, { method: "POST" }),
    iniciarInvestigacion: (cuentaId: string, forzar = false) =>
      peticion<{ job_id: string | null; estado: string; investigacion_id?: string }>(
        `/cuentas/${cuentaId}/investigacion/iniciar?forzar=${forzar}`,
        { method: "POST" },
      ),
    estado: (jobId: string) =>
      peticion<{
        tipo: string
        titulo: string
        estado: string
        progreso: number
        paso_actual?: string
        url_descarga?: string
        artefacto_id?: string
        resultado?: unknown
        error?: string
      }>(`/cuentas/jobs/${jobId}`),
    obtenerEstudioIa: (cuentaId: string) =>
      peticion<{
        analisis: {
          resumen: string
          oportunidades: Array<{ producto: string; urgencia: "alta" | "media" | "baja" }>
          mensaje: string
          confianza: string
        }
        creado_en: string
      }>(`/cuentas/${cuentaId}/estudio-ia`),
  },

  // =============================================================================
  // Documentos
  // =============================================================================
  documentos: {
    listar: (params?: {
      oportunidad_id?: string
      propietario_id?: string
      busqueda?: string
      pagina?: number
      por_pagina?: number
      sort_by?: string
      sort_dir?: "asc" | "desc"
    }) => {
      const query = construirQuery({
        oportunidad_id: params?.oportunidad_id,
        propietario_id: params?.propietario_id,
        busqueda: params?.busqueda,
        pagina: params?.pagina,
        por_pagina: params?.por_pagina,
        sort_by: params?.sort_by,
        sort_dir: params?.sort_dir,
      })
      return peticion<{ total: number; pagina: number; por_pagina: number; datos: unknown[] }>(`/documentos${query}`)
    },
    subir: async (archivo: File, oportunidad_id?: string, cuenta_id?: string) => {
      const form = new FormData()
      form.append("archivo", archivo)
      if (oportunidad_id) form.append("oportunidad_id", oportunidad_id)
      if (cuenta_id) form.append("cuenta_id", cuenta_id)
      const response = await peticionRaw("/documentos/subir", {
        method: "POST",
        body: form,
      })
      return response.json()
    },
    descargar: (id: string, nombreOriginal: string) => downloadFromApi(`/documentos/${id}/descargar`, nombreOriginal),
    abrir: (id: string) => openFromApi(`/documentos/${id}/descargar`),
    blob: async (id: string): Promise<Blob> => {
      const r = await peticionRaw(`/documentos/${id}/descargar`)
      return r.blob()
    },
    slides: (id: string) =>
      peticion<{ total: number; slides: Array<{ index: number; titulo: string; cuerpo: string; notas: string }> }>(
        `/documentos/${id}/slides`,
      ),
    eliminar: (id: string) => peticion<void>(`/documentos/${id}`, { method: "DELETE" }),
    compartir: (id: string, dias = 7) =>
      peticion<{ token: string; expira_en: string }>(`/documentos/${id}/compartir?dias=${dias}`, { method: "POST" }),
    transcribir: (id: string) =>
      peticion<{ id: string; transcripcion: string }>(`/documentos/${id}/transcribir`, { method: "POST" }),
    transcripcion: (id: string) =>
      peticion<{ id: string; transcripcion: string }>(`/documentos/${id}/transcripcion`),
  },

  // =============================================================================
  // Notas de Voz
  // =============================================================================
  notas: {
    listar: (params?: { oportunidad_id?: string; busqueda?: string; pagina?: number }) => {
      const query = construirQuery({
        oportunidad_id: params?.oportunidad_id,
        busqueda: params?.busqueda,
        pagina: params?.pagina,
      })
      return peticion<{ total: number; pagina: number; por_pagina: number; datos: unknown[] }>(`/notas${query}`)
    },
    crear: (datos: { titulo: string; transcripcion: string; duracion_seg?: number; oportunidad_id?: string }) =>
      peticion<unknown>("/notas", { method: "POST", body: JSON.stringify(datos) }),
    subirAudio: async (archivo: File, datos?: { titulo?: string; oportunidad_id?: string }) => {
      const form = new FormData()
      form.append("archivo", archivo)
      if (datos?.titulo) form.append("titulo", datos.titulo)
      if (datos?.oportunidad_id) form.append("oportunidad_id", datos.oportunidad_id)
      const response = await peticionRaw("/notas/transcribir-audio", {
        method: "POST",
        body: form,
      })
      return response.json()
    },
    eliminar: (id: string) =>
      peticion<void>(`/notas/${id}`, { method: "DELETE" }),
  },

  // =============================================================================
  // Clientes — vista global (manager/admin)
  // =============================================================================
  clientes: {
    listar: (params?: {
      busqueda?: string
      propietario_id?: string
      pagina?: number
      por_pagina?: number
      sort_by?: string
      sort_dir?: "asc" | "desc"
    }) => {
      const query = construirQuery({
        busqueda: params?.busqueda,
        propietario_id: params?.propietario_id,
        pagina: params?.pagina,
        por_pagina: params?.por_pagina,
        sort_by: params?.sort_by,
        sort_dir: params?.sort_dir,
      })
      return peticion<{ total: number; pagina: number; por_pagina: number; datos: unknown[] }>(`/cuentas/global${query}`)
    },
    obtener: (id: string, propietarioId?: string) =>
      peticion<unknown>(`/cuentas/global/${id}${construirQuery({ propietario_id: propietarioId })}`),
  },

  // =============================================================================
  // Mis Cuentas
  // =============================================================================
  cuentas: {
    catalogo: (busqueda?: string) => {
      const qs = busqueda ? `?busqueda=${encodeURIComponent(busqueda)}` : ""
      return peticion<Array<{ id: string; nombre: string }>>(`/cuentas/catalogo${qs}`)
    },
    listar: (params?: {
      busqueda?: string
      propietario_id?: string
      pagina?: number
      por_pagina?: number
      sort_by?: string
      sort_dir?: "asc" | "desc"
    }) => {
      const query = construirQuery({
        busqueda: params?.busqueda,
        propietario_id: params?.propietario_id,
        pagina: params?.pagina,
        por_pagina: params?.por_pagina,
        sort_by: params?.sort_by,
        sort_dir: params?.sort_dir,
      })
      return peticion<{ total: number; pagina: number; por_pagina: number; datos: unknown[] }>(`/cuentas${query}`)
    },
    obtener: (id: string, propietarioId?: string) =>
      peticion<unknown>(`/cuentas/${id}${construirQuery({ propietario_id: propietarioId })}`),
  },

  // =============================================================================
  // Usuarios (admin)
  // =============================================================================
  usuarios: {
    listar: (params?: { rol?: string; busqueda?: string; pagina?: number }) => {
      const query = construirQuery({
        rol: params?.rol,
        busqueda: params?.busqueda,
        pagina: params?.pagina,
      })
      return peticion<{ total: number; pagina: number; por_pagina: number; datos: unknown[] }>(`/usuarios${query}`)
    },
    obtener: (id: string) => peticion<unknown>(`/usuarios/${id}`),
    crear: (datos: {
      email: string
      nombre_completo: string
      contrasena: string
      rol: string
      nombre_csv?: string
      manager_id?: string
      sbus_ids?: string[]
    }) => peticion<unknown>("/usuarios", { method: "POST", body: JSON.stringify(datos) }),
    actualizar: (
      id: string,
      datos: {
        nombre_completo?: string
        rol?: string
        nombre_csv?: string
        manager_id?: string
        activo?: boolean
        sbus_ids?: string[]
        motivo_cambio_rol?: string
      },
    ) => peticion<unknown>(`/usuarios/${id}`, { method: "PUT", body: JSON.stringify(datos) }),
    eliminar: (id: string) => peticion<void>(`/usuarios/${id}`, { method: "DELETE" }),
    permisos: () => peticion<Record<string, boolean>>("/usuarios/me/permisos"),
  },

  // =============================================================================
  // Mi Perfil
  // =============================================================================
  perfil: {
    obtener: () => peticion<unknown>("/perfil/me"),
    actualizar: (datos: Record<string, unknown>) =>
      peticion<unknown>("/perfil/me", { method: "PUT", body: JSON.stringify(datos) }),
    stats: () => peticion<unknown>("/perfil/me/stats"),
    exportarCsv: async () => {
      const fecha = new Date().toISOString().slice(0, 10)
      await downloadFromApi("/perfil/me/exportar-csv", `perfil_comercial_${fecha}.csv`, { method: "GET" })
    },
    listarObjetivos: () => peticion<unknown[]>("/perfil/me/objetivos"),
    crearObjetivo: (datos: Record<string, unknown>) =>
      peticion<unknown>("/perfil/me/objetivos", { method: "POST", body: JSON.stringify(datos) }),
    actualizarObjetivo: (id: string, valor_actual: number) =>
      peticion<unknown>(`/perfil/me/objetivos/${id}`, {
        method: "PUT",
        body: JSON.stringify({ valor_actual }),
      }),
    eliminarObjetivo: (id: string) =>
      peticion<void>(`/perfil/me/objetivos/${id}`, { method: "DELETE" }),
    resetearCuenta: () => peticion<{ eliminados: Record<string, number>; total_tablas: number }>("/perfil/me/reset", { method: "DELETE" }),
    obtenerNotificaciones: () => peticion<unknown>("/perfil/me/notificaciones"),
    actualizarNotificaciones: (datos: Record<string, unknown>) =>
      peticion<unknown>("/perfil/me/notificaciones", { method: "PUT", body: JSON.stringify(datos) }),
  },

  // =============================================================================
  // Objetivos comerciales
  // =============================================================================
  objetivos: {
    listar: (params?: {
      estado?: string
      propietario_id?: string
      cuenta_id?: string
      oportunidad_id?: string
      busqueda?: string
      pagina?: number
      por_pagina?: number
      sort_by?: string
      sort_dir?: "asc" | "desc"
    }) => {
      const query = construirQuery({
        estado: params?.estado,
        propietario_id: params?.propietario_id,
        cuenta_id: params?.cuenta_id,
        oportunidad_id: params?.oportunidad_id,
        busqueda: params?.busqueda,
        pagina: params?.pagina,
        por_pagina: params?.por_pagina,
        sort_by: params?.sort_by,
        sort_dir: params?.sort_dir,
      })
      return peticion<{ total: number; pagina: number; por_pagina: number; datos: unknown[] }>(`/objetivos${query}`)
    },
    sugerir: (limite = 20, guardar = true) =>
      peticion<unknown[]>(`/objetivos/sugerir?limite=${limite}&guardar=${guardar}`, { method: "POST" }),
    crear: (datos: {
      cuenta_id?: string
      oportunidad_id?: string
      tipo_objetivo?: string
      titulo: string
      descripcion?: string
      prioridad?: number
      fecha_objetivo?: string
    }) =>
      peticion<unknown>("/objetivos", { method: "POST", body: JSON.stringify(datos) }),
    detalle: (id: string) => peticion<{ objetivo: unknown; artefactos: unknown[] }>(`/objetivos/${id}`),
    actualizar: (
      id: string,
      datos: {
        titulo?: string
        descripcion?: string
        prioridad?: number
        estado?: string
        fecha_objetivo?: string
        score_impacto?: number
        score_confianza?: number
      },
    ) => peticion<unknown>(`/objetivos/${id}`, { method: "PATCH", body: JSON.stringify(datos) }),
    eliminar: (id: string) => peticion<void>(`/objetivos/${id}`, { method: "DELETE" }),
    vincularArtefacto: (objetivoId: string, artefactoId: string, tipoRelacion = "generado") =>
      peticion<{ ok: boolean }>(
        `/objetivos/${objetivoId}/artefactos/${artefactoId}?tipo_relacion=${encodeURIComponent(tipoRelacion)}`,
        { method: "POST" },
      ),
  },

  // =============================================================================
  // Importación CSV
  // =============================================================================
  importacion: {
    subir: async (archivo: File, modo: "upsert" | "append" | "reset") => {
      const form = new FormData()
      form.append("archivo", archivo)
      form.append("modo", modo)
      const response = await peticionRaw("/importacion/csv", {
        method: "POST",
        body: form,
      })
      return response.json()
    },
    estado: (id: string) => peticion<import("@/types").ImportacionEstado>(`/importacion/${id}/estado`),
    historial: () => peticion<import("@/types").ImportacionEstado[]>("/importacion/historial"),
    preview: (id: string) =>
      peticion<{ id: string; nombre_archivo: string; creado_en: string; columnas: string[]; filas: Record<string, string>[] }>(
        `/importacion/${id}/preview`,
      ),
    eliminar: (id: string) => peticion<void>(`/importacion/${id}`, { method: "DELETE" }),
    chat: (pregunta: string, importacion_id?: string) =>
      peticion<{ respuesta: string; resumen: Record<string, number>; importacion_id_contexto?: string | null }>("/importacion/chat", {
        method: "POST",
        body: JSON.stringify({ pregunta, importacion_id }),
      }),
  },

  // =============================================================================
  // Cross-Selling Intelligence
  // =============================================================================
  // =============================================================================
  // Forecast + Cola Cross-sell
  // =============================================================================
  forecast: {
    me: (recalcular = false, propietarioId?: string) =>
      peticion<import("@/types").ForecastResult>(
        `/forecast/me${construirQuery({ recalcular, propietario_id: propietarioId })}`,
      ),
    equipo: () =>
      peticion<import("@/types").ForecastEquipo>("/forecast/equipo"),
    crossSellQueue: (limit = 10, recalcular = false) =>
      peticion<import("@/types").CrossSellQueueItem[]>(
        `/forecast/cross-sell-queue?limit=${limit}&recalcular=${recalcular}`
      ),
    registrarReal: (snapshotId: string, mes: string, importe: number) =>
      peticion<{ ok: boolean }>(`/forecast/snapshots/${snapshotId}/real`, {
        method: "PUT",
        body: JSON.stringify({ mes, importe }),
      }),
  },

  crossSelling: {
    listar: (params?: { busqueda?: string; sbu?: string; confianza?: string; solo_ranking?: boolean }) => {
      const qs = new URLSearchParams()
      if (params?.busqueda) qs.set("busqueda", params.busqueda)
      if (params?.sbu) qs.set("sbu", params.sbu)
      if (params?.confianza) qs.set("confianza", params.confianza)
      if (params?.solo_ranking) qs.set("solo_ranking", "true")
      return peticion<unknown>(`/cross-selling?${qs}`)
    },
    obtener: (accountName: string) =>
      peticion<unknown>(`/cross-selling/${encodeURIComponent(accountName)}`),
  },

  // =============================================================================
  // Historial de documentos generados
  // =============================================================================

  historial: {
    listar: (params?: {
      cuentaId?: string
      contextoTipo?: ContextoTipo
      contextoId?: string
      pagina?: number
      por_pagina?: number
      sort_by?: string
      sort_dir?: "asc" | "desc"
    }) => {
      const qs = construirQuery({
        cuenta_id: params?.cuentaId,
        contexto_tipo: params?.contextoTipo,
        contexto_id: params?.contextoId,
        pagina: params?.pagina,
        por_pagina: params?.por_pagina,
        sort_by: params?.sort_by,
        sort_dir: params?.sort_dir,
      })
      return peticion<import("@/types").DocumentoHistorial[]>(`/historial${qs}`)
    },
    artefactos: (params?: {
      contextoTipo?: ContextoTipo
      contextoId?: string
      pagina?: number
      por_pagina?: number
      sort_by?: string
      sort_dir?: "asc" | "desc"
    }) => {
      const qs = construirQuery({
        contexto_tipo: params?.contextoTipo,
        contexto_id: params?.contextoId,
        pagina: params?.pagina,
        por_pagina: params?.por_pagina,
        sort_by: params?.sort_by,
        sort_dir: params?.sort_dir,
      })
      return peticion<{ pagina: number; por_pagina: number; datos: unknown[] }>(`/historial/artefactos${qs}`)
    },
    urlDescarga: async (docId: string): Promise<string> => {
      const data = await peticion<{ url: string }>(`/historial/${docId}/url`)
      return data.url
    },
    descargar: (docId: string, nombre = `historial_${docId}`) =>
      downloadFromApi(`/historial/${docId}/descargar`, nombre),
    abrir: (docId: string) => openFromApi(`/historial/${docId}/descargar`),
    blob: async (docId: string): Promise<Blob> => {
      const r = await peticionRaw(`/historial/${docId}/descargar`)
      return r.blob()
    },
    slides: (docId: string) =>
      peticion<{ total: number; slides: Array<{ index: number; titulo: string; cuerpo: string; notas: string }> }>(
        `/historial/${docId}/slides`
      ),
    texto: (docId: string) =>
      peticion<{ tipo: string; texto?: string; datos?: unknown }>(`/historial/${docId}/texto`),
    eliminar: (docId: string) =>
      peticion<void>(`/historial/${docId}`, { method: "DELETE" }),
    compartir: (docId: string, dias = 7) =>
      peticion<{ token: string; expira_en: string }>(`/historial/${docId}/compartir?dias=${dias}`, { method: "POST" }),
  },

  // =============================================================================
  // Plantillas de documentación (admin)
  // =============================================================================

  plantillas: {
    listar: (tipo?: string, soloActivas = true) => {
      const qs = new URLSearchParams({ solo_activas: String(soloActivas) })
      if (tipo) qs.set("tipo", tipo)
      return peticion<import("@/types").PlantillaDoc[]>(`/plantillas?${qs}`)
    },
    obtener: (id: string) =>
      peticion<import("@/types").PlantillaDoc>(`/plantillas/${id}`),
    variables: (id: string) =>
      peticion<{ tipo: string; variables: string[] }>(`/plantillas/${id}/variables`),
    crear: (datos: { nombre: string; tipo: string; contenido: Record<string, unknown> }) =>
      peticion<import("@/types").PlantillaDoc>("/plantillas", {
        method: "POST",
        body: JSON.stringify(datos),
      }),
    actualizar: (id: string, datos: { nombre?: string; contenido?: Record<string, unknown>; activa?: boolean }) =>
      peticion<import("@/types").PlantillaDoc>(`/plantillas/${id}`, {
        method: "PUT",
        body: JSON.stringify(datos),
      }),
    eliminar: (id: string) =>
      peticion<void>(`/plantillas/${id}`, { method: "DELETE" }),
  },

  // =============================================================================
  // Artefactos IA unificados (versionado + trazabilidad)
  // =============================================================================
  artefactos: {
    listar: (params?: {
      tipo?: string
      subtipo?: string
      entidad_tipo?: string
      entidad_id?: string
      cuenta_id?: string
      propietario_id?: string
      q?: string
      pagina?: number
      por_pagina?: number
      sort_by?: string
      sort_dir?: "asc" | "desc"
    }) => {
      const qs = construirQuery({
        tipo: params?.tipo,
        subtipo: params?.subtipo,
        entidad_tipo: params?.entidad_tipo,
        entidad_id: params?.entidad_id,
        cuenta_id: params?.cuenta_id,
        propietario_id: params?.propietario_id,
        q: params?.q,
        pagina: params?.pagina,
        por_pagina: params?.por_pagina,
        sort_by: params?.sort_by,
        sort_dir: params?.sort_dir,
      })
      return peticion<{ total: number; pagina: number; por_pagina: number; datos: unknown[] }>(`/artefactos${qs}`)
    },
    detalle: (id: string) => peticion<unknown>(`/artefactos/${id}`),
    blob: async (id: string): Promise<Blob> => {
      const r = await peticionRaw(`/artefactos/${id}/blob`)
      return r.blob()
    },
    versiones: (id: string) => peticion<unknown[]>(`/artefactos/${id}/versiones`),
    crearVersion: (id: string, payload: {
      prompt?: string
      resultado_texto?: string
      resultado_json?: Record<string, unknown>
      storage_key?: string
      modelo?: string
      plantilla_id?: string
      metadatos?: Record<string, unknown>
      fuentes?: Array<{
        fuente_artefacto_id?: string
        fuente_tipo?: string
        fuente_ref?: string
        peso?: number
      }>
    }) =>
      peticion<unknown>(`/artefactos/${id}/versiones`, { method: "POST", body: JSON.stringify(payload) }),
    marcarVersionActual: (id: string, versionNum: number) =>
      peticion<{ ok: boolean }>(`/artefactos/${id}/versiones/${versionNum}/actual`, { method: "PATCH" }),
    eliminar: (id: string) =>
      peticion<void>(`/artefactos/${id}`, { method: "DELETE" }),
    contexto: (params?: { entidad_tipo?: string; entidad_id?: string; cuenta_id?: string; limit?: number }) => {
      const qs = construirQuery({
        entidad_tipo: params?.entidad_tipo,
        entidad_id: params?.entidad_id,
        cuenta_id: params?.cuenta_id,
        limit: params?.limit,
      })
      return peticion<unknown[]>(`/artefactos/contexto${qs}`)
    },
    repositorio: (params?: {
      tipo?: string
      subtipo?: string
      entidad_tipo?: string
      entidad_id?: string
      cuenta_id?: string
      propietario_id?: string
      q?: string
      pagina?: number
      por_pagina?: number
    }) => {
      const qs = construirQuery({
        tipo: params?.tipo,
        subtipo: params?.subtipo,
        entidad_tipo: params?.entidad_tipo,
        entidad_id: params?.entidad_id,
        cuenta_id: params?.cuenta_id,
        propietario_id: params?.propietario_id,
        q: params?.q,
        pagina: params?.pagina,
        por_pagina: params?.por_pagina,
      })
      return peticion<import("@/types").ArtefactoRepositorioRespuesta>(`/artefactos/repositorio${qs}`)
    },
  },

  // =============================================================================
  // Archivos de cuenta (subidos manualmente)
  // =============================================================================

  archivosCuenta: {
    subir: async (cuentaId: string, archivo: File): Promise<{
      id: string; nombre_original: string; tipo_mime: string | null
      tamaño_bytes: number | null; creado_en: string; tiene_texto: boolean
    }> => {
      const form = new FormData()
      form.append("archivo", archivo)
      const res = await peticionRaw(`/cuentas/${cuentaId}/archivos/subir`, {
        method: "POST",
        body: form,
      })
      return res.json()
    },

    listar: (cuentaId: string) =>
      peticion<Array<{
        id: string; nombre_original: string; tipo_mime: string | null
        tamaño_bytes: number | null; creado_en: string; tiene_texto: boolean
      }>>(`/cuentas/${cuentaId}/archivos`),

    contenido: (cuentaId: string, docId: string) =>
      peticion<{ texto: string }>(`/cuentas/${cuentaId}/archivos/${docId}/contenido`),

    descargar: (cuentaId: string, docId: string, nombreFichero: string): Promise<void> =>
      downloadFromApi(`/cuentas/${cuentaId}/archivos/${docId}/descargar`, nombreFichero),

    eliminar: (cuentaId: string, docId: string) =>
      peticion<void>(`/cuentas/${cuentaId}/archivos/${docId}`, { method: "DELETE" }),
  },
}
