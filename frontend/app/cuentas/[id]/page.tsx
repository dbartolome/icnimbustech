"use client"

import { useState, use, useEffect, useRef, useCallback, useMemo } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import * as Tabs from "@radix-ui/react-tabs"
import { ArrowLeft, Building2, TrendingUp, Sparkles, Users, FileText, Presentation, Mic, Search, Globe, AlertCircle, Newspaper, Zap, FolderOpen, Upload, Trash2, Download, Bot, SendHorizontal, ChevronDown, ChevronUp, Play, Pause, Square, Volume2, Brain, X } from "lucide-react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import { useDocumentoJob } from "@/hooks/use-documento-job"
import { Topbar } from "@/components/layout/topbar"
import { ArtefactoPicker } from "@/components/ui/artefacto-picker"
import { useAppStore } from "@/store/use-app-store"
import type {
  CuentaDetalle,
  CrossSellingItem,
  FichaReunion,
} from "@/types"

// ─── Formatters ───────────────────────────────────────────────────────────────

const fmtEUR = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 })
const fmtEURc = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", notation: "compact", maximumFractionDigits: 1 })

const ETAPA_LABEL: Record<string, string> = {
  estimation_sent: "Estimación enviada",
  technically_approved: "Aprobado técnicamente",
  in_progress: "En progreso",
  discover: "Discovery",
  contract_offer_sent: "Oferta contrato",
  propose: "Propuesta",
  estimation_accepted: "Estimación aceptada",
  negotiate: "Negociación",
  closed_won: "Ganada",
  closed_lost: "Perdida",
  closed_withdrawn: "Retirada",
}

function badgeEtapa(etapa: string) {
  if (etapa === "closed_won") return "bg-emerald-50 text-emerald-700"
  if (etapa === "closed_lost") return "bg-red-50 text-red-600"
  if (etapa === "closed_withdrawn") return "bg-zinc-100 text-zinc-500"
  return "bg-blue-50 text-blue-700"
}

// ─── Scoring ring ─────────────────────────────────────────────────────────────

function ScoreRing({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs text-zinc-400">—</span>
  const color = score >= 70 ? "#10b981" : score >= 40 ? "#f59e0b" : "#ef4444"
  const label = score >= 70 ? "Alto" : score >= 40 ? "Medio" : "Bajo"
  const r = 14
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - score / 100)
  return (
    <div className="flex items-center gap-2">
      <svg width={36} height={36} viewBox="0 0 36 36" className="-rotate-90">
        <circle cx={18} cy={18} r={r} fill="none" stroke="#f4f4f5" strokeWidth={4} />
        <circle cx={18} cy={18} r={r} fill="none" stroke={color} strokeWidth={4}
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" />
      </svg>
      <div>
        <p className="text-sm font-bold leading-none" style={{ color }}>{score}</p>
        <p className="text-[10px] text-zinc-400">{label}</p>
      </div>
    </div>
  )
}

// ─── Tab: Oportunidades ───────────────────────────────────────────────────────

function TabOportunidades({ cuenta }: { cuenta: CuentaDetalle }) {
  const activasBase = cuenta.oportunidades.filter(
    (o) => o.etapa !== "closed_won" && o.etapa !== "closed_lost" && o.etapa !== "closed_withdrawn"
  )
  const cerradasBase = cuenta.oportunidades.filter(
    (o) => o.etapa === "closed_won" || o.etapa === "closed_lost" || o.etapa === "closed_withdrawn"
  )
  const [sortActivasBy, setSortActivasBy] = useState<"importe" | "fecha" | "nombre" | "etapa">("importe")
  const [sortActivasDir, setSortActivasDir] = useState<"asc" | "desc">("desc")
  const [sortCerradasBy, setSortCerradasBy] = useState<"fecha" | "importe" | "nombre" | "etapa">("fecha")
  const [sortCerradasDir, setSortCerradasDir] = useState<"asc" | "desc">("desc")

  const valorFecha = (v: { fecha_decision?: string | null; fecha_creacion?: string | null }) =>
    new Date(v.fecha_decision ?? v.fecha_creacion ?? "1970-01-01").getTime()

  const activas = useMemo(() => {
    const arr = [...activasBase]
    arr.sort((a, b) => {
      if (sortActivasBy === "importe") return Number(a.importe) - Number(b.importe)
      if (sortActivasBy === "fecha") return valorFecha(a) - valorFecha(b)
      if (sortActivasBy === "etapa") return String(a.etapa).localeCompare(String(b.etapa))
      return String(a.nombre).localeCompare(String(b.nombre))
    })
    if (sortActivasDir === "desc") arr.reverse()
    return arr
  }, [activasBase, sortActivasBy, sortActivasDir])

  const cerradas = useMemo(() => {
    const arr = [...cerradasBase]
    arr.sort((a, b) => {
      if (sortCerradasBy === "importe") return Number(a.importe) - Number(b.importe)
      if (sortCerradasBy === "etapa") return String(a.etapa).localeCompare(String(b.etapa))
      if (sortCerradasBy === "nombre") return String(a.nombre).localeCompare(String(b.nombre))
      return valorFecha(a) - valorFecha(b)
    })
    if (sortCerradasDir === "desc") arr.reverse()
    return arr
  }, [cerradasBase, sortCerradasBy, sortCerradasDir])

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          { label: "Pipeline activo", valor: fmtEURc.format(cuenta.pipeline_activo), sub: `${cuenta.oportunidades_activas} activas` },
          { label: "Importe ganado", valor: fmtEURc.format(cuenta.importe_ganado), sub: "cerrado won" },
          { label: "Win Rate", valor: `${Number(cuenta.win_rate).toFixed(1)}%`, sub: "won vs total" },
          { label: "Total ops", valor: String(cuenta.total_oportunidades), sub: `${activasBase.length} en curso` },
        ].map(({ label, valor, sub }) => (
          <div key={label} className="bg-white rounded-xl border border-zinc-200 p-4">
            <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide">{label}</p>
            <p className="text-xl font-bold text-zinc-900 mt-1">{valor}</p>
            <p className="text-xs text-zinc-400 mt-0.5">{sub}</p>
          </div>
        ))}
      </div>

      {/* Oportunidades activas */}
      {activas.length > 0 && (
        <div>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">En curso</h3>
            <div className="flex items-center gap-2">
              <select
                value={sortActivasBy}
                onChange={(e) => setSortActivasBy(e.target.value as "importe" | "fecha" | "nombre" | "etapa")}
                className="text-[11px] border border-zinc-200 rounded-md px-2 py-1 bg-white text-zinc-600"
              >
                <option value="importe">Orden: importe</option>
                <option value="fecha">Orden: fecha</option>
                <option value="nombre">Orden: nombre</option>
                <option value="etapa">Orden: etapa</option>
              </select>
              <select
                value={sortActivasDir}
                onChange={(e) => setSortActivasDir(e.target.value as "asc" | "desc")}
                className="text-[11px] border border-zinc-200 rounded-md px-2 py-1 bg-white text-zinc-600"
              >
                <option value="desc">Descendente</option>
                <option value="asc">Ascendente</option>
              </select>
            </div>
          </div>
          <div className="space-y-2">
            {activas.map((op) => (
              <div key={op.id} className="bg-white rounded-xl border border-zinc-200 px-4 py-3 flex items-center justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-zinc-900 truncate">{op.nombre}</p>
                  {op.fecha_decision && (
                    <p className="text-xs text-zinc-400 mt-0.5">Decisión: {op.fecha_decision.slice(0, 10)}</p>
                  )}
                </div>
                <div className="flex items-center gap-4 shrink-0">
                  <span className={cn("text-[11px] font-medium px-2 py-0.5 rounded-full", badgeEtapa(op.etapa))}>
                    {ETAPA_LABEL[op.etapa] ?? op.etapa}
                  </span>
                  <p className="text-sm font-semibold text-zinc-800 tabular-nums">{fmtEUR.format(op.importe)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cerradas */}
      {cerradas.length > 0 && (
        <div>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">Historial</h3>
            <div className="flex items-center gap-2">
              <select
                value={sortCerradasBy}
                onChange={(e) => setSortCerradasBy(e.target.value as "fecha" | "importe" | "nombre" | "etapa")}
                className="text-[11px] border border-zinc-200 rounded-md px-2 py-1 bg-white text-zinc-600"
              >
                <option value="fecha">Orden: fecha</option>
                <option value="importe">Orden: importe</option>
                <option value="nombre">Orden: nombre</option>
                <option value="etapa">Orden: etapa</option>
              </select>
              <select
                value={sortCerradasDir}
                onChange={(e) => setSortCerradasDir(e.target.value as "asc" | "desc")}
                className="text-[11px] border border-zinc-200 rounded-md px-2 py-1 bg-white text-zinc-600"
              >
                <option value="desc">Descendente</option>
                <option value="asc">Ascendente</option>
              </select>
            </div>
          </div>
          <div className="space-y-1.5">
            {cerradas.slice(0, 10).map((op) => (
              <div key={op.id} className="flex items-center justify-between px-4 py-2.5 rounded-lg border border-zinc-100 bg-zinc-50 gap-4">
                <p className="text-xs text-zinc-600 truncate min-w-0 flex-1">{op.nombre}</p>
                <div className="flex items-center gap-3 shrink-0">
                  <span className={cn("text-[11px] font-medium px-2 py-0.5 rounded-full", badgeEtapa(op.etapa))}>
                    {ETAPA_LABEL[op.etapa] ?? op.etapa}
                  </span>
                  <p className="text-xs font-semibold text-zinc-700 tabular-nums">{fmtEUR.format(op.importe)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {cuenta.oportunidades.length === 0 && (
        <div className="flex items-center justify-center h-32 text-zinc-400 text-sm">
          Sin oportunidades registradas
        </div>
      )}
    </div>
  )
}

// ─── Tab: Cross-Selling ───────────────────────────────────────────────────────

const CONFIANZA_COLOR: Record<string, string> = {
  Alta: "bg-emerald-100 text-emerald-700",
  "Media-Alta": "bg-teal-100 text-teal-700",
  Media: "bg-amber-100 text-amber-700",
  "Media-Baja": "bg-orange-100 text-orange-700",
  Baja: "bg-red-100 text-red-700",
}

function TabCrossSelling({ cuentaId, nombreCuenta }: { cuentaId: string; nombreCuenta: string }) {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery<CrossSellingItem>({
    queryKey: ["cross-selling", nombreCuenta],
    queryFn: () => api.crossSelling.obtener(nombreCuenta) as Promise<CrossSellingItem>,
    retry: false,
  })
  const { data: estudioIa } = useQuery({
    queryKey: ["estudio-ia", cuentaId],
    queryFn: () => api.documentosJobs.obtenerEstudioIa(cuentaId),
    retry: false,
  })
  const { lanzar } = useDocumentoJob()
  const [lanzando, setLanzando] = useState<string | null>(null)

  // lanzarJob acepta un key libre (tipo o "tipo-contexto") para tracking granular
  async function lanzarJob(key: string, tipo: "pdf" | "pptx" | "briefing" | "estudio_ia", fn: () => Promise<{ job_id: string; estado: string }>) {
    setLanzando(key)
    try {
      await lanzar(tipo, fn, () => {
        if (tipo === "estudio_ia") {
          queryClient.invalidateQueries({ queryKey: ["estudio-ia", cuentaId] })
        }
      })
    } finally {
      setLanzando(null)
    }
  }

  if (isLoading) return <SpinnerCentrado />

  if (!data) return (
    <div className="space-y-4">
      {estudioIa ? (
        <div className="bg-violet-50 border border-violet-200 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-violet-800 flex items-center gap-1.5">
              <Sparkles size={13} /> Análisis IC
            </p>
            <span className="text-[10px] text-violet-500">{new Date(estudioIa.creado_en).toLocaleDateString("es-ES")}</span>
          </div>
          <p className="text-sm text-violet-900">{estudioIa.analisis.resumen}</p>
          {estudioIa.analisis.oportunidades?.map((op, i) => (
            <div key={i} className="bg-white rounded-lg border border-violet-100 overflow-hidden">
              <div className="flex items-center justify-between px-3 py-2">
                <span className="text-xs font-medium text-zinc-800">{op.producto}</span>
                <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full", {
                  "bg-red-100 text-red-700": op.urgencia === "alta",
                  "bg-amber-100 text-amber-700": op.urgencia === "media",
                  "bg-green-100 text-green-700": op.urgencia === "baja",
                })}>{op.urgencia}</span>
              </div>
              <div className="flex items-center gap-1 px-3 pb-2 border-t border-violet-50">
                {(["pdf", "pptx", "briefing"] as const).map((tipo) => {
                  const key = `${tipo}-${op.producto}`
                  const Icono = tipo === "pdf" ? FileText : tipo === "pptx" ? Presentation : Mic
                  const titulo = tipo === "pdf" ? "PDF" : tipo === "pptx" ? "Deck" : "Audio"
                  return (
                    <button key={tipo} disabled={!!lanzando}
                      onClick={() => lanzarJob(key, tipo, () => {
                        const fn = tipo === "pdf" ? api.documentosJobs.generarPdf : tipo === "pptx" ? api.documentosJobs.generarPptx : api.documentosJobs.generarBriefing
                        return fn(cuentaId, { contexto: op.producto, contextoTipo: "cuenta", contextoId: cuentaId })
                      })}
                      className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded border border-violet-200 text-violet-600 hover:bg-violet-100 disabled:opacity-40 transition-colors mt-1">
                      {lanzando === key ? <span className="w-2.5 h-2.5 border border-current border-t-transparent rounded-full animate-spin" /> : <Icono size={9} />}
                      {titulo}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
          {estudioIa.analisis.mensaje && (
            <p className="text-xs text-violet-700 italic">&quot;{estudioIa.analisis.mensaje}&quot;</p>
          )}
          <button
            onClick={() => lanzarJob("estudio_ia", "estudio_ia", () => api.documentosJobs.generarEstudioIa(cuentaId))}
            disabled={!!lanzando}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 text-white text-xs font-medium rounded-lg hover:bg-violet-700 disabled:opacity-50 transition-colors"
          >
            {lanzando === "estudio_ia" ? <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Sparkles size={12} />}
            Actualizar análisis
          </button>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-center h-32 text-zinc-400 text-sm bg-zinc-50 rounded-xl border border-zinc-200">
            Sin inteligencia de cross-selling para esta cuenta.
          </div>
          <div className="bg-violet-50 border border-violet-200 rounded-xl p-4">
            <p className="text-sm font-semibold text-violet-800 mb-1">Generar estudio con IC</p>
            <p className="text-xs text-violet-600 mb-3">IC analizará la cuenta y detectará oportunidades de cross-selling.</p>
            <button
              onClick={() => lanzarJob("estudio_ia", "estudio_ia", () => api.documentosJobs.generarEstudioIa(cuentaId))}
              disabled={!!lanzando}
              className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white text-sm font-medium rounded-lg hover:bg-violet-700 disabled:opacity-50 transition-colors"
            >
          {lanzando === "estudio_ia" ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Sparkles size={16} />
          )}
          Analizar con IC
            </button>
          </div>
        </>
      )}
    </div>
  )

  return (
    <div className="space-y-5">
      {/* Botones IC */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => lanzarJob("estudio_ia", "estudio_ia", () => api.documentosJobs.generarEstudioIa(cuentaId))}
          disabled={!!lanzando}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 text-white text-xs font-medium rounded-lg hover:bg-violet-700 disabled:opacity-50 transition-colors"
        >
          {lanzando === "estudio_ia" ? <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Sparkles size={13} />}
          Actualizar estudio IC
        </button>
        <button
          onClick={() => lanzarJob("pdf", "pdf", () => api.documentosJobs.generarPdf(cuentaId))}
          disabled={!!lanzando}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 text-white text-xs font-medium rounded-lg hover:bg-zinc-900 disabled:opacity-50 transition-colors"
        >
          {lanzando === "pdf" ? <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <FileText size={13} />}
          Informe PDF
        </button>
        <button
          onClick={() => lanzarJob("pptx", "pptx", () => api.documentosJobs.generarPptx(cuentaId))}
          disabled={!!lanzando}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 text-white text-xs font-medium rounded-lg hover:bg-zinc-900 disabled:opacity-50 transition-colors"
        >
          {lanzando === "pptx" ? <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Presentation size={13} />}
          Presentación
        </button>
        <button
          onClick={() => lanzarJob("briefing", "briefing", () => api.documentosJobs.generarBriefing(cuentaId))}
          disabled={!!lanzando}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 text-white text-xs font-medium rounded-lg hover:bg-zinc-900 disabled:opacity-50 transition-colors"
        >
          {lanzando === "briefing" ? <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Mic size={13} />}
          Briefing voz
        </button>
      </div>

      {/* Estudio IC generado */}
      {estudioIa && (
        <div className="bg-violet-50 border border-violet-200 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-violet-800 flex items-center gap-1.5">
              <Sparkles size={13} /> Análisis IC
            </p>
            <span className="text-[10px] text-violet-500">{new Date(estudioIa.creado_en).toLocaleDateString("es-ES")}</span>
          </div>
          <p className="text-sm text-violet-900">{estudioIa.analisis.resumen}</p>
          <div className="space-y-1.5">
            {estudioIa.analisis.oportunidades?.map((op, i) => (
              <div key={i} className="bg-white rounded-lg border border-violet-100 overflow-hidden">
                <div className="flex items-center justify-between px-3 py-2">
                  <span className="text-xs font-medium text-zinc-800">{op.producto}</span>
                  <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full", {
                    "bg-red-100 text-red-700": op.urgencia === "alta",
                    "bg-amber-100 text-amber-700": op.urgencia === "media",
                    "bg-green-100 text-green-700": op.urgencia === "baja",
                  })}>{op.urgencia}</span>
                </div>
                <div className="flex items-center gap-1 px-3 pb-2 border-t border-violet-50">
                  {(["pdf", "pptx", "briefing"] as const).map((tipo) => {
                    const key = `${tipo}-${op.producto}`
                    const Icono = tipo === "pdf" ? FileText : tipo === "pptx" ? Presentation : Mic
                    const titulo = tipo === "pdf" ? "PDF" : tipo === "pptx" ? "Deck" : "Audio"
                    return (
                      <button key={tipo} disabled={!!lanzando}
                        onClick={() => lanzarJob(key, tipo, () => {
                          const fn = tipo === "pdf" ? api.documentosJobs.generarPdf : tipo === "pptx" ? api.documentosJobs.generarPptx : api.documentosJobs.generarBriefing
                          return fn(cuentaId, { contexto: op.producto, contextoTipo: "cuenta", contextoId: cuentaId })
                        })}
                        className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded border border-violet-200 text-violet-600 hover:bg-violet-100 disabled:opacity-40 transition-colors mt-1">
                        {lanzando === key ? <span className="w-2.5 h-2.5 border border-current border-t-transparent rounded-full animate-spin" /> : <Icono size={9} />}
                        {titulo}
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
          {estudioIa.analisis.mensaje && (
            <p className="text-xs text-violet-700 italic">&quot;{estudioIa.analisis.mensaje}&quot;</p>
          )}
        </div>
      )}

    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Izquierda: meta */}
      <div className="space-y-4">
        <div className="bg-white rounded-xl border border-zinc-200 p-4 space-y-3">
          <div className="flex flex-wrap gap-2">
            {data.sbu && (
              <span className="text-[11px] font-medium px-2.5 py-1 rounded-full bg-blue-100 text-blue-700">{data.sbu}</span>
            )}
            {data.confianza && (
              <span className={cn("text-[11px] font-medium px-2.5 py-1 rounded-full", CONFIANZA_COLOR[data.confianza])}>
                Confianza: {data.confianza}
              </span>
            )}
            {data.ranking_accionable && (
              <span className="text-[11px] font-medium px-2.5 py-1 rounded-full bg-sgs-rojo/10 text-sgs-rojo">
                #{data.ranking_accionable} ranking
              </span>
            )}
          </div>

          {data.servicio_actual && (
            <div>
              <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide mb-1">Servicio actual</p>
              <p className="text-sm text-zinc-700">{data.servicio_actual}</p>
            </div>
          )}

          {data.oportunidades_top && (
            <div>
              <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide mb-1">Oportunidades top</p>
              <p className="text-sm text-zinc-700 whitespace-pre-line leading-relaxed">{data.oportunidades_top}</p>
            </div>
          )}
        </div>

        {(data.sector_osint || data.trigger_activador) && (
          <div className="bg-white rounded-xl border border-zinc-200 p-4 space-y-2">
            <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">Contexto de mercado</p>
            {data.sector_osint && (
              <p className="text-sm text-zinc-700"><span className="font-medium">Sector:</span> {data.sector_osint}</p>
            )}
            {data.trigger_activador && (
              <p className="text-sm text-zinc-700"><span className="font-medium">Trigger:</span> {data.trigger_activador}</p>
            )}
          </div>
        )}
      </div>

      {/* Derecha: mensaje accionable */}
      <div className="space-y-4">
        {data.mensaje_comercial && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
            <p className="text-[10px] font-semibold text-blue-500 uppercase tracking-wide mb-2">Mensaje sugerido por IC</p>
            <p className="text-sm text-blue-900 italic leading-relaxed">{data.mensaje_comercial}</p>
          </div>
        )}

        {data.preguntas_discovery && (
          <div className="bg-white rounded-xl border border-zinc-200 p-4">
            <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide mb-3">Preguntas de discovery</p>
            <div className="space-y-2">
              {data.preguntas_discovery.split(/\d\)/).filter(Boolean).map((q, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-[11px] font-bold text-sgs-rojo shrink-0 mt-0.5">{i + 1})</span>
                  <p className="text-sm text-zinc-700">{q.trim()}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
    </div>
  )
}

// ─── Helpers: reproductores y visores ────────────────────────────────────────

function BriefingPlayer({ texto, cuentaId }: { texto: string; cuentaId: string }) {
  const queryClient = useQueryClient()
  const [estado, setEstado] = useState<"idle" | "playing" | "paused">("idle")
  const [generandoMp3, setGenerandoMp3] = useState(false)
  const [errorMp3, setErrorMp3] = useState<string | null>(null)
  const [mp3DocId, setMp3DocId] = useState<string | null>(null)
  const [mp3Nombre, setMp3Nombre] = useState<string | null>(null)
  const [mp3Url, setMp3Url] = useState<string | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)

  // Usando ref para evitar closures obsoletos en el loop de animación
  const dibujarRef = useRef<(activo: boolean) => void>(null!)
  dibujarRef.current = function dibujar(activo: boolean) {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    const { width, height } = canvas
    ctx.clearRect(0, 0, width, height)
    const n = 36, gap = 2, bw = (width - (n - 1) * gap) / n
    for (let i = 0; i < n; i++) {
      const amp = activo
        ? (Math.sin(Date.now() / 180 + i * 0.7) * 0.45 + 0.55) * height * 0.75
        : height * 0.06
      const x = i * (bw + gap), y = (height - amp) / 2
      const r = Math.min(2, bw / 2, amp / 2)
      ctx.fillStyle = activo ? "#7c3aed" : "#d4d4d8"
      // roundRect compatible con todos los navegadores
      ctx.beginPath()
      ctx.moveTo(x + r, y)
      ctx.arcTo(x + bw, y, x + bw, y + amp, r)
      ctx.arcTo(x + bw, y + amp, x, y + amp, r)
      ctx.arcTo(x, y + amp, x, y, r)
      ctx.arcTo(x, y, x + bw, y, r)
      ctx.closePath()
      ctx.fill()
    }
    if (activo) animRef.current = requestAnimationFrame(() => dibujarRef.current(activo))
  }

  useEffect(() => {
    dibujarRef.current(false)
    return () => { window.speechSynthesis?.cancel(); cancelAnimationFrame(animRef.current) }
  }, [])

  async function generarMp3() {
    setGenerandoMp3(true)
    setErrorMp3(null)
    try {
      const res = await api.voice.generarAudioMp3(cuentaId)
      setMp3DocId(res.doc_id)
      setMp3Nombre(res.nombre_fichero ?? `briefing_${cuentaId.slice(0, 8)}.mp3`)
      const blob = await api.historial.blob(res.doc_id)
      const url = URL.createObjectURL(blob)
      setMp3Url(url)
      queryClient.invalidateQueries({ queryKey: ["historial-cuenta", cuentaId] })
    } catch (e) {
      setErrorMp3(e instanceof Error ? e.message : "Error generando el audio MP3")
    } finally {
      setGenerandoMp3(false)
    }
  }

  function play() {
    if (!("speechSynthesis" in window)) return
    window.speechSynthesis.cancel()
    cancelAnimationFrame(animRef.current)
    const utt = new SpeechSynthesisUtterance(texto)
    utt.lang = "es-ES"; utt.rate = 0.92
    utt.onend = () => { cancelAnimationFrame(animRef.current); dibujarRef.current(false); setEstado("idle") }
    utt.onerror = () => { cancelAnimationFrame(animRef.current); dibujarRef.current(false); setEstado("idle") }
    window.speechSynthesis.speak(utt)
    setEstado("playing"); dibujarRef.current(true)
  }
  function pause() { window.speechSynthesis.pause(); cancelAnimationFrame(animRef.current); dibujarRef.current(false); setEstado("paused") }
  function resume() { window.speechSynthesis.resume(); setEstado("playing"); dibujarRef.current(true) }
  function stop() { window.speechSynthesis.cancel(); cancelAnimationFrame(animRef.current); dibujarRef.current(false); setEstado("idle") }

  return (
    <div className="space-y-3">
      <div className="bg-violet-50 rounded-xl border border-violet-200 p-4 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Volume2 size={14} className="text-violet-600" />
            <p className="text-xs font-semibold text-violet-800">Reproductor de briefing</p>
          </div>
          {!mp3Url && (
            <button
              onClick={generarMp3}
              disabled={generandoMp3}
              className="flex items-center gap-1.5 px-2.5 py-1 bg-violet-600 text-white text-[11px] font-medium rounded-lg hover:bg-violet-700 disabled:opacity-60 transition-colors"
              title="Generar audio MP3 descargable"
            >
              <Mic size={11} />
              {generandoMp3 ? "Generando MP3…" : "Generar MP3"}
            </button>
          )}
        </div>
        {errorMp3 && (
          <p className="text-[11px] text-red-600 bg-red-50 px-3 py-1.5 rounded-lg border border-red-100">{errorMp3}</p>
        )}
        <canvas ref={canvasRef} width={400} height={48} className="w-full rounded-lg bg-white border border-violet-100" />
        <div className="flex items-center gap-2">
          {estado !== "playing" && (
            <button onClick={estado === "paused" ? resume : play}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 text-white text-xs font-medium rounded-lg hover:bg-violet-700 transition-colors">
              <Play size={12} fill="currentColor" /> {estado === "paused" ? "Continuar" : "Escuchar"}
            </button>
          )}
          {estado === "playing" && (
            <button onClick={pause}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 text-white text-xs font-medium rounded-lg hover:bg-amber-600 transition-colors">
              <Pause size={12} fill="currentColor" /> Pausar
            </button>
          )}
          {estado !== "idle" && (
            <button onClick={stop}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-zinc-200 text-zinc-600 text-xs font-medium rounded-lg hover:bg-zinc-50 transition-colors">
              <Square size={12} fill="currentColor" /> Detener
            </button>
          )}
        </div>
      </div>

      {mp3Url && (
        <div className="bg-white rounded-xl border border-violet-100 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">Audio MP3 generado</p>
            {mp3DocId && mp3Nombre && (
              <button
                onClick={() => api.historial.descargar(mp3DocId, mp3Nombre)}
                className="flex items-center gap-1 text-[11px] text-violet-600 hover:text-violet-800 font-medium transition-colors"
              >
                <Download size={11} /> Descargar MP3
              </button>
            )}
          </div>
          <audio controls src={mp3Url} className="w-full" />
          <p className="text-[10px] text-zinc-400">El audio también aparece en la pestaña Documentos.</p>
        </div>
      )}

      <div className="bg-white rounded-xl border border-zinc-200 p-4 max-h-80 overflow-y-auto">
        <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide mb-2">Script</p>
        <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-wrap">{texto}</p>
      </div>
    </div>
  )
}

function VisorSlides({ docId }: { docId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["slides", docId],
    queryFn: () => api.historial.slides(docId),
    staleTime: Infinity,
  })
  const [idx, setIdx] = useState(0)

  if (isLoading) return <SpinnerCentrado />
  if (!data?.slides.length) return (
    <div className="flex items-center justify-center h-48 text-zinc-400 text-sm">Sin diapositivas extraídas</div>
  )
  const slide = data.slides[idx]
  return (
    <div className="space-y-3">
      <div className="bg-zinc-900 rounded-xl p-6 min-h-48 relative overflow-hidden">
        <span className="absolute top-3 right-3 text-[10px] text-zinc-500 font-mono tabular-nums">{idx + 1}/{data.total}</span>
        {slide.titulo && <h3 className="text-white font-bold text-base mb-3 leading-snug pr-12">{slide.titulo}</h3>}
        {slide.cuerpo && <p className="text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap">{slide.cuerpo}</p>}
        {slide.notas && (
          <div className="mt-4 pt-3 border-t border-zinc-700">
            <p className="text-[10px] text-zinc-500 uppercase tracking-wide mb-1">Notas del presentador</p>
            <p className="text-zinc-400 text-xs">{slide.notas}</p>
          </div>
        )}
      </div>
      <div className="flex items-center gap-1 flex-wrap">
        {data.slides.map((_, i) => (
          <button key={i} onClick={() => setIdx(i)}
            className={cn("w-7 h-7 text-[10px] font-semibold rounded-lg transition-colors",
              i === idx ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-500 hover:bg-zinc-200")}>
            {i + 1}
          </button>
        ))}
      </div>
    </div>
  )
}

function VisorPDF({ docId }: { docId: string }) {
  const [url, setUrl] = useState<string | null>(null)
  const [err, setErr] = useState(false)
  useEffect(() => {
    let activa = true
    let objectUrl: string | null = null
    api.historial
      .blob(docId)
      .then((blob) => {
        if (!activa) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      })
      .catch(() => setErr(true))
    return () => {
      activa = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [docId])
  if (err) return <div className="flex items-center justify-center h-48 text-zinc-400 text-sm">No se pudo generar la URL</div>
  if (!url) return <SpinnerCentrado />
  return (
    <div className="space-y-2">
      <iframe src={url} className="w-full rounded-xl border border-zinc-200" style={{ height: 500 }} title="Vista previa PDF" />
      <a href={url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-xs text-blue-600 hover:underline">
        <Download size={12} /> Abrir en nueva pestaña
      </a>
    </div>
  )
}

function VisorAudio({ docId }: { docId: string }) {
  const [url, setUrl] = useState<string | null>(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    setCargando(true)
    api.historial.blob(docId)
      .then((blob) => { setUrl(URL.createObjectURL(blob)) })
      .catch(() => {})
      .finally(() => setCargando(false))
    return () => { if (url) URL.revokeObjectURL(url) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docId])

  if (cargando) return <SpinnerCentrado />
  if (!url) return <div className="flex items-center justify-center h-24 text-zinc-400 text-sm">No se pudo cargar el audio</div>
  return (
    <div className="bg-violet-50 rounded-xl border border-violet-200 p-4 space-y-2">
      <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">Audio MP3</p>
      <audio controls src={url} className="w-full" />
    </div>
  )
}

function VistaGenerado({ doc, cuentaId }: { doc: DocHistorial; cuentaId: string }) {
  const [texto, setTexto] = useState<string | null>(null)
  const [cargando, setCargando] = useState(false)
  useEffect(() => {
    if (doc.tipo === "briefing") {
      setCargando(true)
      api.historial.texto(doc.id).then((r) => setTexto(r.texto ?? null)).finally(() => setCargando(false))
    }
  }, [doc.id, doc.tipo])

  if (doc.tipo === "pdf") return <VisorPDF docId={doc.id} />
  if (doc.tipo === "pptx") return <VisorSlides docId={doc.id} />
  if (doc.tipo === "audio") return <VisorAudio docId={doc.id} />
  if (doc.tipo === "briefing") {
    if (cargando) return <SpinnerCentrado />
    if (texto) return <BriefingPlayer texto={texto} cuentaId={cuentaId} />
    return <div className="flex items-center justify-center h-48 text-zinc-400 text-sm">Sin contenido</div>
  }
  return (
    <div className="flex flex-col items-center justify-center gap-3 h-48 text-zinc-400">
      <FileText size={32} className="text-zinc-200" />
      <p className="text-sm">Descarga para ver el contenido</p>
    </div>
  )
}

// ─── Tab: Inteligencia & Documentos ──────────────────────────────────────────

type ItemSeleccionado =
  | { fuente: "archivo"; doc: ArchivoDoc }
  | { fuente: "generado"; doc: DocHistorial }

function TabIA({ cuentaId }: { cuentaId: string }) {
  const queryClient = useQueryClient()
  const { lanzar } = useDocumentoJob()
  const [lanzando, setLanzando] = useState<string | null>(null)

  // Investigación
  const { data: investigacion, isLoading: cargandoInv, refetch: refetchInv } = useQuery({
    queryKey: ["investigacion", cuentaId],
    queryFn: () => api.investigacion.estado(cuentaId),
    retry: false,
  })
  const [invExpandida, setInvExpandida] = useState(false)

  // Archivos subidos
  const { data: archivos = [], isLoading: cargandoArchivos } = useQuery<ArchivoDoc[]>({
    queryKey: ["archivos-cuenta", cuentaId],
    queryFn: () => api.archivosCuenta.listar(cuentaId),
  })

  // Generados por IC
  const { data: generados = [] } = useQuery<DocHistorial[]>({
    queryKey: ["historial-cuenta", cuentaId],
    queryFn: () => api.historial.listar({ cuentaId }),
  })

  // Selección activa
  const [seleccion, setSeleccion] = useState<ItemSeleccionado | null>(null)
  const archivoSeleccionadoId = seleccion?.fuente === "archivo" ? seleccion.doc.id : null
  const archivoSeleccionadoTieneTexto = seleccion?.fuente === "archivo" ? Boolean(seleccion.doc.tiene_texto) : false

  // Chat para archivos subidos
  const [mensajes, setMensajes] = useState<MensajeChat[]>([])
  const [textoDoc, setTextoDoc] = useState<string | null>(null)
  const [inputChat, setInputChat] = useState("")
  const [streamingRespuesta, setStreamingRespuesta] = useState("")
  const [chateando, setChateando] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Upload
  const [subiendo, setSubiendo] = useState(false)
  const [errorSubida, setErrorSubida] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const [errorChat, setErrorChat] = useState<string | null>(null)

  // Reset al cambiar selección
  const selKey = seleccion?.fuente === "archivo" ? seleccion.doc.id : seleccion?.fuente ?? null
  useEffect(() => {
    setMensajes([]); setTextoDoc(null); setInputChat(""); setErrorChat(null)
    if (archivoSeleccionadoId && archivoSeleccionadoTieneTexto) {
      api.archivosCuenta.contenido(cuentaId, archivoSeleccionadoId).then(r => setTextoDoc(r.texto))
    }
  }, [selKey, cuentaId, archivoSeleccionadoId, archivoSeleccionadoTieneTexto])

  // Auto-expandir investigación si hay datos
  useEffect(() => {
    if (investigacion?.estado === "completada") setInvExpandida(true)
  }, [investigacion?.estado])

  async function lanzarJob(id: string, tipo: Parameters<typeof lanzar>[0], fn: Parameters<typeof lanzar>[1]) {
    setLanzando(id)
    try {
      await lanzar(tipo, fn, () => {
        queryClient.invalidateQueries({ queryKey: ["investigacion", cuentaId] })
        queryClient.invalidateQueries({ queryKey: ["historial-cuenta", cuentaId] })
      })
    } finally { setLanzando(null) }
  }

  const handleArchivos = useCallback(async (lista: FileList | null) => {
    if (!lista?.length) return
    setErrorSubida(null)
    setSubiendo(true)
    try {
      for (const f of Array.from(lista)) await api.archivosCuenta.subir(cuentaId, f)
      queryClient.invalidateQueries({ queryKey: ["archivos-cuenta", cuentaId] })
    } catch (e) {
      const msg = e instanceof Error ? e.message : "No se pudo subir el archivo."
      setErrorSubida(msg)
    } finally { setSubiendo(false) }
  }, [cuentaId, queryClient])

  async function enviarMensaje() {
    if (!inputChat.trim() || chateando || seleccion?.fuente !== "archivo") return
    setErrorChat(null)
    const docId = seleccion.doc.id
    const userMsg: MensajeChat = { role: "user", content: inputChat.trim() }
    const nuevosMensajes = [...mensajes, userMsg]
    setMensajes(nuevosMensajes); setInputChat(""); setChateando(true); setStreamingRespuesta("")
    try {
      const res = await api.ia.chatStreamCuenta(cuentaId, nuevosMensajes, undefined, docId)
      if (!res.ok) {
        const txt = await res.text()
        throw new Error(txt || `Error ${res.status} en chat IC`)
      }
      if (!res.body) return
      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let acc = ""
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        for (const linea of dec.decode(value).split("\n")) {
          const t = linea.replace(/^data: /, "").trim()
          if (!t || t === "[DONE]") continue
          if (t.startsWith("[ERROR]")) throw new Error(t.replace("[ERROR]", "").trim() || "Error en IC")
          acc += t; setStreamingRespuesta(acc)
        }
      }
      setMensajes([...nuevosMensajes, { role: "assistant", content: acc }])
      setStreamingRespuesta("")
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: "smooth" }), 50)
    } catch (e) {
      const msg = e instanceof Error ? e.message : "No se pudo completar el chat con IC."
      setErrorChat(msg)
      setMensajes([...nuevosMensajes, { role: "assistant", content: `Error: ${msg}` }])
      setStreamingRespuesta("")
    } finally { setChateando(false) }
  }

  const TIPO_LABEL: Record<string, string> = { pdf: "Informe PDF", pptx: "Presentación", briefing: "Briefing voz", audio: "Audio MP3", investigacion: "Investigación", propuesta: "Propuesta IC" }
  const TIPO_ICONO: Record<string, React.ReactNode> = {
    pdf: <FileText size={13} className="text-red-500 shrink-0" />,
    pptx: <Presentation size={13} className="text-orange-500 shrink-0" />,
    briefing: <Mic size={13} className="text-violet-600 shrink-0" />,
    audio: <Volume2 size={13} className="text-violet-500 shrink-0" />,
    investigacion: <Search size={13} className="text-blue-500 shrink-0" />,
    propuesta: <Brain size={13} className="text-emerald-600 shrink-0" />,
  }

  const ACCIONES = [
    { id: "investigar", tipo: "investigacion" as const, icono: Search, titulo: "Investigar empresa", color: "border-violet-200 bg-violet-50 text-violet-700 hover:bg-violet-100", fn: () => api.documentosJobs.iniciarInvestigacion(cuentaId) },
    { id: "pdf", tipo: "pdf" as const, icono: FileText, titulo: "Informe PDF", color: "border-red-100 bg-red-50 text-red-700 hover:bg-red-100", fn: () => api.documentosJobs.generarPdf(cuentaId) },
    { id: "pptx", tipo: "pptx" as const, icono: Presentation, titulo: "Presentación", color: "border-orange-100 bg-orange-50 text-orange-700 hover:bg-orange-100", fn: () => api.documentosJobs.generarPptx(cuentaId) },
    { id: "briefing", tipo: "briefing" as const, icono: Mic, titulo: "Briefing voz", color: "border-violet-100 bg-violet-50 text-violet-700 hover:bg-violet-100", fn: () => api.documentosJobs.generarBriefing(cuentaId) },
  ]

  return (
    <div className="space-y-5">

      {/* ACCIONES */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {ACCIONES.map((a) => {
          const Ico = a.icono
          const cargando = lanzando === a.id
          return (
            <button key={a.id} onClick={() => lanzarJob(a.id, a.tipo, a.fn)} disabled={!!lanzando}
              className={cn("flex flex-col items-start gap-2 p-4 rounded-xl border text-left transition-colors disabled:opacity-50", a.color)}>
              {cargando ? <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" /> : <Ico size={18} />}
              <p className="text-xs font-semibold leading-snug">{a.titulo}</p>
            </button>
          )
        })}
      </div>

      {/* INVESTIGACIÓN (colapsable) */}
      <div className="rounded-xl border border-zinc-200 overflow-hidden">
        <button onClick={() => setInvExpandida(!invExpandida)}
          className="w-full flex items-center justify-between px-4 py-3 bg-white hover:bg-zinc-50 transition-colors text-left">
          <div className="flex items-center gap-2">
            <Globe size={14} className="text-zinc-500" />
            <p className="text-xs font-semibold text-zinc-700">Investigación de empresa</p>
            {investigacion?.estado === "completada" && <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">Completada</span>}
            {investigacion?.estado === "procesando" && <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 flex items-center gap-1"><div className="w-2 h-2 border border-amber-600 border-t-transparent rounded-full animate-spin" />En curso</span>}
            {investigacion?.estado === "error" && <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-600">Error</span>}
          </div>
          {invExpandida ? <ChevronUp size={14} className="text-zinc-400" /> : <ChevronDown size={14} className="text-zinc-400" />}
        </button>

        {invExpandida && (
          <div className="border-t border-zinc-100 bg-zinc-50/60 p-4">
            {cargandoInv && <div className="flex justify-center py-6"><div className="w-5 h-5 border-2 border-zinc-300 border-t-transparent rounded-full animate-spin" /></div>}

            {!cargandoInv && (!investigacion || investigacion.estado === "error") && (
              <div className="space-y-2">
                {investigacion?.estado === "error" && (
                  <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                    <AlertCircle size={13} className="shrink-0" /> {investigacion.error_msg || "Error desconocido"}
                  </div>
                )}
                <p className="text-sm text-zinc-400 text-center py-6">Sin datos. Usa el botón &quot;Investigar empresa&quot; para analizar con IC.</p>
              </div>
            )}

            {!cargandoInv && investigacion?.estado === "procesando" && (
              <div className="flex flex-col items-center gap-2 py-6 text-zinc-400">
                <div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                <p className="text-sm">Analizando empresa con IC…</p>
                <button onClick={() => refetchInv()} className="text-xs text-violet-600 underline">Actualizar</button>
              </div>
            )}

            {!cargandoInv && investigacion?.estado === "completada" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] text-zinc-400">Completada {investigacion.completado_en ? new Date(investigacion.completado_en).toLocaleDateString("es-ES") : "—"}</p>
                  <button onClick={() => lanzarJob("investigar", "investigacion", () => api.documentosJobs.iniciarInvestigacion(cuentaId))}
                    className="flex items-center gap-1 px-3 py-1 bg-violet-600 text-white text-[11px] font-medium rounded-lg hover:bg-violet-700 transition-colors">
                    <Search size={11} /> Reinvestigar
                  </button>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="bg-white rounded-lg border border-zinc-200 p-3 space-y-1.5">
                    <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide flex items-center gap-1"><Globe size={10} /> Perfil</p>
                    {investigacion.sector && <p className="text-xs text-zinc-700"><span className="font-medium">Sector:</span> {investigacion.sector}</p>}
                    {investigacion.num_empleados && <p className="text-xs text-zinc-700"><span className="font-medium">Empleados:</span> {investigacion.num_empleados}</p>}
                    {investigacion.certificaciones_actuales?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {investigacion.certificaciones_actuales.map((c: string, i: number) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">{c}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  {investigacion.pain_points?.length > 0 && (
                    <div className="bg-white rounded-lg border border-zinc-200 p-3 space-y-1.5">
                      <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide flex items-center gap-1"><AlertCircle size={10} /> Pain points</p>
                      <ul className="space-y-1">
                        {investigacion.pain_points.slice(0, 4).map((pp: string, i: number) => (
                          <li key={i} className="text-xs text-zinc-600 flex gap-1.5"><span className="text-sgs-rojo font-bold shrink-0">·</span>{pp}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {investigacion.noticias_relevantes?.length > 0 && (
                    <div className="bg-white rounded-lg border border-zinc-200 p-3 space-y-1.5">
                      <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide flex items-center gap-1"><Newspaper size={10} /> Noticias</p>
                      <ul className="space-y-1">
                        {investigacion.noticias_relevantes.slice(0, 3).map((n: string, i: number) => (
                          <li key={i} className="text-xs text-zinc-600 flex gap-1.5"><span className="text-amber-500 font-bold shrink-0">·</span>{n}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {investigacion.oportunidades_detectadas?.length > 0 && (
                    <div className="bg-white rounded-lg border border-zinc-200 p-3 space-y-1.5">
                      <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide flex items-center gap-1"><Zap size={10} /> Oportunidades</p>
                      <ul className="space-y-1">
                        {investigacion.oportunidades_detectadas.slice(0, 4).map((o: string, i: number) => (
                          <li key={i} className="text-xs text-zinc-600 flex gap-1.5"><span className="text-emerald-500 font-bold shrink-0">·</span>{o}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* BIBLIOTECA + VISTA */}
      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4 items-start">

        {/* Columna izquierda: biblioteca */}
        <div className="space-y-4">
          {/* Upload drop zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); handleArchivos(e.dataTransfer.files) }}
            onClick={() => inputRef.current?.click()}
            className={cn("flex items-center gap-2 px-3 py-2.5 rounded-lg border-2 border-dashed cursor-pointer transition-colors",
              dragging ? "border-violet-400 bg-violet-50" : "border-zinc-200 bg-zinc-50 hover:bg-zinc-100")}>
            <input ref={inputRef} type="file" multiple accept=".pdf,.docx,.doc,.txt,.csv,.xlsx,.xls,.pptx,.ppt" className="hidden" onChange={(e) => handleArchivos(e.target.files)} />
            {subiendo ? <div className="w-4 h-4 border-2 border-violet-500 border-t-transparent rounded-full animate-spin shrink-0" /> : <Upload size={14} className="text-zinc-400 shrink-0" />}
            <p className="text-xs text-zinc-500">{subiendo ? "Subiendo…" : "Subir archivos"}</p>
          </div>
          {errorSubida && (
            <div className="px-3 py-2 rounded-lg border border-red-200 bg-red-50 text-xs text-red-700">
              Error al subir: {errorSubida}
            </div>
          )}

          {/* Generados por IC */}
          <div className="space-y-1">
            <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide flex items-center gap-1.5 px-1">
              <Sparkles size={10} /> Generados por IC
            </p>
            {generados.length === 0 ? (
              <p className="text-xs text-zinc-400 text-center py-3 bg-zinc-50 rounded-lg border border-zinc-100">Sin documentos generados</p>
            ) : generados.slice(0, 12).map((doc) => {
              const activo = seleccion?.fuente === "generado" && seleccion.doc.id === doc.id
              return (
                <div key={doc.id} onClick={() => setSeleccion({ fuente: "generado", doc })}
                  className={cn("flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer transition-colors group",
                    activo ? "border-zinc-700 bg-zinc-900" : "border-zinc-100 bg-white hover:bg-zinc-50")}>
                  {TIPO_ICONO[doc.tipo] ?? <FileText size={13} className="text-zinc-400 shrink-0" />}
                  <div className="min-w-0 flex-1">
                    <p className={cn("text-xs font-medium truncate", activo ? "text-white" : "text-zinc-700")}>{TIPO_LABEL[doc.tipo] ?? doc.tipo}</p>
                    <p className={cn("text-[10px]", activo ? "text-zinc-400" : "text-zinc-400")}>{doc.creado_en?.slice(0, 10)}</p>
                  </div>
                  <button
                    onClick={async (e) => {
                      e.stopPropagation()
                      if (doc.tipo === "audio") {
                        api.historial.descargar(doc.id, doc.nombre_fichero ?? `audio_${doc.id}.mp3`)
                      } else {
                        await api.historial.abrir(doc.id)
                      }
                    }}
                    className={cn("shrink-0 opacity-0 group-hover:opacity-100 transition-opacity", activo ? "text-zinc-400 hover:text-white" : "text-zinc-400 hover:text-zinc-700")}
                    title={doc.tipo === "audio" ? "Descargar MP3" : "Abrir"}>
                    <Download size={12} />
                  </button>
                </div>
              )
            })}
          </div>

          {/* Archivos subidos */}
          <div className="space-y-1">
            <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide flex items-center gap-1.5 px-1">
              <FolderOpen size={10} /> Tus archivos
            </p>
            {cargandoArchivos ? (
              <div className="h-16 flex items-center justify-center"><div className="w-4 h-4 border-2 border-zinc-300 border-t-transparent rounded-full animate-spin" /></div>
            ) : archivos.length === 0 ? (
              <p className="text-xs text-zinc-400 text-center py-3 bg-zinc-50 rounded-lg border border-zinc-100">Sin archivos subidos</p>
            ) : archivos.map((doc) => {
              const activo = seleccion?.fuente === "archivo" && seleccion.doc.id === doc.id
              return (
                <div key={doc.id} onClick={() => setSeleccion({ fuente: "archivo", doc })}
                  className={cn("flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer transition-colors group",
                    activo ? "border-violet-300 bg-violet-50" : "border-zinc-100 bg-white hover:bg-zinc-50")}>
                  {iconoTipo(doc.tipo_mime)}
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-zinc-800 truncate">{doc.nombre_original}</p>
                    <p className="text-[10px] text-zinc-400">{fmtBytes(doc.tamaño_bytes)}</p>
                  </div>
                  {doc.tiene_texto && <span className="text-[9px] bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded font-semibold shrink-0">IC</span>}
                  <button onClick={(e) => { e.stopPropagation(); api.archivosCuenta.descargar(cuentaId, doc.id, doc.nombre_original) }}
                    className="text-zinc-300 hover:text-zinc-600 opacity-0 group-hover:opacity-100 shrink-0 transition-all" title="Descargar">
                    <Download size={12} />
                  </button>
                  <button onClick={async (e) => { e.stopPropagation(); await api.archivosCuenta.eliminar(cuentaId, doc.id); queryClient.invalidateQueries({ queryKey: ["archivos-cuenta", cuentaId] }); if (activo) setSeleccion(null) }}
                    className="text-zinc-300 hover:text-red-500 opacity-0 group-hover:opacity-100 shrink-0 transition-all" title="Eliminar">
                    <Trash2 size={12} />
                  </button>
                </div>
              )
            })}
          </div>
        </div>

        {/* Columna derecha: vista previa */}
        <div className="min-h-[400px]">
          {!seleccion ? (
            <div className="h-full flex flex-col items-center justify-center gap-3 p-10 bg-zinc-50 rounded-xl border border-dashed border-zinc-200 text-zinc-400 min-h-[400px]">
              <Bot size={32} className="text-zinc-300" />
              <p className="text-sm font-medium text-zinc-500">Selecciona un documento</p>
              <p className="text-xs text-center leading-relaxed">Documentos IC → previsualización directa<br />Tus archivos → extracción de texto y chat</p>
            </div>

          ) : seleccion.fuente === "generado" ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2">
                  {TIPO_ICONO[seleccion.doc.tipo]}
                  <p className="text-sm font-semibold text-zinc-800">{TIPO_LABEL[seleccion.doc.tipo] ?? seleccion.doc.tipo}</p>
                  <span className="text-xs text-zinc-400">{seleccion.doc.creado_en?.slice(0, 10)}</span>
                </div>
                <button onClick={() => setSeleccion(null)} className="text-zinc-400 hover:text-zinc-700 transition-colors"><X size={14} /></button>
              </div>
              <VistaGenerado doc={seleccion.doc} cuentaId={cuentaId} />
            </div>

          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2 min-w-0">
                  {iconoTipo(seleccion.doc.tipo_mime)}
                  <p className="text-xs font-semibold text-zinc-800 truncate max-w-[160px] sm:max-w-[300px]">{seleccion.doc.nombre_original}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button onClick={() => api.archivosCuenta.descargar(cuentaId, seleccion.doc.id, seleccion.doc.nombre_original)}
                    className="text-zinc-400 hover:text-zinc-700 transition-colors" title="Descargar"><Download size={13} /></button>
                  <button onClick={() => setSeleccion(null)} className="text-zinc-400 hover:text-zinc-700 transition-colors"><X size={13} /></button>
                </div>
              </div>

              {seleccion.doc.tiene_texto && (
                <div className="bg-zinc-50 rounded-lg border border-zinc-200 px-3 py-2 max-h-36 overflow-y-auto">
                  <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide mb-1">Contenido extraído</p>
                  <p className="text-[11px] text-zinc-600 leading-relaxed font-mono whitespace-pre-wrap">{textoDoc || "Cargando…"}</p>
                </div>
              )}
              {!seleccion.doc.tiene_texto && (
                <div className="px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
                  Sin texto extraíble. El chat usará el contexto de la cuenta.
                </div>
              )}

              {/* Chat */}
              <div className="bg-white rounded-xl border border-zinc-200 flex flex-col" style={{ minHeight: 320 }}>
                <div className="px-3 py-2 border-b border-zinc-100 flex items-center gap-1.5">
                  <Bot size={13} className="text-violet-600" />
                  <p className="text-xs font-semibold text-zinc-700">Chat con el documento</p>
                </div>
                {errorChat && (
                  <div className="mx-3 mt-2 px-2.5 py-2 rounded-lg border border-red-200 bg-red-50 text-xs text-red-700">
                    {errorChat}
                  </div>
                )}
                <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2 max-h-56">
                  {mensajes.length === 0 && !streamingRespuesta && (
                    <div className="flex items-center justify-center h-full text-[11px] text-zinc-400 py-10">
                      Haz una pregunta sobre el documento
                    </div>
                  )}
                  {mensajes.map((m, i) => (
                    <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                      <div className={cn("max-w-[85%] px-3 py-2 rounded-xl text-xs leading-relaxed",
                        m.role === "user" ? "bg-violet-600 text-white rounded-br-sm" : "bg-zinc-100 text-zinc-800 rounded-bl-sm")}>
                        {m.content}
                      </div>
                    </div>
                  ))}
                  {streamingRespuesta && (
                    <div className="flex justify-start">
                      <div className="max-w-[85%] px-3 py-2 rounded-xl rounded-bl-sm text-xs leading-relaxed bg-zinc-100 text-zinc-800">
                        {streamingRespuesta}<span className="inline-block w-1 h-3 ml-0.5 bg-zinc-400 animate-pulse" />
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>
                <div className="px-3 py-2 border-t border-zinc-100 flex gap-2">
                  <input value={inputChat} onChange={(e) => setInputChat(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviarMensaje() } }}
                    placeholder="Pregunta sobre el documento…" disabled={chateando}
                    className="flex-1 text-xs px-3 py-1.5 rounded-lg border border-zinc-200 focus:outline-none focus:border-violet-400 disabled:opacity-50" />
                  <button onClick={enviarMensaje} disabled={chateando || !inputChat.trim()}
                    className="p-1.5 rounded-lg bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-40 transition-colors">
                    {chateando ? <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <SendHorizontal size={14} />}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-4">
        <div className="mb-3">
          <h4 className="text-sm font-semibold text-zinc-900">Repositorio IC de la cuenta</h4>
          <p className="text-xs text-zinc-500 mt-1">
            Consulta y previsualiza todo lo generado por Inteligencia Comercial vinculado a esta cuenta.
          </p>
        </div>
        <ArtefactoPicker contextoTipo="cuenta" contextoId={cuentaId} modoModal />
      </div>
    </div>
  )
}

// ─── Tab: Reunión 360 ─────────────────────────────────────────────────────────

function TabReunion({ cuentaId }: { cuentaId: string }) {
  const [preguntas, setPreguntas] = useState<string[]>([])
  const [cargandoPreguntas, setCargandoPreguntas] = useState(false)
  const [errorPreguntas, setErrorPreguntas] = useState<string | null>(null)

  const { data, isLoading, isError } = useQuery<FichaReunion>({
    queryKey: ["reunion-360", cuentaId],
    queryFn: () => api.reuniones.preparar(cuentaId) as Promise<FichaReunion>,
    retry: false,
  })

  async function generarPreguntas() {
    setCargandoPreguntas(true)
    setErrorPreguntas(null)
    try {
      const resp = await api.reuniones.preguntas(cuentaId)
      setPreguntas((resp as { preguntas?: string[] }).preguntas ?? [])
    } catch (err) {
      setErrorPreguntas(err instanceof Error ? err.message : "No se pudieron generar las preguntas.")
    } finally {
      setCargandoPreguntas(false)
    }
  }

  if (isLoading) return <SpinnerCentrado />
  if (isError || !data) return (
    <div className="flex items-center justify-center h-48 text-zinc-400 text-sm">
      No se pudo cargar la ficha 360.
    </div>
  )

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Contexto */}
      <div className="space-y-4">
        <div className="bg-white rounded-xl border border-zinc-200 p-4 space-y-3">
          <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">Contexto de cuenta</p>
          <div className="space-y-2">
            <p className="text-sm text-zinc-700"><span className="font-medium">Sector:</span> {data.cuenta.sector ?? "N/D"}</p>
            <p className="text-sm text-zinc-700"><span className="font-medium">Empleados:</span> {data.cuenta.num_empleados ?? "N/D"}</p>
            {data.investigacion.pain_points.length > 0 && (
              <div>
                <p className="text-sm font-medium text-zinc-700 mb-1">Pain points:</p>
                <ul className="space-y-1">
                  {data.investigacion.pain_points.slice(0, 3).map((pp, i) => (
                    <li key={i} className="text-sm text-zinc-600 flex gap-2">
                      <span className="text-sgs-rojo shrink-0">·</span>{pp}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-zinc-200 p-4 space-y-2">
          <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">Estado pipeline</p>
          <p className="text-sm text-zinc-700">Activas: <span className="font-semibold">{data.pipeline.activas}</span></p>
          <p className="text-sm text-zinc-700">Importe: <span className="font-semibold">{fmtEUR.format(data.pipeline.importe_total)}</span></p>
          {data.pipeline.etapa_critica && (
            <p className="text-sm text-zinc-700">Etapa crítica: <span className="font-semibold">{ETAPA_LABEL[data.pipeline.etapa_critica] ?? data.pipeline.etapa_critica}</span></p>
          )}
          <p className="text-sm text-zinc-700">Score medio: <span className="font-semibold">{data.score_medio}</span></p>
        </div>

        {/* Materiales */}
        <div className="bg-white rounded-xl border border-zinc-200 p-4">
          <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide mb-3">Materiales disponibles</p>
          <div className="flex gap-2 flex-wrap">
            {[
              { label: "Deck", ok: data.materiales.deck_disponible },
              { label: "PDF", ok: data.materiales.pdf_disponible },
              { label: "Briefing audio", ok: data.materiales.briefing_disponible },
            ].map(({ label, ok }) => (
              <span key={label} className={cn(
                "text-[11px] font-medium px-3 py-1 rounded-full",
                ok ? "bg-emerald-100 text-emerald-700" : "bg-zinc-100 text-zinc-400"
              )}>
                {ok ? "✓ " : "— "}{label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Preguntas IC */}
      <div className="space-y-4">
        <div className="bg-white rounded-xl border border-zinc-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">Preguntas de calificación</p>
            <button
              onClick={generarPreguntas}
              disabled={cargandoPreguntas}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium rounded-lg border border-zinc-200 text-zinc-700 hover:bg-zinc-50 disabled:opacity-50 transition-colors"
            >
              {cargandoPreguntas ? (
                <span className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
              ) : (
                <Sparkles size={12} />
              )}
              {cargandoPreguntas ? "Generando..." : "Generar con IC"}
            </button>
          </div>

          {errorPreguntas && (
            <p className="text-[11px] text-red-600 mb-2">{errorPreguntas}</p>
          )}

          {preguntas.length === 0 ? (
            <p className="text-sm text-zinc-400">Pulsa &quot;Generar con IC&quot; para obtener preguntas personalizadas de calificación.</p>
          ) : (
            <div className="space-y-2">
              {preguntas.map((pregunta, idx) => (
                <div key={idx} className="flex gap-2.5">
                  <span className="text-[11px] font-bold text-sgs-rojo shrink-0 mt-0.5">{idx + 1})</span>
                  <p className="text-sm text-zinc-700">{pregunta}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Próximos pasos */}
        {data.seguimientos.length > 0 && (
          <div className="bg-white rounded-xl border border-zinc-200 p-4">
            <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide mb-3">Próximos pasos</p>
            <div className="space-y-2">
              {data.seguimientos.slice(0, 5).map((s) => (
                <div key={s.id} className="rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2">
                  <p className="text-sm font-medium text-zinc-800">{s.titulo}</p>
                  <p className="text-xs text-zinc-500 mt-0.5">{s.fecha_vencimiento}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Tab: Archivos & Documentos ───────────────────────────────────────────────

type ArchivoDoc = {
  id: string; nombre_original: string; tipo_mime: string | null
  tamaño_bytes: number | null; creado_en: string; tiene_texto: boolean
}

type DocHistorial = import("@/types").DocumentoHistorial

type MensajeChat = { role: "user" | "assistant"; content: string }

function fmtBytes(b: number | null) {
  if (!b) return "—"
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}

function iconoTipo(mime: string | null) {
  if (!mime) return <FileText size={14} className="text-zinc-400" />
  if (mime.includes("pdf")) return <FileText size={14} className="text-red-500" />
  if (mime.includes("word") || mime.includes("docx")) return <FileText size={14} className="text-blue-500" />
  if (mime.includes("sheet") || mime.includes("excel")) return <FileText size={14} className="text-green-600" />
  if (mime.includes("presentation") || mime.includes("pptx")) return <FileText size={14} className="text-orange-500" />
  return <FileText size={14} className="text-zinc-400" />
}



// ─── Spinner ──────────────────────────────────────────────────────────────────

function SpinnerCentrado() {
  return (
    <div className="flex items-center justify-center h-48">
      <div className="h-7 w-7 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const TABS = [
  { id: "oportunidades", label: "Oportunidades", icono: TrendingUp },
  { id: "cross-selling", label: "Cross-Selling IC", icono: Sparkles },
  { id: "ia", label: "IC & Docs", icono: Brain },
  { id: "reunion", label: "Reunión 360", icono: Users },
] as const

type TabId = typeof TABS[number]["id"]

export default function FichaClientePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const router = useRouter()
  const searchParams = useSearchParams()
  const { isManager } = useAppStore()
  const [tabActivo, setTabActivo] = useState<TabId>("oportunidades")
  const [propietarioId, setPropietarioId] = useState(searchParams.get("propietario_id") ?? "")
  const propietarioFiltro = isManager() && propietarioId ? propietarioId : undefined

  const { data: comerciales = [] } = useQuery<Array<{ propietario_id: string; nombre_completo: string }>>({
    queryKey: ["equipo-ranking-selector-cuenta-detalle"],
    queryFn: () => api.equipo.ranking() as Promise<Array<{ propietario_id: string; nombre_completo: string }>>,
    enabled: isManager(),
  })

  const { data: cuenta, isLoading, isError } = useQuery<CuentaDetalle>({
    queryKey: ["cuenta", id, propietarioFiltro],
    queryFn: () => api.cuentas.obtener(id, propietarioFiltro) as Promise<CuentaDetalle>,
  })

  if (isLoading) {
    return (
      <div className="flex flex-col flex-1">
        <div className="h-32 border-b border-zinc-200 bg-white animate-pulse" />
        <div className="flex-1 flex items-center justify-center">
          <div className="h-8 w-8 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    )
  }

  if (isError || !cuenta) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center gap-3">
        <Building2 size={40} className="text-zinc-300" />
        <p className="text-sm text-zinc-500">No se encontró la cuenta.</p>
        <button onClick={() => router.back()} className="text-xs text-sgs-rojo underline">Volver</button>
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1">
      <Topbar
        titulo={cuenta.nombre}
        subtitulo="Ficha de cliente, pipeline y herramientas IC"
      />
      {/* ── Cabecera ── */}
      <div className="bg-white border-b border-zinc-200 px-4 sm:px-6 py-5">
        <div className="flex items-start gap-4">
          <button
            onClick={() => router.back()}
            className="mt-0.5 shrink-0 text-zinc-400 hover:text-zinc-700 transition-colors"
            aria-label="Volver"
          >
            <ArrowLeft size={18} />
          </button>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Building2 size={16} className="text-zinc-400 shrink-0" />
              <p className="text-xs text-zinc-500 uppercase tracking-wide font-medium">Ficha de cliente</p>
            </div>
            <h1 className="text-xl font-bold text-zinc-900 truncate">{cuenta.nombre}</h1>
            {cuenta.ultima_actividad && (
              <p className="text-xs text-zinc-400 mt-0.5">
                Última actividad: {cuenta.ultima_actividad.slice(0, 10)}
              </p>
            )}
            {isManager() && (
              <div className="mt-3">
                <select
                  value={propietarioId}
                  onChange={(e) => setPropietarioId(e.target.value)}
                  className="w-full max-w-sm text-sm border border-zinc-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
                >
                  <option value="">Todos los comerciales</option>
                  {comerciales.map((c) => (
                    <option key={c.propietario_id} value={c.propietario_id}>
                      {c.nombre_completo}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Mini KPIs inline */}
          <div className="hidden lg:flex items-center gap-6 shrink-0">
            <div className="text-right">
              <p className="text-xs text-zinc-400">Pipeline</p>
              <p className="text-sm font-bold text-zinc-900">{fmtEURc.format(cuenta.pipeline_activo)}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-zinc-400">Win Rate</p>
              <p className="text-sm font-bold text-zinc-900">{Number(cuenta.win_rate).toFixed(1)}%</p>
            </div>
            <ScoreRing score={cuenta.oportunidades_activas > 0 ? Math.round(cuenta.win_rate) : null} />
          </div>
        </div>

        {/* ── Tabs ── */}
        <Tabs.Root value={tabActivo} onValueChange={(v) => setTabActivo(v as TabId)}>
          <Tabs.List className="flex gap-1 mt-5 -mb-px overflow-x-auto pb-1">
            {TABS.map(({ id: tabId, label, icono: Icono }) => (
              <Tabs.Trigger
                key={tabId}
                value={tabId}
                className={cn(
                  "flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-t-lg border border-transparent transition-colors",
                  "data-[state=active]:border-zinc-200 data-[state=active]:border-b-white data-[state=active]:bg-white data-[state=active]:text-zinc-900",
                  "data-[state=inactive]:text-zinc-500 data-[state=inactive]:hover:text-zinc-700"
                )}
              >
                <Icono size={13} />
                {label}
              </Tabs.Trigger>
            ))}
          </Tabs.List>
        </Tabs.Root>
      </div>

      {/* ── Contenido tab ── */}
      <div className="flex-1 overflow-auto p-2.5 md:p-3.5">
        {tabActivo === "oportunidades" && <TabOportunidades cuenta={cuenta} />}
        {tabActivo === "cross-selling" && <TabCrossSelling cuentaId={cuenta.id} nombreCuenta={cuenta.nombre} />}
        {tabActivo === "ia" && <TabIA cuentaId={id} />}
        {tabActivo === "reunion" && <TabReunion cuentaId={id} />}
      </div>
    </div>
  )
}
