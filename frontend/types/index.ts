// =============================================================================
// Negocio — interfaces de dominio en español
// =============================================================================

export interface PermisosUsuario {
  ver_equipo: boolean
  ver_todos_pipeline: boolean
  gestionar_usuarios: boolean
  importar_datos: boolean
  ver_informes_ejecutivos: boolean
  gestionar_alertas: boolean
}

export interface UsuarioActual {
  usuario_id: string
  email: string
  nombre_completo: string
  rol: "admin" | "manager" | "supervisor" | "comercial"
  sbus_asignados: string[]
  permisos: PermisosUsuario
}

export interface KpisDashboard {
  total_oportunidades: number
  oportunidades_activas: number
  oportunidades_ganadas: number
  oportunidades_perdidas: number
  pipeline_total: number
  pipeline_activo: number
  importe_ganado: number
  importe_perdido: number
  ticket_medio_ganado: number
  win_rate_global: number
  calculado_en: string
}

export interface PuntoEvolucion {
  mes: string
  total_creadas: number
  ganadas: number
}

export interface BreakdownSbu {
  sbu: string
  total_oportunidades: number
  oportunidades_activas: number
  pipeline_activo: number
  importe_ganado: number
  win_rate: number
}

export interface EtapaFunnel {
  etapa: string
  num_oportunidades: number
  importe_total: number
  importe_medio: number
}

export interface Oportunidad {
  id: string
  nombre: string
  importe: number
  etapa: string
  fecha_creacion: string
  fecha_decision: string | null
}

export interface ScoringOportunidad {
  oportunidad_id: string
  score: number
  factores: Record<string, unknown>
  calculado_en: string
}

export interface Seguimiento {
  id: string
  oportunidad_id: string | null
  cuenta_id: string | null
  usuario_id: string
  creado_por: string
  tipo: "recordatorio" | "proximo_paso" | "cadencia"
  titulo: string
  descripcion: string | null
  fecha_vencimiento: string
  estado: "pendiente" | "completado" | "cancelado"
  completado_en: string | null
  creado_en: string
  actualizado_en: string
}

export interface ComercialRanking {
  propietario_id: string
  nombre_completo: string
  total_oportunidades: number
  oportunidades_ganadas: number
  cerradas: number
  importe_ganado: number
  pipeline_abierto: number
  win_rate: number
}

export interface ProductoAnalisis {
  id: string
  nombre: string
  total_oportunidades: number
  oportunidades_ganadas: number
  importe_ganado: number
  ticket_medio: number
  win_rate: number
}

export interface Alerta {
  id: string
  titulo: string
  descripcion: string | null
  nivel: "critico" | "seguimiento" | "oportunidad"
  resuelta: boolean
  creado_en: string
  usuario_nombre: string | null
}

// =============================================================================
// Perfil
// =============================================================================

export interface PerfilRead {
  usuario_id: string
  email: string
  nombre_completo: string
  rol: string
  telefono: string | null
  zona: string | null
  sbu_principal: string | null
  avatar_url: string | null
  manager_id: string | null
}

export interface PerfilStats {
  pipeline_activo: number
  win_rate: number
  oportunidades_abiertas: number
  oportunidades_ganadas: number
  oportunidades_perdidas: number
  ticket_medio: number
}

export interface ObjetivoRead {
  id: string
  nombre: string
  valor_actual: number
  valor_meta: number
  unidad: string
  periodo: string
  progreso_pct: number
}

export interface NotificacionesConfig {
  alertas_pipeline: boolean
  briefing_diario: boolean
  alerta_win_rate: boolean
  hora_briefing: string
  umbral_win_rate: number
  voz_tts: string
  duracion_podcast_min: number
}

export interface ObjetivoComercial {
  id: string
  usuario_id: string
  cuenta_id: string | null
  cuenta_nombre: string | null
  oportunidad_id: string | null
  oportunidad_nombre: string | null
  tipo_objetivo: string
  origen: string
  titulo: string
  descripcion: string | null
  prioridad: number
  estado: string
  fecha_objetivo: string | null
  score_impacto: number
  score_confianza: number
  artefactos_total: number
  cross_sell_ref: string | null
  metadatos: Record<string, unknown>
  creado_en: string
  actualizado_en: string
}

export interface ObjetivoArtefacto {
  id: string
  tipo: string
  subtipo: string | null
  titulo: string | null
  actualizado_en: string
  tipo_relacion: string
}

export interface ObjetivoDetalle {
  objetivo: ObjetivoComercial
  artefactos: ObjetivoArtefacto[]
}

export interface ObjetivoSugerencia {
  oportunidad_id: string
  oportunidad_nombre: string
  cuenta_id: string | null
  cuenta_nombre: string | null
  tipo_objetivo: string
  titulo: string
  descripcion: string
  prioridad: number
  score_impacto: number
  score_confianza: number
  cross_sell_ref: string | null
}

// =============================================================================
// Informes PDF
// =============================================================================

export interface InformeResumen {
  id: string
  tipo: string
  titulo: string
  periodo: string | null
  destinatario: string | null
  estado: string
  paginas: number | null
  creado_en: string
  completado_en: string | null
}

export interface EstadoJobInforme {
  job_id: string
  estado: string
  progreso: number
  paso_actual: string | null
  indice: Array<{ titulo: string; descripcion: string }> | null
}

// =============================================================================
// Documentos
// =============================================================================

export interface DocumentoRead {
  id: string
  nombre_original: string
  tipo_mime: string | null
  tamaño_bytes: number | null
  oportunidad_id: string | null
  oportunidad_nombre: string | null
  cuenta_id: string | null
  cuenta_nombre: string | null
  creado_en: string
  tiene_transcripcion: boolean
}

// =============================================================================
// Notas de Voz
// =============================================================================

export interface NotaRead {
  id: string
  titulo: string
  transcripcion: string
  duracion_seg: number | null
  oportunidad_id: string | null
  oportunidad_nombre: string | null
  creado_en: string
}

// =============================================================================
// Cuentas
// =============================================================================

export interface OportunidadEnCuenta {
  id: string
  nombre: string
  importe: number
  etapa: string
  fecha_creacion: string
  fecha_decision: string | null
}

export interface CuentaResumen {
  id: string
  nombre: string
  total_oportunidades: number
  oportunidades_activas: number
  pipeline_activo: number
  importe_ganado: number
  win_rate: number
  ultima_actividad: string | null
}

export interface CuentaDetalle extends CuentaResumen {
  oportunidades: OportunidadEnCuenta[]
}

export interface FichaReunion {
  cuenta: {
    nombre: string
    sector: string | null
    num_empleados: string | null
  }
  investigacion: {
    pain_points: string[]
    certificaciones_actuales: string[]
    noticias_relevantes: string[]
  }
  propuesta: {
    productos_recomendados: Array<Record<string, unknown>>
    escenario_medio: Record<string, unknown>
  }
  pipeline: {
    activas: number
    importe_total: number
    etapa_critica: string | null
  }
  seguimientos: Array<{
    id: string
    tipo: string
    titulo: string
    descripcion: string | null
    fecha_vencimiento: string
    estado: string
  }>
  score_medio: number
  materiales: {
    deck_disponible: boolean
    pdf_disponible: boolean
    briefing_disponible: boolean
  }
}

export interface ValidacionCheck {
  ok: boolean
  msg: string
  bloquea: boolean
}

export interface ValidacionCalidad {
  cuenta_id: string
  tipo_entregable: "pdf" | "pptx" | "deck" | "briefing"
  valido: boolean
  nivel: "ok" | "warning" | "error"
  checks: ValidacionCheck[]
}

export interface CoachingSesion {
  id: string
  usuario_id: string
  cuenta_id: string | null
  tipo: "analisis_notas" | "plan_mejora" | "feedback_pitch"
  resultado: Record<string, unknown>
  creado_en: string
}

// =============================================================================
// Usuarios (admin)
// =============================================================================

export interface UsuarioRead {
  id: string
  email: string
  nombre_completo: string
  rol: "admin" | "manager" | "supervisor" | "comercial"
  nombre_csv: string | null
  manager_id: string | null
  activo: boolean
  creado_en: string
  sbus_asignados: string[]
}

// =============================================================================
// API — respuestas genéricas
// =============================================================================

export interface RespuestaPaginada<T> {
  total: number
  pagina: number
  por_pagina: number
  datos: T[]
}

export interface RespuestaToken {
  access_token: string
  tipo_token: string
}

// =============================================================================
// Configuración IA
// =============================================================================

export interface IaConfig {
  proveedor: "anthropic" | "ollama"
  ollamaUrl: string
  ollamaModelo: string
}

export type ServicioIa = "copilot" | "voice" | "informes" | "decks" | "cross_selling" | "importacion"

export interface IaConfigs {
  copilot: IaConfig
  voice: IaConfig
  informes: IaConfig
  decks: IaConfig
  cross_selling: IaConfig
  importacion: IaConfig
}

// =============================================================================
// Importación CSV
// =============================================================================

export interface ImportacionEstado {
  id: string
  nombre_archivo: string
  modo: "upsert" | "append" | "reset"
  estado: "procesando" | "completado" | "error"
  total_filas: number | null
  filas_procesadas: number | null
  filas_creadas: number | null
  filas_actualizadas: number | null
  filas_error: number | null
  errores: Array<{ fila: number; error: string }> | null
  creado_en: string
  usuario: string | null
}

// =============================================================================
// Forecast
// =============================================================================

export interface EscenarioForecast {
  m1: number
  m2: number
  m3: number
  total: number
}

export interface ForecastResult {
  usuario_id: string
  usuario_nombre: string
  mes_1: string
  mes_2: string
  mes_3: string
  pipeline_total: number
  pipeline_maduro: number
  baseline_mediana: number
  sbu_dominante: string | null
  wr_sbu: number
  pesimista: EscenarioForecast
  base: EscenarioForecast
  optimista: EscenarioForecast
}

export interface ForecastEquipoItem {
  usuario_nombre: string
  pipeline_maduro: number
  baseline_mediana: number
  sbu_dominante: string | null
  pesimista_total: number
  base_total: number
  optimista_total: number
}

export interface ForecastEquipo {
  comerciales: ForecastEquipoItem[]
  totales_pesimista: number
  totales_base: number
  totales_optimista: number
}

export interface CrossSellQueueItem {
  id: string | null
  cuenta_nombre: string
  sbu_actual: string | null
  productos_won: string | null
  ops_abiertas: number
  pipeline_abierto: number
  oportunidades_top: string | null
  mensaje_comercial: string | null
  preguntas_discovery: string | null
  confianza: string | null
  score: number
}

// =============================================================================
// Clientes (vista global — manager/admin)
// =============================================================================

export interface OportunidadEnCliente {
  id: string
  nombre: string
  importe: number
  etapa: string
  fecha_creacion: string
  fecha_decision: string | null
  propietario_nombre: string | null
  sbu_nombre: string | null
  producto_nombre: string | null
}

export interface ClienteResumen {
  id: string
  nombre: string
  total_oportunidades: number
  oportunidades_activas: number
  pipeline_activo: number
  importe_ganado: number
  win_rate: number
  ultima_actividad: string | null
  comerciales: string[]
  sbus: string[]
}

export interface ClienteDetalle extends Omit<ClienteResumen, "ultima_actividad"> {
  oportunidades: OportunidadEnCliente[]
}

// =============================================================================
// Productos — oportunidades por producto
// =============================================================================

export interface OportunidadEnProducto {
  id: string
  nombre: string
  importe: number
  etapa: string
  fecha_creacion: string
  fecha_decision: string | null
  cuenta_id: string | null
  cuenta_nombre: string | null
  propietario_nombre: string | null
}

// =============================================================================
// Cross-Selling Intelligence
// =============================================================================

export interface CrossSellingItem {
  id: string
  account_name: string
  sbu: string | null
  servicio_actual: string | null
  ops_abiertas: number | null
  oportunidades_top: string | null
  sector_osint: string | null
  trigger_activador: string | null
  confianza: "Alta" | "Media-Alta" | "Media" | "Media-Baja" | "Baja" | null
  ranking_accionable: number | null
  mensaje_comercial: string | null
  preguntas_discovery: string | null
  creado_en: string
}

// =============================================================================
// Historial de documentos generados por agentes IA
// =============================================================================

export interface DocumentoHistorial {
  id: string
  tipo: "investigacion" | "propuesta" | "pdf" | "pptx" | "briefing" | "audio" | "transcripcion"
  nombre_fichero: string
  tamano_bytes: number | null
  metadatos: Record<string, unknown>
  contexto_tipo?: "cuenta" | "cliente" | "producto" | "oportunidad"
  contexto_id?: string | null
  creado_en: string
  cuenta_nombre: string | null
  usuario_nombre: string
}

export interface ArtefactoRepositorioItem {
  id: string
  tipo: string
  subtipo: string
  titulo: string
  estado: string
  version_actual: number
  creado_en: string
  actualizado_en: string
  preview_texto: string
  storage_key: string | null
  entidad_tipo: string | null
  entidad_id: string | null
  cuenta_id: string | null
  origen_tabla: string | null
  origen_id: string | null
}

export interface ArtefactoRepositorioGrupo {
  origen_tipo: string
  origen_id: string | null
  origen_key: string
  origen_nombre: string
  actualizado_en: string
  total: number
  items: ArtefactoRepositorioItem[]
}

export interface ArtefactoRepositorioRespuesta {
  pagina: number
  por_pagina: number
  total_items: number
  total_grupos: number
  datos: ArtefactoRepositorioGrupo[]
}

// =============================================================================
// Plantillas de documentación
// =============================================================================

export interface PlantillaDoc {
  id: string
  nombre: string
  tipo: "pdf" | "pptx" | "investigacion" | "propuesta" | "briefing" | "informe"
  activa: boolean
  contenido: Record<string, unknown>
  variables: string[]
  creado_en: string
  actualizado_en: string
  creado_por_nombre: string | null
}
