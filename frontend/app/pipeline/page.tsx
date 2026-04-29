"use client"

import { useState, useEffect, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import Link from "next/link"
import { Topbar } from "@/components/layout/topbar"
import { api } from "@/lib/api"
import { obtenerApiBaseUrl } from "@/lib/api-base-url"
import { cn, formatearEuros, ETIQUETAS_ETAPA } from "@/lib/utils"
import { useAppStore } from "@/store/use-app-store"
import { useDocumentoJob } from "@/hooks/use-documento-job"
import { ArtefactoPicker } from "@/components/ui/artefacto-picker"
import type { RespuestaPaginada, Oportunidad, EtapaFunnel, ScoringOportunidad } from "@/types"

// =============================================================================
// Constantes
// =============================================================================

const ETAPAS_FILTRO = [
  { value: "", label: "Todas las etapas" },
  { value: "discover", label: "Discover" },
  { value: "propose", label: "Propuesta" },
  { value: "estimation_sent", label: "Estimación enviada" },
  { value: "estimation_accepted", label: "Estimación aceptada" },
  { value: "technically_approved", label: "Aprobado técnicamente" },
  { value: "contract_offer_sent", label: "Contrato enviado" },
  { value: "negotiate", label: "Negociación" },
  { value: "in_progress", label: "En progreso" },
  { value: "closed_won", label: "Cerrado ganado" },
  { value: "closed_lost", label: "Cerrado perdido" },
  { value: "closed_withdrawn", label: "Retirado" },
]

const COLOR_ETAPA: Record<string, string> = {
  closed_won: "bg-green-50 text-green-700",
  closed_lost: "bg-red-50 text-red-700",
  closed_withdrawn: "bg-zinc-100 text-zinc-500",
  negotiate: "bg-amber-50 text-amber-700",
  contract_offer_sent: "bg-blue-50 text-blue-700",
  technically_approved: "bg-indigo-50 text-indigo-700",
  estimation_accepted: "bg-purple-50 text-purple-700",
  estimation_sent: "bg-sky-50 text-sky-700",
  in_progress: "bg-teal-50 text-teal-700",
  propose: "bg-orange-50 text-orange-700",
  discover: "bg-zinc-50 text-zinc-600",
}

const LINEAS_NEGOCIO = [
  "Certification", "ESG Solutions", "Second Party", "Testing", "Inspection",
  "Training & Qualification", "Product Certification", "Customized Assurance",
  "Digital Trust", "Healthcare", "Food & Retail", "Technical Advisory", "Government & Sustainability",
]

const CANALES_VENTA = ["Directo", "Indirecto", "Alliance", "Online"]
const POR_PAGINA = 50

// =============================================================================
// Tipo detalle oportunidad
// =============================================================================

interface OportunidadDetalle {
  id: string
  nombre: string
  importe: number
  etapa: string
  fecha_creacion: string | null
  fecha_decision: string | null
  linea_negocio: string | null
  canal_venta: string | null
  tipo: string | null
  external_id: string | null
  cuenta_id: string | null
  producto_id: string | null
  cuenta_nombre: string | null
  propietario_nombre: string | null
  sbu_nombre: string | null
  producto_nombre: string | null
  creado_en: string
  actualizado_en: string
}

// =============================================================================
// Sugerencia AI inline
// =============================================================================

type Sugerencia = { linea_negocio: string; canal_venta: string; confianza: number; razonamiento: string }

function BadgeConfianza({ valor }: { valor: number }) {
  const color = valor >= 0.8 ? "bg-emerald-100 text-emerald-700"
    : valor >= 0.6 ? "bg-amber-100 text-amber-700"
    : "bg-zinc-100 text-zinc-500"
  return (
    <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded-full", color)}>
      {Math.round(valor * 100)}% confianza
    </span>
  )
}

// =============================================================================
// Modal Nueva Oportunidad
// =============================================================================

function ModalNuevaOportunidad({ onCerrar }: { onCerrar: () => void }) {
  const queryClient = useQueryClient()
  const [nombre, setNombre] = useState("")
  const [cuenta, setCuenta] = useState("")
  const [importe, setImporte] = useState("")
  const [etapa, setEtapa] = useState("discover")
  const [lineaNegocio, setLineaNegocio] = useState("")
  const [canalVenta, setCanalVenta] = useState("")
  const [fechaCreacion, setFechaCreacion] = useState(new Date().toISOString().split("T")[0])
  const [sugerencia, setSugerencia] = useState<Sugerencia | null>(null)
  const [cargandoSugerencia, setCargandoSugerencia] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState("")
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (nombre.length < 5) { setSugerencia(null); return }
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(async () => {
      setCargandoSugerencia(true)
      try {
        const result = await api.pipeline.sugerirCampos({ nombre_oportunidad: nombre, cuenta: cuenta || undefined })
        setSugerencia(result)
      } catch { /* silencioso */ } finally { setCargandoSugerencia(false) }
    }, 800)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [nombre, cuenta])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    const importeNum = parseFloat(importe.replace(",", "."))
    if (isNaN(importeNum) || importeNum <= 0) { setError("El importe debe ser mayor que 0."); return }
    setEnviando(true)
    try {
      await fetch(`${obtenerApiBaseUrl()}/pipeline`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}` },
        body: JSON.stringify({ nombre, importe: importeNum, etapa, fecha_creacion: fechaCreacion, linea_negocio: lineaNegocio || null, canal_venta: canalVenta || null }),
      })
      queryClient.invalidateQueries({ queryKey: ["pipeline-lista"] })
      queryClient.invalidateQueries({ queryKey: ["pipeline-funnel"] })
      onCerrar()
    } catch { setError("Error al crear la oportunidad.") } finally { setEnviando(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overlay-strong">
      <div className="ui-panel w-full max-w-lg mx-4 overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-200 flex items-center justify-between">
          <h2 className="text-base font-semibold text-zinc-900">Nueva oportunidad</h2>
          <button onClick={onCerrar} className="text-zinc-400 hover:text-zinc-700 text-lg leading-none">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-700 mb-1">Nombre <span className="text-sgs-rojo">*</span></label>
            <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Ej: ISO 9001 Auditoría Empresa S.L." required className="ui-input text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-700 mb-1">Cuenta / Cliente</label>
            <input value={cuenta} onChange={(e) => setCuenta(e.target.value)} placeholder="Nombre de la empresa cliente" className="ui-input text-sm" />
          </div>
          {(cargandoSugerencia || sugerencia) && (
            <div className={cn("rounded-lg border px-3 py-2.5 text-xs", sugerencia ? "border-blue-200 bg-blue-50" : "border-zinc-200 bg-zinc-50")}>
              {cargandoSugerencia ? (
                <span className="text-zinc-500 flex items-center gap-2"><span className="inline-block w-3 h-3 border-2 border-zinc-400 border-t-transparent rounded-full animate-spin" />Analizando con IC...</span>
              ) : sugerencia ? (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2"><span className="text-blue-700 font-medium">✦ Sugerencia IC</span><BadgeConfianza valor={sugerencia.confianza} /></div>
                  <p className="text-zinc-600"><span className="font-medium">BL:</span> {sugerencia.linea_negocio} · <span className="font-medium">Canal:</span> {sugerencia.canal_venta}</p>
                  {sugerencia.razonamiento && <p className="text-zinc-400 italic">{sugerencia.razonamiento}</p>}
                  <button type="button" onClick={() => { setLineaNegocio(sugerencia.linea_negocio); setCanalVenta(sugerencia.canal_venta) }} className="mt-1 text-[11px] font-medium text-blue-700 hover:text-blue-900 underline">Aplicar sugerencia →</button>
                </div>
              ) : null}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1">Business Line</label>
              <select value={lineaNegocio} onChange={(e) => setLineaNegocio(e.target.value)} className="ui-input text-sm">
                <option value="">— Seleccionar —</option>
                {LINEAS_NEGOCIO.map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1">Canal de venta</label>
              <select value={canalVenta} onChange={(e) => setCanalVenta(e.target.value)} className="ui-input text-sm">
                <option value="">— Seleccionar —</option>
                {CANALES_VENTA.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1">Importe (€) <span className="text-sgs-rojo">*</span></label>
              <input type="number" min="0.01" step="0.01" value={importe} onChange={(e) => setImporte(e.target.value)} placeholder="0.00" required className="ui-input text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1">Etapa</label>
              <select value={etapa} onChange={(e) => setEtapa(e.target.value)} className="ui-input text-sm">
                {ETAPAS_FILTRO.filter((e) => e.value).map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-700 mb-1">Fecha de creación</label>
            <input type="date" value={fechaCreacion} onChange={(e) => setFechaCreacion(e.target.value)} className="ui-input text-sm" />
          </div>
          {error && <p className="text-xs text-red-600">{error}</p>}
          <div className="flex items-center justify-end gap-3 pt-2 border-t border-zinc-100">
            <button type="button" onClick={onCerrar} className="px-4 py-2 text-sm text-zinc-600 hover:text-zinc-900">Cancelar</button>
            <button type="submit" disabled={enviando} className="px-4 py-2 text-sm font-medium bg-sgs-rojo text-white rounded-lg hover:bg-red-700 disabled:opacity-50">{enviando ? "Creando..." : "Crear oportunidad"}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// =============================================================================
// Drawer de detalle + edición
// =============================================================================

function DrawerOportunidad({
  opId,
  onCerrar,
  puedeEditar,
  puedeEliminar,
}: {
  opId: string
  onCerrar: () => void
  puedeEditar: boolean
  puedeEliminar: boolean
}) {
  const queryClient = useQueryClient()
  const [editando, setEditando] = useState(false)
  const [confirmEliminar, setConfirmEliminar] = useState(false)
  const [lanzandoIa, setLanzandoIa] = useState<"pdf" | "pptx" | "briefing" | null>(null)
  const [form, setForm] = useState<Partial<OportunidadDetalle>>({})
  const [error, setError] = useState("")
  const [tabDrawer, setTabDrawer] = useState<"detalle" | "repositorio">("detalle")
  const { lanzar } = useDocumentoJob()

  const { data: op, isLoading } = useQuery<OportunidadDetalle>({
    queryKey: ["pipeline-detalle", opId],
    queryFn: () => api.pipeline.obtener(opId) as Promise<OportunidadDetalle>,
  })

  useEffect(() => {
    if (op) setForm({ nombre: op.nombre, importe: op.importe, etapa: op.etapa, fecha_creacion: op.fecha_creacion ?? "", fecha_decision: op.fecha_decision ?? "", linea_negocio: op.linea_negocio ?? "", canal_venta: op.canal_venta ?? "" })
  }, [op])

  const mutGuardar = useMutation({
    mutationFn: () => api.pipeline.actualizar(opId, {
      nombre: form.nombre,
      importe: form.importe ? Number(form.importe) : undefined,
      etapa: form.etapa,
      fecha_creacion: form.fecha_creacion || undefined,
      fecha_decision: form.fecha_decision || undefined,
      linea_negocio: form.linea_negocio || null,
      canal_venta: form.canal_venta || null,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline-lista"] })
      queryClient.invalidateQueries({ queryKey: ["pipeline-detalle", opId] })
      queryClient.invalidateQueries({ queryKey: ["pipeline-funnel"] })
      setEditando(false)
    },
    onError: (e: Error) => setError(e.message),
  })

  const mutEliminar = useMutation({
    mutationFn: () => api.pipeline.eliminar(opId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline-lista"] })
      queryClient.invalidateQueries({ queryKey: ["pipeline-funnel"] })
      onCerrar()
    },
  })

  function campo(label: string, children: React.ReactNode) {
    return (
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 mb-1">{label}</p>
        {children}
      </div>
    )
  }

  return (
    <>
      <div className="fixed inset-0 overlay-strong z-40" onClick={onCerrar} />
      <aside className="fixed right-0 top-0 h-screen w-full sm:w-[480px] bg-white border-l border-zinc-200 z-50 flex flex-col shadow-xl">
        {/* Header */}
        <div className="px-5 py-4 border-b border-zinc-200 flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-[10px] text-zinc-400 uppercase tracking-widest mb-0.5">Oportunidad</p>
            <h2 className="text-sm font-semibold text-zinc-900 truncate">{op?.nombre ?? "Cargando..."}</h2>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {puedeEditar && !editando && (
              <button onClick={() => { setEditando(true); setError("") }} className="text-xs px-2.5 py-1 border border-zinc-200 rounded-md hover:bg-zinc-50 text-zinc-600">✎ Editar</button>
            )}
            <button onClick={onCerrar} className="text-zinc-400 hover:text-zinc-700 text-lg leading-none">✕</button>
          </div>
        </div>

        {/* Tabs del drawer */}
        {!editando && (
          <div className="flex border-b border-zinc-100 shrink-0">
            {(["detalle", "repositorio"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTabDrawer(t)}
                className={cn(
                  "flex-1 py-2.5 text-xs font-medium transition-colors",
                  tabDrawer === t
                    ? "text-sgs-rojo border-b-2 border-sgs-rojo -mb-px"
                    : "text-zinc-500 hover:text-zinc-700",
                )}
              >
                {t === "detalle" ? "Detalle" : "Repositorio IC"}
              </button>
            ))}
          </div>
        )}

        {/* Contenido */}
        {tabDrawer === "repositorio" && op ? (
          <div className="flex-1 p-4 overflow-y-auto">
            <ArtefactoPicker contextoTipo="oportunidad" contextoId={op.id} />
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="p-5 space-y-3">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-8 bg-zinc-100 rounded animate-pulse" />)}</div>
            ) : op ? (
            <div className="p-5 space-y-5">
              {/* Badge etapa */}
              <span className={cn("inline-block px-2.5 py-1 rounded-full text-xs font-semibold", COLOR_ETAPA[op.etapa] ?? "bg-zinc-100 text-zinc-600")}>
                {ETIQUETAS_ETAPA[op.etapa] ?? op.etapa}
              </span>

              {editando ? (
                /* ── Formulario edición ── */
                <div className="space-y-4">
                  {campo("Nombre", (
                    <input value={form.nombre ?? ""} onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))} className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo" />
                  ))}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {campo("Importe (€)", (
                      <input type="number" value={form.importe ?? ""} onChange={(e) => setForm((f) => ({ ...f, importe: Number(e.target.value) }))} className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo" />
                    ))}
                    {campo("Etapa", (
                      <select value={form.etapa ?? ""} onChange={(e) => setForm((f) => ({ ...f, etapa: e.target.value }))} className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo bg-white">
                        {ETAPAS_FILTRO.filter((e) => e.value).map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
                      </select>
                    ))}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {campo("Fecha creación", (
                      <input type="date" value={form.fecha_creacion ?? ""} onChange={(e) => setForm((f) => ({ ...f, fecha_creacion: e.target.value }))} className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo" />
                    ))}
                    {campo("Fecha decisión", (
                      <input type="date" value={form.fecha_decision ?? ""} onChange={(e) => setForm((f) => ({ ...f, fecha_decision: e.target.value }))} className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo" />
                    ))}
                  </div>
                  {campo("Business Line", (
                    <select value={form.linea_negocio ?? ""} onChange={(e) => setForm((f) => ({ ...f, linea_negocio: e.target.value }))} className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo bg-white">
                      <option value="">— Sin especificar —</option>
                      {LINEAS_NEGOCIO.map((l) => <option key={l} value={l}>{l}</option>)}
                    </select>
                  ))}
                  {campo("Canal de venta", (
                    <select value={form.canal_venta ?? ""} onChange={(e) => setForm((f) => ({ ...f, canal_venta: e.target.value }))} className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo bg-white">
                      <option value="">— Sin especificar —</option>
                      {CANALES_VENTA.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  ))}
                  {error && <p className="text-xs text-red-600">{error}</p>}
                </div>
              ) : (
                /* ── Vista de detalle ── */
                <div className="space-y-4">
                  {op.cuenta_id && (
                    <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-2">IC contextual (oportunidad)</p>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => {
                            setLanzandoIa("pdf")
                            void lanzar(
                              "pdf",
                              () => api.documentosJobs.generarPdf(op.cuenta_id as string, { contexto: op.nombre, contextoTipo: "oportunidad", contextoId: op.id }),
                              () => setLanzandoIa(null),
                              () => setLanzandoIa(null),
                            )
                          }}
                          disabled={lanzandoIa !== null}
                          className="px-3 py-1.5 text-xs font-medium border border-zinc-300 rounded-lg bg-white hover:bg-zinc-100 disabled:opacity-50"
                        >
                          {lanzandoIa === "pdf" ? "Lanzando…" : "PDF"}
                        </button>
                        <button
                          onClick={() => {
                            setLanzandoIa("pptx")
                            void lanzar(
                              "pptx",
                              () => api.documentosJobs.generarPptx(op.cuenta_id as string, { contexto: op.nombre, contextoTipo: "oportunidad", contextoId: op.id }),
                              () => setLanzandoIa(null),
                              () => setLanzandoIa(null),
                            )
                          }}
                          disabled={lanzandoIa !== null}
                          className="px-3 py-1.5 text-xs font-medium border border-zinc-300 rounded-lg bg-white hover:bg-zinc-100 disabled:opacity-50"
                        >
                          {lanzandoIa === "pptx" ? "Lanzando…" : "Deck"}
                        </button>
                        <button
                          onClick={() => {
                            setLanzandoIa("briefing")
                            void lanzar(
                              "briefing",
                              () => api.documentosJobs.generarBriefing(op.cuenta_id as string, { contexto: op.nombre, contextoTipo: "oportunidad", contextoId: op.id }),
                              () => setLanzandoIa(null),
                              () => setLanzandoIa(null),
                            )
                          }}
                          disabled={lanzandoIa !== null}
                          className="px-3 py-1.5 text-xs font-medium border border-zinc-300 rounded-lg bg-white hover:bg-zinc-100 disabled:opacity-50"
                        >
                          {lanzandoIa === "briefing" ? "Lanzando…" : "Briefing"}
                        </button>
                        <Link
                          href={`/documentos?tab=ia&contexto_tipo=oportunidad&contexto_id=${op.id}`}
                          className="px-3 py-1.5 text-xs font-medium border border-zinc-300 rounded-lg bg-white hover:bg-zinc-100"
                        >
                          Historial IC
                        </Link>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-zinc-50 rounded-xl p-4">
                    <div>
                      <p className="text-[10px] text-zinc-400 uppercase tracking-widest">Importe</p>
                      <p className="text-lg font-bold text-zinc-900">{formatearEuros(op.importe)}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-zinc-400 uppercase tracking-widest">SBU</p>
                      <p className="text-sm font-semibold text-zinc-700">{op.sbu_nombre ?? "—"}</p>
                    </div>
                  </div>

                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between py-2 border-b border-zinc-50">
                      <span className="text-zinc-400">Cuenta</span>
                      <span className="font-medium text-zinc-800 text-right max-w-[260px] truncate">{op.cuenta_nombre ?? "—"}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-zinc-50">
                      <span className="text-zinc-400">Propietario</span>
                      <span className="font-medium text-zinc-800">{op.propietario_nombre ?? "—"}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-zinc-50">
                      <span className="text-zinc-400">Producto</span>
                      <span className="font-medium text-zinc-800">{op.producto_nombre ?? "—"}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-zinc-50">
                      <span className="text-zinc-400">Business Line</span>
                      <span className="font-medium text-zinc-800">{op.linea_negocio ?? "—"}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-zinc-50">
                      <span className="text-zinc-400">Canal de venta</span>
                      <span className="font-medium text-zinc-800">{op.canal_venta ?? "—"}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-zinc-50">
                      <span className="text-zinc-400">Fecha creación</span>
                      <span className="font-medium text-zinc-800">{op.fecha_creacion ? new Date(op.fecha_creacion).toLocaleDateString("es-ES") : "—"}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-zinc-50">
                      <span className="text-zinc-400">Fecha decisión</span>
                      <span className="font-medium text-zinc-800">{op.fecha_decision ? new Date(op.fecha_decision).toLocaleDateString("es-ES") : "—"}</span>
                    </div>
                    {op.external_id && (
                      <div className="flex justify-between py-2 border-b border-zinc-50">
                        <span className="text-zinc-400">ID Salesforce</span>
                        <span className="font-mono text-xs text-zinc-500">{op.external_id}</span>
                      </div>
                    )}
                    <div className="flex justify-between py-2">
                      <span className="text-zinc-400">Actualizado</span>
                      <span className="text-zinc-500 text-xs">{new Date(op.actualizado_en).toLocaleDateString("es-ES")}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : null}
          </div>
        )}

        {/* Footer */}
        <div className="px-5 py-4 border-t border-zinc-100 space-y-2">
          {editando ? (
            <div className="flex gap-2">
              <button onClick={() => { setEditando(false); setError("") }} className="flex-1 px-4 py-2 text-sm border border-zinc-200 rounded-lg hover:bg-zinc-50 text-zinc-600">Cancelar</button>
              <button onClick={() => mutGuardar.mutate()} disabled={mutGuardar.isPending} className="flex-1 px-4 py-2 text-sm font-medium bg-sgs-rojo text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
                {mutGuardar.isPending ? "Guardando..." : "Guardar cambios"}
              </button>
            </div>
          ) : puedeEliminar ? (
            confirmEliminar ? (
              <div className="flex gap-2">
                <button onClick={() => setConfirmEliminar(false)} className="flex-1 px-4 py-2 text-sm border border-zinc-200 rounded-lg hover:bg-zinc-50 text-zinc-600">Cancelar</button>
                <button onClick={() => mutEliminar.mutate()} disabled={mutEliminar.isPending} className="flex-1 px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
                  {mutEliminar.isPending ? "Eliminando..." : "Confirmar eliminación"}
                </button>
              </div>
            ) : (
              <button onClick={() => setConfirmEliminar(true)} className="w-full px-4 py-2 text-xs text-red-500 hover:text-red-700 hover:bg-red-50 border border-red-200 rounded-lg transition-colors">
                ✕ Eliminar oportunidad
              </button>
            )
          ) : null}
        </div>
      </aside>
    </>
  )
}

// =============================================================================
// Página principal
// =============================================================================

export default function PaginaPipeline() {
  const [pagina, setPagina] = useState(1)
  const [etapaFiltro, setEtapaFiltro] = useState("")
  const [sortBy, setSortBy] = useState<"nombre" | "etapa" | "importe" | "fecha_creacion" | "fecha_decision">("fecha_creacion")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")
  const [soloCriticos, setSoloCriticos] = useState(false)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [opSeleccionada, setOpSeleccionada] = useState<string | null>(null)
  const [scorePorOportunidad, setScorePorOportunidad] = useState<Record<string, ScoringOportunidad>>({})
  const [opScoreSeleccionada, setOpScoreSeleccionada] = useState<string | null>(null)
  const [propietarioId, setPropietarioId] = useState("")
  const { isManager, isAdmin } = useAppStore()
  const propietarioFiltro = isManager() && propietarioId ? propietarioId : undefined

  const { data: comerciales = [] } = useQuery<Array<{ propietario_id: string; nombre_completo: string }>>({
    queryKey: ["equipo-ranking-selector-pipeline"],
    queryFn: () => api.equipo.ranking() as Promise<Array<{ propietario_id: string; nombre_completo: string }>>,
    enabled: isManager(),
  })

  const { data, isLoading } = useQuery<RespuestaPaginada<Oportunidad>>({
    queryKey: ["pipeline-lista", pagina, etapaFiltro, sortBy, sortDir, propietarioFiltro],
    queryFn: () => {
      let url = `/pipeline?pagina=${pagina}&por_pagina=${POR_PAGINA}&sort_by=${sortBy}&sort_dir=${sortDir}`
      if (etapaFiltro) url += `&etapa=${etapaFiltro}`
      if (propietarioFiltro) url += `&propietario_id=${propietarioFiltro}`
      return fetch(`${obtenerApiBaseUrl()}${url}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}` },
      }).then((r) => r.json())
    },
  })

  const { data: funnel = [] } = useQuery<EtapaFunnel[]>({
    queryKey: ["pipeline-funnel", propietarioFiltro],
    queryFn: () => api.pipeline.funnel(propietarioFiltro) as Promise<EtapaFunnel[]>,
  })

  const { data: criticos = [] } = useQuery({
    queryKey: ["pipeline-scores-criticos"],
    queryFn: () => api.scoring.criticos(40),
  })

  useEffect(() => {
    const oportunidades = data?.datos ?? []
    if (oportunidades.length === 0) return

    const idsSinCargar = oportunidades
      .map((o) => o.id)
      .filter((id) => !scorePorOportunidad[id])
    if (idsSinCargar.length === 0) return

    let cancelado = false
    Promise.all(
      idsSinCargar.map(async (id) => {
        try {
          const score = await api.scoring.obtener(id)
          return { id, score }
        } catch {
          return null
        }
      }),
    ).then((resultados) => {
      if (cancelado) return
      const nuevos: Record<string, ScoringOportunidad> = {}
      for (const item of resultados) {
        if (item?.score) nuevos[item.id] = item.score
      }
      if (Object.keys(nuevos).length > 0) {
        setScorePorOportunidad((prev) => ({ ...prev, ...nuevos }))
      }
    })

    return () => { cancelado = true }
  }, [data?.datos, scorePorOportunidad])

  const totalPaginas = data ? Math.ceil(data.total / POR_PAGINA) : 1
  const maxImporte = funnel.length ? Math.max(...funnel.map((e) => Number(e.importe_total)), 1) : 1
  const idsCriticos = new Set((criticos ?? []).map((c) => c.oportunidad_id))
  const filasVisibles = (data?.datos ?? []).filter((op) => !soloCriticos || idsCriticos.has(op.id))

  function cambiarEtapa(etapa: string) { setEtapaFiltro(etapa); setPagina(1) }
  function cambiarOrden(columna: "nombre" | "etapa" | "importe" | "fecha_creacion" | "fecha_decision") {
    if (sortBy === columna) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"))
    } else {
      setSortBy(columna)
      setSortDir(columna === "nombre" || columna === "etapa" ? "asc" : "desc")
    }
    setPagina(1)
  }
  function iconoOrden(columna: string) {
    if (sortBy !== columna) return "↕"
    return sortDir === "asc" ? "↑" : "↓"
  }

  return (
    <>
      <Topbar titulo="Pipeline" subtitulo="Gestión de oportunidades comerciales" />

      {modalAbierto && <ModalNuevaOportunidad onCerrar={() => setModalAbierto(false)} />}
      {opSeleccionada && (
        <DrawerOportunidad
          opId={opSeleccionada}
          onCerrar={() => setOpSeleccionada(null)}
          puedeEditar={isManager()}
          puedeEliminar={isAdmin()}
        />
      )}

      <main className="flex-1 p-2.5 md:p-3.5 space-y-5">
        {/* Funnel */}
        {funnel.length > 0 && (
          <div className="ui-panel p-5">
            <h2 className="text-sm font-semibold text-zinc-800 mb-4">Distribución del funnel</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {funnel.filter((e) => !["closed_won", "closed_lost", "closed_withdrawn"].includes(e.etapa)).map((etapa) => {
                const pct = (Number(etapa.importe_total) / maxImporte) * 100
                return (
                  <button key={etapa.etapa} onClick={() => cambiarEtapa(etapaFiltro === etapa.etapa ? "" : etapa.etapa)}
                    className={`text-left p-3 rounded-lg border transition-all ${etapaFiltro === etapa.etapa ? "border-sgs-rojo bg-red-50" : "border-zinc-200 hover:border-zinc-300"}`}>
                    <p className="text-xs font-medium text-zinc-700 truncate">{ETIQUETAS_ETAPA[etapa.etapa] ?? etapa.etapa}</p>
                    <p className="text-sm font-bold text-zinc-900 mt-0.5">{formatearEuros(Number(etapa.importe_total))}</p>
                    <p className="text-xs text-zinc-400">{etapa.num_oportunidades} opps</p>
                    <div className="h-1 bg-zinc-100 rounded-full mt-2 overflow-hidden">
                      <div className="h-full rounded-full bg-sgs-azul" style={{ width: `${pct}%` }} />
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Filtros + botón */}
        <div className="flex items-center gap-3 flex-wrap justify-between">
          <div className="flex items-center gap-3 flex-wrap">
            <select value={etapaFiltro} onChange={(e) => cambiarEtapa(e.target.value)} className="text-sm border border-zinc-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo">
              {ETAPAS_FILTRO.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
            </select>
            {isManager() && (
              <select
                value={propietarioId}
                onChange={(e) => { setPropietarioId(e.target.value); setPagina(1) }}
                className="text-sm border border-zinc-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
              >
                <option value="">Todos los comerciales</option>
                {comerciales.map((c) => (
                  <option key={c.propietario_id} value={c.propietario_id}>{c.nombre_completo}</option>
                ))}
              </select>
            )}
            <button
              onClick={() => setSoloCriticos((v) => !v)}
              className={cn(
                "text-xs px-3 py-2 rounded-lg border transition-colors",
                soloCriticos
                  ? "border-red-300 bg-red-50 text-red-700"
                  : "border-zinc-300 bg-white text-zinc-600 hover:bg-zinc-50",
              )}
            >
              Score crítico (&lt;40)
            </button>
            {data && <p className="text-sm text-zinc-500"><span className="font-semibold text-zinc-900">{data.total.toLocaleString("es-ES")}</span> oportunidades</p>}
            {etapaFiltro && <button onClick={() => cambiarEtapa("")} className="text-xs text-zinc-400 hover:text-zinc-700 underline">Limpiar filtro</button>}
            <select
              value={sortBy}
              onChange={(e) => cambiarOrden(e.target.value as "nombre" | "etapa" | "importe" | "fecha_creacion" | "fecha_decision")}
              className="text-sm border border-zinc-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
            >
              <option value="fecha_creacion">Orden: fecha creación</option>
              <option value="fecha_decision">Orden: fecha decisión</option>
              <option value="importe">Orden: importe</option>
              <option value="nombre">Orden: oportunidad</option>
              <option value="etapa">Orden: etapa</option>
            </select>
            <select
              value={sortDir}
              onChange={(e) => { setSortDir(e.target.value as "asc" | "desc"); setPagina(1) }}
              className="text-sm border border-zinc-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
            >
              <option value="desc">Descendente</option>
              <option value="asc">Ascendente</option>
            </select>
          </div>
          {isManager() && (
            <button onClick={() => setModalAbierto(true)} className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-sgs-rojo text-white rounded-lg hover:bg-red-700 transition-colors">
              + Nueva oportunidad
            </button>
          )}
        </div>

        {/* Tabla */}
        <div className="ui-panel overflow-hidden">
          {isLoading ? (
            <div className="p-6 space-y-3">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-10 bg-zinc-100 rounded animate-pulse" />)}</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-zinc-50 border-b border-zinc-100">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                      <button type="button" onClick={() => cambiarOrden("nombre")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                        Oportunidad <span>{iconoOrden("nombre")}</span>
                      </button>
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                      <button type="button" onClick={() => cambiarOrden("etapa")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                        Etapa <span>{iconoOrden("etapa")}</span>
                      </button>
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-zinc-500 uppercase tracking-wide">Score</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                      <button type="button" onClick={() => cambiarOrden("importe")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                        Importe <span>{iconoOrden("importe")}</span>
                      </button>
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                      <button type="button" onClick={() => cambiarOrden("fecha_creacion")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                        Creada <span>{iconoOrden("fecha_creacion")}</span>
                      </button>
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                      <button type="button" onClick={() => cambiarOrden("fecha_decision")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                        Decisión <span>{iconoOrden("fecha_decision")}</span>
                      </button>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-50">
                  {filasVisibles.map((op) => (
                    <tr
                      key={op.id}
                      onClick={() => setOpSeleccionada(op.id)}
                      className={cn(
                        "hover:bg-zinc-50 transition-colors cursor-pointer",
                        opSeleccionada === op.id && "bg-red-50 border-l-2 border-l-sgs-rojo"
                      )}
                    >
                      <td className="px-4 py-3"><p className="font-medium text-zinc-900 truncate max-w-xs">{op.nombre}</p></td>
                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${COLOR_ETAPA[op.etapa] ?? "bg-zinc-100 text-zinc-600"}`}>
                          {ETIQUETAS_ETAPA[op.etapa] ?? op.etapa}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {scorePorOportunidad[op.id] ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setOpScoreSeleccionada(op.id)
                            }}
                            className={cn(
                              "inline-block px-2 py-0.5 rounded-full text-xs font-semibold",
                              scorePorOportunidad[op.id].score >= 70
                                ? "bg-emerald-100 text-emerald-700"
                                : scorePorOportunidad[op.id].score >= 40
                                  ? "bg-amber-100 text-amber-700"
                                  : "bg-red-100 text-red-700",
                            )}
                          >
                            {scorePorOportunidad[op.id].score}
                          </button>
                        ) : (
                          <span className="text-xs text-zinc-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-zinc-900">{formatearEuros(op.importe)}</td>
                      <td className="px-4 py-3 text-right text-zinc-500 text-xs">{op.fecha_creacion ? new Date(op.fecha_creacion).toLocaleDateString("es-ES") : "—"}</td>
                      <td className="px-4 py-3 text-right text-zinc-500 text-xs">{op.fecha_decision ? new Date(op.fecha_decision).toLocaleDateString("es-ES") : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Paginación */}
          {data && totalPaginas > 1 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-zinc-100">
              <p className="text-xs text-zinc-500">Página {pagina} de {totalPaginas}</p>
              <div className="flex gap-2">
                <button onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina === 1} className="px-3 py-1.5 text-xs border border-zinc-200 rounded-lg disabled:opacity-40 hover:bg-zinc-50">← Anterior</button>
                <button onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina === totalPaginas} className="px-3 py-1.5 text-xs border border-zinc-200 rounded-lg disabled:opacity-40 hover:bg-zinc-50">Siguiente →</button>
              </div>
            </div>
          )}
        </div>
      </main>

      {opScoreSeleccionada && scorePorOportunidad[opScoreSeleccionada] && (
        <>
          <div className="fixed inset-0 overlay-strong z-40" onClick={() => setOpScoreSeleccionada(null)} />
          <aside className="fixed right-0 top-0 h-screen w-full sm:w-[420px] bg-white border-l border-zinc-200 z-50 flex flex-col shadow-xl">
            <div className="px-5 py-4 border-b border-zinc-200 flex items-center justify-between">
              <div>
                <p className="text-[10px] text-zinc-400 uppercase tracking-widest">Scoring</p>
                <h3 className="text-sm font-semibold text-zinc-900">Desglose de factores</h3>
              </div>
              <button onClick={() => setOpScoreSeleccionada(null)} className="text-zinc-400 hover:text-zinc-700 text-lg leading-none">✕</button>
            </div>
            <div className="p-5 space-y-3 overflow-y-auto">
              <div className="rounded-xl bg-zinc-50 border border-zinc-100 p-4">
                <p className="text-xs text-zinc-500">Score actual</p>
                <p className="text-2xl font-bold text-zinc-900 mt-1">{scorePorOportunidad[opScoreSeleccionada].score}</p>
              </div>
              {Object.entries(scorePorOportunidad[opScoreSeleccionada].factores).map(([clave, valor]) => (
                <div key={clave} className="flex items-center justify-between border-b border-zinc-100 pb-2">
                  <p className="text-sm text-zinc-700">{clave.replaceAll("_", " ")}</p>
                  <p className="text-sm font-semibold text-zinc-900">{String(valor)}</p>
                </div>
              ))}
            </div>
          </aside>
        </>
      )}
    </>
  )
}
