"use client"

import { useState, useEffect, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import { Topbar } from "@/components/layout/topbar"
import { useJobsStore } from "@/store/use-jobs-store"
import { useAppStore } from "@/store/use-app-store"
import type { InformeResumen, EstadoJobInforme } from "@/types"

// =============================================================================
// Combobox de empresas
// =============================================================================

function ComboboxCuentas({
  cuentas,
  valor,
  onChange,
}: {
  cuentas: Array<{ nombre: string }>
  valor: string
  onChange: (v: string) => void
}) {
  const [busqueda, setBusqueda] = useState(valor)
  const [abierto, setAbierto] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const filtradas = busqueda.trim().length === 0
    ? cuentas.slice(0, 50)
    : cuentas
        .filter((c) => c.nombre.toLowerCase().includes(busqueda.toLowerCase()))
        .slice(0, 50)

  // Cerrar al hacer clic fuera
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setAbierto(false)
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [])

  function seleccionar(nombre: string) {
    onChange(nombre)
    setBusqueda(nombre)
    setAbierto(false)
  }

  function limpiar() {
    onChange("")
    setBusqueda("")
  }

  return (
    <div ref={ref} className="relative">
      <div className="relative">
        <input
          type="text"
          value={busqueda}
          onChange={(e) => { setBusqueda(e.target.value); setAbierto(true); if (!e.target.value) onChange("") }}
          onFocus={() => setAbierto(true)}
          placeholder="Buscar empresa…"
          className="w-full px-3 py-2 pr-8 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
        />
        {busqueda && (
          <button
            onClick={limpiar}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-700 text-xs"
          >
            ✕
          </button>
        )}
      </div>

      {abierto && (
        <div className="absolute z-20 mt-1 w-full bg-white border border-zinc-200 rounded-lg shadow-lg max-h-56 overflow-y-auto">
          {filtradas.length === 0 ? (
            <p className="px-3 py-2 text-xs text-zinc-400 italic">Sin resultados</p>
          ) : (
            <>
              {/* Opción vacía */}
              <button
                onClick={() => seleccionar("")}
                className="w-full text-left px-3 py-2 text-xs text-zinc-400 hover:bg-zinc-50 border-b border-zinc-100"
              >
                — Sin empresa específica —
              </button>
              {filtradas.map((c) => (
                <button
                  key={c.nombre}
                  onClick={() => seleccionar(c.nombre)}
                  className={cn(
                    "w-full text-left px-3 py-2 text-sm hover:bg-red-50 hover:text-sgs-rojo transition-colors",
                    valor === c.nombre && "bg-red-50 text-sgs-rojo font-medium",
                  )}
                >
                  {c.nombre}
                </button>
              ))}
              {filtradas.length === 50 && (
                <p className="px-3 py-1.5 text-[10px] text-zinc-400 italic border-t border-zinc-100">
                  Mostrando 50 de {cuentas.filter(c => c.nombre.toLowerCase().includes(busqueda.toLowerCase())).length} resultados — sigue escribiendo para filtrar
                </p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Const types
// =============================================================================

const TIPO_INFORME = {
  EJECUTIVO: "ejecutivo_mensual",
  COMERCIAL: "analisis_comercial",
  CLIENTE: "propuesta_cliente",
  PIPELINE: "revision_pipeline",
} as const

type TipoInforme = (typeof TIPO_INFORME)[keyof typeof TIPO_INFORME]

const TIPOS_CONFIG = [
  {
    id: TIPO_INFORME.EJECUTIVO,
    titulo: "Informe ejecutivo mensual",
    descripcion: "KPIs globales, pipeline, rendimiento del equipo y alertas clave.",
    icono: "📊",
  },
  {
    id: TIPO_INFORME.COMERCIAL,
    titulo: "Análisis de comercial",
    descripcion: "Rendimiento individual detallado con comparativa frente al equipo.",
    icono: "👤",
  },
  {
    id: TIPO_INFORME.CLIENTE,
    titulo: "Propuesta para cliente",
    descripcion: "Informe personalizado con datos del pipeline del cliente.",
    icono: "🤝",
  },
  {
    id: TIPO_INFORME.PIPELINE,
    titulo: "Revisión de pipeline",
    descripcion: "Funnel completo con recomendaciones de acción por etapa.",
    icono: "🔄",
  },
]

const PERIODOS = [
  "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4",
  "2026-Q1", "2026-Q2", "2026-ANUAL", "2025-ANUAL",
]

const ESTADO_COLOR: Record<string, string> = {
  completado: "text-emerald-700 bg-emerald-50",
  generando: "text-blue-700 bg-blue-50",
  pendiente: "text-amber-700 bg-amber-50",
  error: "text-red-700 bg-red-50",
}

const ESTADO_LABEL: Record<string, string> = {
  completado: "Completado",
  generando: "Generando…",
  pendiente: "Pendiente",
  error: "Error",
}

// =============================================================================
// Panel de progreso (polling)
// =============================================================================

function PanelProgreso({
  jobId,
  titulo,
  onCompletado,
}: {
  jobId: string
  titulo: string
  onCompletado: () => void
}) {
  const completadoRef = useRef(false)
  const { addJob, updateJob } = useJobsStore()

  useEffect(() => {
    addJob({ jobId, tipo: "informe", titulo, estado: "pendiente", progreso: 0 })
  }, [jobId, titulo, addJob])

  const { data } = useQuery<EstadoJobInforme>({
    queryKey: ["informe-job", jobId],
    queryFn: () => api.informes.estado(jobId) as Promise<EstadoJobInforme>,
    refetchInterval: (query) => {
      const estado = query.state.data?.estado
      return estado === "completado" || estado === "error" ? false : 2000
    },
  })

  useEffect(() => {
    if (!data) return
    updateJob(jobId, { estado: data.estado, progreso: data.progreso })
    if (data.estado === "completado" && !completadoRef.current) {
      completadoRef.current = true
      onCompletado()
    }
  }, [data, jobId, updateJob, onCompletado])

  if (!data) return null

  return (
    <div className="bg-white rounded-xl border border-zinc-200 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-800">Generando informe…</h3>
        <span className="text-sm font-bold text-sgs-rojo">{data.progreso}%</span>
      </div>

      {/* Barra de progreso */}
      <div className="h-2 bg-zinc-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-sgs-rojo rounded-full transition-all duration-500"
          style={{ width: `${data.progreso}%` }}
        />
      </div>

      {data.paso_actual && (
        <p className="text-xs text-zinc-500">{data.paso_actual}</p>
      )}

      {/* Índice generado */}
      {data.indice && data.indice.length > 0 && (
        <div className="border-t border-zinc-100 pt-4">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">
            Índice del informe
          </p>
          <ol className="space-y-1">
            {data.indice.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-zinc-600">
                <span className="font-semibold text-sgs-rojo shrink-0">{i + 1}.</span>
                <span>{item.titulo}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {data.estado === "error" && (
        <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          Error durante la generación. Inténtalo de nuevo.
        </p>
      )}
    </div>
  )
}

// =============================================================================
// Tarjeta de informe histórico
// =============================================================================

function TarjetaInforme({
  informe,
  onEliminar,
}: {
  informe: InformeResumen
  onEliminar: (id: string) => void
}) {
  const [descargando, setDescargando] = useState(false)

  async function descargar() {
    setDescargando(true)
    try {
      await api.informes.descargar(informe.id, informe.titulo)
    } finally {
      setDescargando(false)
    }
  }

  const tipoConfig = TIPOS_CONFIG.find((t) => t.id === informe.tipo)

  return (
    <div className="flex items-center gap-4 bg-white rounded-xl border border-zinc-200 px-4 py-3 hover:border-zinc-300 transition-colors">
      <span className="text-2xl shrink-0">{tipoConfig?.icono ?? "📄"}</span>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-900 truncate">{informe.titulo}</p>
        <div className="flex items-center gap-3 mt-0.5 flex-wrap">
          {informe.periodo && (
            <span className="text-xs text-zinc-400">{informe.periodo}</span>
          )}
          {informe.paginas && (
            <span className="text-xs text-zinc-400">{informe.paginas + 1} págs.</span>
          )}
          <span className="text-xs text-zinc-400">{informe.creado_en.slice(0, 10)}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <span className={cn("text-[10px] font-medium px-2 py-0.5 rounded-full", ESTADO_COLOR[informe.estado] ?? "text-zinc-500 bg-zinc-100")}>
          {ESTADO_LABEL[informe.estado] ?? informe.estado}
        </span>

        {informe.estado === "completado" && (
          <button
            onClick={descargar}
            disabled={descargando}
            className="px-3 py-1.5 text-xs font-medium border border-zinc-200 text-zinc-700 rounded-lg hover:bg-zinc-50 disabled:opacity-50 transition-colors"
          >
            {descargando ? "…" : "↓ PDF"}
          </button>
        )}

        <button
          onClick={() => onEliminar(informe.id)}
          className="text-zinc-300 hover:text-red-500 transition-colors text-sm"
          title="Eliminar"
        >
          ✕
        </button>
      </div>
    </div>
  )
}

// =============================================================================
// Página principal
// =============================================================================

export default function InformesPage() {
  const iaConfig = useAppStore((s) => s.iaConfigs.informes)
  const [tipoSeleccionado, setTipoSeleccionado] = useState<TipoInforme>(TIPO_INFORME.EJECUTIVO)
  const [periodo, setPeriodo] = useState("")
  const [empresaSeleccionada, setEmpresaSeleccionada] = useState("")
  const [destinatario, setDestinatario] = useState("")
  const [contexto, setContexto] = useState("")
  const [jobActivo, setJobActivo] = useState<string | null>(null)
  const [tituloActivo, setTituloActivo] = useState("")
  const queryClient = useQueryClient()

  const { data: cuentasCatalogo = [] } = useQuery({
    queryKey: ["cuentas-catalogo"],
    queryFn: () => api.cuentas.catalogo(),
    staleTime: 5 * 60_000,
  })

  const { data: historial, isLoading: cargandoHistorial } = useQuery<InformeResumen[]>({
    queryKey: ["informes"],
    queryFn: () => api.informes.listar() as Promise<InformeResumen[]>,
  })

  const cuentas = cuentasCatalogo

  const mutGenerar = useMutation({
    mutationFn: () =>
      api.informes.generar(
        {
          tipo: tipoSeleccionado,
          periodo: periodo || undefined,
          destinatario: empresaSeleccionada || destinatario || undefined,
          contexto: contexto || undefined,
        },
        iaConfig,
      ),
    onSuccess: (data) => {
      const tipoConfig = TIPOS_CONFIG.find((t) => t.id === tipoSeleccionado)
      const titulo = tipoConfig?.titulo ?? "Informe"
      setJobActivo(data.job_id)
      setTituloActivo(titulo)
      queryClient.invalidateQueries({ queryKey: ["informes"] })
    },
  })

  const mutEliminar = useMutation({
    mutationFn: (id: string) => api.informes.eliminar(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["informes"] }),
  })

  function onCompletado() {
    queryClient.invalidateQueries({ queryKey: ["informes"] })
  }

  return (
    <div className="flex-1 flex flex-col">
      <Topbar
        titulo="Informes PDF"
        subtitulo="Generación y seguimiento de informes ejecutivos con IC"
      />
      {/* Header */}
      <header className="px-4 sm:px-6 py-5 border-b border-zinc-200 bg-white">
        <h1 className="text-xl font-bold text-zinc-900">Informes PDF</h1>
        <p className="text-sm text-zinc-500 mt-0.5">
          Genera informes ejecutivos con análisis de IC sobre tu pipeline
        </p>
      </header>

      <main className="flex-1 p-2.5 md:p-3.5 space-y-5 w-full">
        {/* Selector de tipo */}
        <div className="bg-white rounded-xl border border-zinc-200 p-5">
          <h2 className="text-sm font-semibold text-zinc-800 mb-4">Tipo de informe</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {TIPOS_CONFIG.map((t) => (
              <button
                key={t.id}
                onClick={() => setTipoSeleccionado(t.id)}
                className={cn(
                  "text-left px-4 py-3 rounded-lg border transition-all",
                  tipoSeleccionado === t.id
                    ? "border-sgs-rojo bg-red-50"
                    : "border-zinc-200 hover:border-zinc-300",
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span>{t.icono}</span>
                  <p className={cn(
                    "text-sm font-medium",
                    tipoSeleccionado === t.id ? "text-sgs-rojo" : "text-zinc-800",
                  )}>
                    {t.titulo}
                  </p>
                </div>
                <p className="text-xs text-zinc-400">{t.descripcion}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Formulario */}
        <div className="bg-white rounded-xl border border-zinc-200 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-zinc-800">Configuración</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-zinc-600 mb-1">Periodo</label>
              <select
                value={periodo}
                onChange={(e) => setPeriodo(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo bg-white"
              >
                <option value="">Sin especificar</option>
                {PERIODOS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-600 mb-1">Empresa cliente</label>
              <ComboboxCuentas
                cuentas={cuentas}
                valor={empresaSeleccionada}
                onChange={setEmpresaSeleccionada}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1">
              Destinatario <span className="text-zinc-400 font-normal">(persona — opcional)</span>
            </label>
            <input
              type="text"
              placeholder="Ej: Director Comercial, Comité de Dirección…"
              value={destinatario}
              onChange={(e) => setDestinatario(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1">
              Contexto adicional <span className="text-zinc-400 font-normal">(opcional)</span>
            </label>
            <textarea
              rows={3}
              placeholder="Información adicional que IC debe tener en cuenta al redactar el informe…"
              value={contexto}
              onChange={(e) => setContexto(e.target.value)}
              maxLength={1000}
              className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo resize-none"
            />
          </div>

          <button
            onClick={() => mutGenerar.mutate()}
            disabled={mutGenerar.isPending || !!jobActivo}
            className="w-full py-2.5 rounded-lg text-sm font-medium text-white bg-sgs-rojo disabled:opacity-50 transition-opacity"
          >
            {mutGenerar.isPending ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Iniciando…
              </span>
            ) : (
              "📊  Generar informe con IC"
            )}
          </button>

          {mutGenerar.isError && (
            <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">
              {mutGenerar.error instanceof Error ? mutGenerar.error.message : "Error al iniciar la generación."}
            </p>
          )}
        </div>

        {/* Panel de progreso */}
        {jobActivo && (
          <PanelProgreso
            jobId={jobActivo}
            titulo={tituloActivo}
            onCompletado={() => {
              onCompletado()
              setTimeout(() => setJobActivo(null), 3000)
            }}
          />
        )}

        {/* Historial */}
        <div>
          <h2 className="text-sm font-semibold text-zinc-800 mb-3">
            Informes generados {historial ? `(${historial.length})` : ""}
          </h2>

          {cargandoHistorial ? (
            <div className="flex items-center justify-center h-20">
              <div className="h-6 w-6 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
            </div>
          ) : !historial?.length ? (
            <div className="flex flex-col items-center justify-center h-20 gap-2">
              <p className="text-sm text-zinc-500">Aún no has generado ningún informe.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {historial.map((inf) => (
                <TarjetaInforme
                  key={inf.id}
                  informe={inf}
                  onEliminar={(id) => mutEliminar.mutate(id)}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
