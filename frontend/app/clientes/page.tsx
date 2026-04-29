"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { cn } from "@/lib/utils"
import { Topbar } from "@/components/layout/topbar"
import { api } from "@/lib/api"
import { useDocumentoJob } from "@/hooks/use-documento-job"
import { ArtefactoPicker } from "@/components/ui/artefacto-picker"
import { useAppStore } from "@/store/use-app-store"
import { formatearEuros, formatearPorcentaje } from "@/lib/utils"
import type { ClienteResumen, ClienteDetalle, OportunidadEnCliente } from "@/types"

// ── Constantes de etapas ─────────────────────────────────────────────────────

const ETAPA_LABEL: Record<string, string> = {
  estimation_sent: "Estimación enviada",
  technically_approved: "Aprobado técn.",
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

// ── Badge etapa ───────────────────────────────────────────────────────────────

function BadgeEtapa({ etapa }: { etapa: string }) {
  const color =
    etapa === "closed_won"
      ? "bg-emerald-50 text-emerald-700"
      : etapa === "closed_lost"
      ? "bg-red-50 text-red-600"
      : etapa === "closed_withdrawn"
      ? "bg-zinc-100 text-zinc-500"
      : "bg-blue-50 text-blue-700"
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium ${color}`}>
      {ETAPA_LABEL[etapa] ?? etapa}
    </span>
  )
}

// ── Chip pequeño (comercial / SBU) ────────────────────────────────────────────

function Chip({ texto, variante = "zinc" }: { texto: string; variante?: "zinc" | "blue" | "amber" }) {
  const estilos = {
    zinc: "bg-zinc-100 text-zinc-600",
    blue: "bg-blue-50 text-blue-700",
    amber: "bg-amber-50 text-amber-700",
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium ${estilos[variante]}`}>
      {texto}
    </span>
  )
}

// ── Tab equipo (agrupación de oportunidades por comercial) ────────────────────

function TabEquipo({ oportunidades }: { oportunidades: OportunidadEnCliente[] }) {
  const porComercial = oportunidades.reduce<
    Record<string, { nombre: string; total: number; ganadas: number; pipeline: number; opps: number }>
  >((acc, op) => {
    const nombre = op.propietario_nombre ?? "Sin asignar"
    if (!acc[nombre]) {
      acc[nombre] = { nombre, total: 0, ganadas: 0, pipeline: 0, opps: 0 }
    }
    acc[nombre].total += 1
    acc[nombre].opps += 1
    if (op.etapa === "closed_won") acc[nombre].ganadas += 1
    if (!["closed_won", "closed_lost", "closed_withdrawn"].includes(op.etapa)) {
      acc[nombre].pipeline += Number(op.importe)
    }
    return acc
  }, {})

  const comerciales = Object.values(porComercial).sort((a, b) => b.pipeline - a.pipeline)

  if (comerciales.length === 0) {
    return <p className="text-sm text-zinc-400 text-center py-8">Sin comerciales asignados.</p>
  }

  return (
    <div className="space-y-2 px-5 py-4">
      {comerciales.map((c) => {
        const wr = c.total > 0 ? Math.round((c.ganadas / c.total) * 100) : 0
        return (
          <div
            key={c.nombre}
            className="rounded-lg border border-zinc-100 bg-white px-4 py-3"
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-zinc-100 flex items-center justify-center text-xs font-bold text-zinc-600 shrink-0">
                  {c.nombre.charAt(0).toUpperCase()}
                </div>
                <p className="text-sm font-medium text-zinc-900">{c.nombre}</p>
              </div>
              <span
                className={cn(
                  "text-xs font-semibold px-2 py-0.5 rounded-full",
                  wr >= 70 ? "bg-emerald-100 text-emerald-700"
                    : wr >= 40 ? "bg-amber-100 text-amber-700"
                    : "bg-red-100 text-red-700",
                )}
              >
                {wr}% WR
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 mt-2 text-center">
              <div>
                <p className="text-[10px] text-zinc-400">Pipeline</p>
                <p className="text-xs font-semibold text-zinc-800">{formatearEuros(c.pipeline)}</p>
              </div>
              <div>
                <p className="text-[10px] text-zinc-400">Oportunidades</p>
                <p className="text-xs font-semibold text-zinc-800">{c.total}</p>
              </div>
              <div>
                <p className="text-[10px] text-zinc-400">Ganadas</p>
                <p className="text-xs font-semibold text-emerald-700">{c.ganadas}</p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Drawer detalle de cliente ─────────────────────────────────────────────────

type TabDetalle = "oportunidades" | "equipo" | "repositorio"

function DrawerCliente({
  cliente,
  propietarioId,
  onClose,
}: {
  cliente: ClienteResumen
  propietarioId?: string
  onClose: () => void
}) {
  const router = useRouter()
  const [tab, setTab] = useState<TabDetalle>("oportunidades")
  const [lanzandoIaId, setLanzandoIaId] = useState<string | null>(null)
  const { lanzar } = useDocumentoJob()

  const { data, isLoading } = useQuery<ClienteDetalle>({
    queryKey: ["cliente-global", cliente.id, propietarioId ?? "all"],
    queryFn: () => api.clientes.obtener(cliente.id, propietarioId) as Promise<ClienteDetalle>,
  })

  function irADeck() {
    const qs = new URLSearchParams({ empresa: cliente.nombre })
    router.push(`/deck?${qs}`)
  }

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 overlay-strong z-40" onClick={onClose} />

      {/* Panel */}
      <div className="fixed top-0 right-0 h-full w-full sm:w-[520px] bg-white shadow-2xl z-50 flex flex-col">
        {/* Header */}
        <div className="px-5 py-4 border-b border-zinc-100 flex items-start justify-between gap-3 shrink-0">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-zinc-900 truncate">{cliente.nombre}</h2>
            <div className="flex flex-wrap gap-1 mt-1.5">
              {cliente.sbus.slice(0, 4).map((s) => (
                <Chip key={s} texto={s} variante="blue" />
              ))}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-700 text-xl leading-none transition-colors shrink-0 mt-0.5"
          >
            ×
          </button>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 gap-px bg-zinc-100 border-b border-zinc-100 shrink-0">
          {[
            { label: "Pipeline activo", valor: formatearEuros(cliente.pipeline_activo) },
            { label: "Importe ganado", valor: formatearEuros(cliente.importe_ganado) },
            {
              label: "Win Rate",
              valor: formatearPorcentaje(cliente.win_rate),
            },
            {
              label: "Oportunidades",
              valor: `${cliente.total_oportunidades} (${cliente.oportunidades_activas} activas)`,
            },
          ].map(({ label, valor }) => (
            <div key={label} className="bg-white px-4 py-3">
              <p className="text-[10px] text-zinc-400 uppercase tracking-wide">{label}</p>
              <p className="text-sm font-semibold text-zinc-900 mt-0.5">{valor}</p>
            </div>
          ))}
        </div>

        {/* Comerciales asignados */}
        {cliente.comerciales.length > 0 && (
          <div className="px-5 py-2.5 border-b border-zinc-100 flex flex-wrap gap-1.5 shrink-0">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wide self-center mr-1">Equipo:</span>
            {cliente.comerciales.map((c) => (
              <Chip key={c} texto={c} variante="zinc" />
            ))}
          </div>
        )}

        {/* Acciones rápidas */}
        <div className="px-5 py-2.5 border-b border-zinc-100 flex items-center gap-2 shrink-0">
          <button
            onClick={irADeck}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-zinc-200 rounded-lg hover:bg-zinc-50 text-zinc-700 transition-colors"
          >
            ⬡ Generar deck
          </button>
          <a
            href="/informes"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-zinc-200 rounded-lg hover:bg-zinc-50 text-zinc-700 transition-colors"
          >
            📊 Informe
          </a>
          <a
            href="/voice"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-zinc-200 rounded-lg hover:bg-zinc-50 text-zinc-700 transition-colors"
          >
            ◎ Voice Studio
          </a>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-zinc-100 shrink-0">
          {(["oportunidades", "equipo", "repositorio"] as TabDetalle[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "flex-1 py-2.5 text-xs font-medium transition-colors",
                tab === t
                  ? "text-sgs-rojo border-b-2 border-sgs-rojo -mb-px"
                  : "text-zinc-500 hover:text-zinc-700",
              )}
            >
              {t === "oportunidades"
                ? `Oportunidades${data ? ` (${data.oportunidades.length})` : ""}`
                : t === "equipo"
                ? `Equipo${data ? ` (${new Set(data.oportunidades.map((o) => o.propietario_nombre)).size})` : ""}`
                : "Repositorio IC"}
            </button>
          ))}
        </div>

        {/* Contenido */}
        <div className="flex-1 overflow-y-auto">
          {tab === "repositorio" ? (
            <div className="p-4">
              <ArtefactoPicker contextoTipo="cuenta" contextoId={cliente.id} modoModal />
            </div>
          ) : isLoading ? (
            <div className="flex items-center justify-center h-40">
              <div className="h-7 w-7 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
            </div>
          ) : !data ? (
            <p className="text-sm text-zinc-400 text-center py-12">Error al cargar los datos.</p>
          ) : tab === "oportunidades" ? (
            <div className="px-5 py-4 space-y-2">
              {data.oportunidades.map((op) => {
                const fecha = op.fecha_decision ?? op.fecha_creacion
                return (
                  <div
                    key={op.id}
                    className="rounded-lg border border-zinc-100 bg-zinc-50 px-4 py-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-xs font-medium text-zinc-900 leading-snug line-clamp-2">{op.nombre}</p>
                      <p className="text-xs font-semibold text-zinc-900 shrink-0">{formatearEuros(op.importe)}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                      <BadgeEtapa etapa={op.etapa} />
                      {op.sbu_nombre && <Chip texto={op.sbu_nombre} variante="blue" />}
                      {op.producto_nombre && <Chip texto={op.producto_nombre} variante="amber" />}
                    </div>
                    <div className="flex items-center justify-between mt-1.5">
                      <span className="text-[10px] text-zinc-500">
                        {op.propietario_nombre ?? "Sin asignar"}
                      </span>
                      {fecha && (
                        <span className="text-[10px] text-zinc-400">
                          {new Date(fecha).toLocaleDateString("es-ES", {
                            day: "2-digit",
                            month: "short",
                            year: "numeric",
                          })}
                        </span>
                      )}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      <button
                        onClick={() => {
                          setLanzandoIaId(`pdf-${op.id}`)
                          void lanzar(
                            "pdf",
                            () => api.documentosJobs.generarPdf(cliente.id, { contexto: op.nombre, contextoTipo: "oportunidad", contextoId: op.id }),
                            () => setLanzandoIaId(null),
                            () => setLanzandoIaId(null),
                          )
                        }}
                        disabled={lanzandoIaId !== null}
                        className="px-2 py-1 text-[10px] font-medium border border-zinc-300 rounded-md bg-white hover:bg-zinc-100 disabled:opacity-50"
                      >
                        {lanzandoIaId === `pdf-${op.id}` ? "Lanzando…" : "PDF"}
                      </button>
                      <button
                        onClick={() => {
                          setLanzandoIaId(`pptx-${op.id}`)
                          void lanzar(
                            "pptx",
                            () => api.documentosJobs.generarPptx(cliente.id, { contexto: op.nombre, contextoTipo: "oportunidad", contextoId: op.id }),
                            () => setLanzandoIaId(null),
                            () => setLanzandoIaId(null),
                          )
                        }}
                        disabled={lanzandoIaId !== null}
                        className="px-2 py-1 text-[10px] font-medium border border-zinc-300 rounded-md bg-white hover:bg-zinc-100 disabled:opacity-50"
                      >
                        {lanzandoIaId === `pptx-${op.id}` ? "Lanzando…" : "Deck"}
                      </button>
                      <button
                        onClick={() => {
                          setLanzandoIaId(`briefing-${op.id}`)
                          void lanzar(
                            "briefing",
                            () => api.documentosJobs.generarBriefing(cliente.id, { contexto: op.nombre, contextoTipo: "oportunidad", contextoId: op.id }),
                            () => setLanzandoIaId(null),
                            () => setLanzandoIaId(null),
                          )
                        }}
                        disabled={lanzandoIaId !== null}
                        className="px-2 py-1 text-[10px] font-medium border border-zinc-300 rounded-md bg-white hover:bg-zinc-100 disabled:opacity-50"
                      >
                        {lanzandoIaId === `briefing-${op.id}` ? "Lanzando…" : "Briefing"}
                      </button>
                      <button
                        onClick={() => router.push(`/documentos?tab=ia&contexto_tipo=oportunidad&contexto_id=${op.id}`)}
                        className="px-2 py-1 text-[10px] font-medium border border-zinc-300 rounded-md bg-white hover:bg-zinc-100"
                      >
                        Historial IC
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <TabEquipo oportunidades={data.oportunidades} />
          )}
        </div>
      </div>
    </>
  )
}

// ── Fila de tabla ─────────────────────────────────────────────────────────────

function FilaCliente({
  cliente,
  activo,
  onClick,
}: {
  cliente: ClienteResumen
  activo: boolean
  onClick: () => void
}) {
  return (
    <tr
      onClick={onClick}
      className={cn(
        "cursor-pointer border-b border-zinc-100 transition-colors",
        activo ? "bg-red-50 border-l-2 border-l-sgs-rojo" : "hover:bg-zinc-50",
      )}
    >
      {/* Empresa */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0",
              activo ? "bg-sgs-rojo text-white" : "bg-zinc-100 text-zinc-600",
            )}
          >
            {cliente.nombre.charAt(0).toUpperCase()}
          </div>
          <span className="text-sm font-medium text-zinc-900 truncate max-w-[220px]">{cliente.nombre}</span>
        </div>
      </td>

      {/* Pipeline activo */}
      <td className="px-4 py-3 text-sm text-zinc-700 text-right tabular-nums font-medium">
        {formatearEuros(cliente.pipeline_activo)}
      </td>

      {/* Importe ganado */}
      <td className="px-4 py-3 text-sm text-zinc-700 text-right tabular-nums">
        {formatearEuros(cliente.importe_ganado)}
      </td>

      {/* Win Rate */}
      <td className="px-4 py-3 text-right">
        <span
          className={cn(
            "text-xs font-semibold px-2 py-0.5 rounded-full",
            cliente.win_rate >= 70
              ? "bg-emerald-100 text-emerald-700"
              : cliente.win_rate >= 40
              ? "bg-amber-100 text-amber-700"
              : "bg-red-100 text-red-700",
          )}
        >
          {formatearPorcentaje(cliente.win_rate)}
        </span>
      </td>

      {/* Oportunidades */}
      <td className="px-4 py-3 text-sm text-zinc-500 text-right tabular-nums">
        {cliente.total_oportunidades}
        {cliente.oportunidades_activas > 0 && (
          <span className="text-xs text-emerald-600 ml-1">
            ({cliente.oportunidades_activas})
          </span>
        )}
      </td>

      {/* Equipo (comerciales) */}
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1 justify-end">
          {cliente.comerciales.slice(0, 2).map((c) => (
            <Chip key={c} texto={c.split(" ")[0]} variante="zinc" />
          ))}
          {cliente.comerciales.length > 2 && (
            <Chip texto={`+${cliente.comerciales.length - 2}`} variante="zinc" />
          )}
        </div>
      </td>

      {/* SBUs */}
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1 justify-end">
          {cliente.sbus.slice(0, 2).map((s) => (
            <Chip key={s} texto={s.split(" ")[0]} variante="blue" />
          ))}
          {cliente.sbus.length > 2 && (
            <Chip texto={`+${cliente.sbus.length - 2}`} variante="blue" />
          )}
        </div>
      </td>

      {/* Última actividad */}
      <td className="px-4 py-3 text-xs text-zinc-400 text-right whitespace-nowrap">
        {cliente.ultima_actividad
          ? new Date(cliente.ultima_actividad).toLocaleDateString("es-ES", {
              day: "2-digit",
              month: "short",
              year: "numeric",
            })
          : "—"}
      </td>
    </tr>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function PaginaClientes() {
  const { isManager } = useAppStore()
  const [busqueda, setBusqueda] = useState("")
  const [propietarioId, setPropietarioId] = useState("")
  const [pagina, setPagina] = useState(1)
  const [sortBy, setSortBy] = useState("pipeline_activo")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")
  const [clienteSeleccionado, setClienteSeleccionado] = useState<ClienteResumen | null>(null)

  const { data: comerciales = [] } = useQuery<Array<{ propietario_id: string; nombre_completo: string }>>({
    queryKey: ["equipo-ranking-selector-clientes"],
    queryFn: () => api.equipo.ranking() as Promise<Array<{ propietario_id: string; nombre_completo: string }>>,
    enabled: isManager(),
  })
  const propietarioFiltro = isManager() && propietarioId ? propietarioId : undefined

  const { data, isLoading, isError } = useQuery<{
    total: number
    pagina: number
    por_pagina: number
    datos: ClienteResumen[]
  }>({
    queryKey: ["clientes-global", busqueda, pagina, sortBy, sortDir, propietarioFiltro],
    queryFn: () =>
      api.clientes.listar({
        busqueda: busqueda || undefined,
        propietario_id: propietarioFiltro,
        pagina,
        por_pagina: 25,
        sort_by: sortBy,
        sort_dir: sortDir,
      }) as Promise<{
        total: number
        pagina: number
        por_pagina: number
        datos: ClienteResumen[]
      }>,
  })
  function cambiarOrden(columna: string) {
    if (sortBy === columna) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"))
    } else {
      setSortBy(columna)
      setSortDir(columna === "nombre" ? "asc" : "desc")
    }
    setPagina(1)
  }
  function iconoOrden(columna: string) {
    if (sortBy !== columna) return "↕"
    return sortDir === "asc" ? "↑" : "↓"
  }

  const totalPaginas = data ? Math.ceil(data.total / data.por_pagina) : 1

  const totalPipeline = data?.datos.reduce((s, c) => s + Number(c.pipeline_activo), 0) ?? 0
  const totalGanado = data?.datos.reduce((s, c) => s + Number(c.importe_ganado), 0) ?? 0

  return (
    <>
      <Topbar
        titulo="Clientes"
        subtitulo="Visión completa de todas las cuentas · equipo y pipeline centralizados"
      />

      <main className="flex-1 flex flex-col overflow-hidden">
        {/* ── KPI strip rápido ─────────────────────────────────────── */}
        {!isLoading && data && (
        <div className="px-6 pt-4 pb-2 grid grid-cols-1 sm:grid-cols-3 gap-4 shrink-0">
            <div className="bg-white border border-zinc-200 rounded-xl px-4 py-3 flex items-center gap-3">
              <span className="text-xl">◉</span>
              <div>
                <p className="text-lg font-bold text-zinc-900">{data.total}</p>
                <p className="text-xs text-zinc-400">Clientes totales</p>
              </div>
            </div>
            <div className="bg-white border border-zinc-200 rounded-xl px-4 py-3 flex items-center gap-3">
              <span className="text-xl">◈</span>
              <div>
                <p className="text-lg font-bold text-zinc-900">{formatearEuros(totalPipeline)}</p>
                <p className="text-xs text-zinc-400">Pipeline activo (pág. actual)</p>
              </div>
            </div>
            <div className="bg-white border border-zinc-200 rounded-xl px-4 py-3 flex items-center gap-3">
              <span className="text-xl">◆</span>
              <div>
                <p className="text-lg font-bold text-zinc-900">{formatearEuros(totalGanado)}</p>
                <p className="text-xs text-zinc-400">Ganado acumulado (pág. actual)</p>
              </div>
            </div>
          </div>
        )}

        {/* ── Barra de herramientas ─────────────────────────────────── */}
        <div className="px-6 py-3 flex items-center justify-between gap-4 shrink-0">
          <div className="flex items-center gap-3">
          <div className="relative w-72">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 text-sm">◎</span>
            <input
              type="text"
              placeholder="Buscar empresa..."
              value={busqueda}
              onChange={(e) => {
                setBusqueda(e.target.value)
                setPagina(1)
              }}
              className="w-full pl-8 pr-3 py-2 text-sm border border-zinc-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-zinc-300"
            />
          </div>
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
          </div>
          {data && (
            <p className="text-xs text-zinc-400">
              {data.total} clientes · ordenados por pipeline
            </p>
          )}
        </div>

        {/* ── Tabla ────────────────────────────────────────────────── */}
        <div className="flex-1 overflow-auto mx-6 mb-0 bg-white rounded-xl border border-zinc-200">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="h-8 w-8 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
            </div>
          ) : isError ? (
            <div className="flex items-center justify-center h-64">
              <p className="text-sm text-zinc-500">Error al cargar los clientes.</p>
            </div>
          ) : !data?.datos.length ? (
            <div className="flex flex-col items-center justify-center h-64 gap-2">
              <span className="text-3xl text-zinc-200">◯</span>
              <p className="text-sm text-zinc-500">
                {busqueda ? "Sin resultados para esa búsqueda." : "No hay clientes registrados."}
              </p>
            </div>
          ) : (
            <table className="w-full text-left">
              <thead className="sticky top-0 bg-zinc-50 border-b border-zinc-200 z-10">
                <tr>
                  <th className="px-4 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-wide">Empresa</th>
                  <th className="px-4 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-wide text-right">
                    <button type="button" onClick={() => cambiarOrden("pipeline_activo")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                      Pipeline <span>{iconoOrden("pipeline_activo")}</span>
                    </button>
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-wide text-right">
                    <button type="button" onClick={() => cambiarOrden("importe_ganado")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                      Ganado <span>{iconoOrden("importe_ganado")}</span>
                    </button>
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-wide text-right">
                    <button type="button" onClick={() => cambiarOrden("win_rate")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                      Win Rate <span>{iconoOrden("win_rate")}</span>
                    </button>
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-wide text-right">
                    <button type="button" onClick={() => cambiarOrden("total_oportunidades")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                      Opps <span>{iconoOrden("total_oportunidades")}</span>
                    </button>
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-wide text-right">Equipo</th>
                  <th className="px-4 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-wide text-right">SBUs</th>
                  <th className="px-4 py-3 text-xs font-semibold text-zinc-500 uppercase tracking-wide text-right">
                    <button type="button" onClick={() => cambiarOrden("ultima_actividad")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                      Última activ. <span>{iconoOrden("ultima_actividad")}</span>
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-zinc-50">
                {data.datos.map((cliente) => (
                  <FilaCliente
                    key={cliente.id}
                    cliente={cliente}
                    activo={clienteSeleccionado?.id === cliente.id}
                    onClick={() =>
                      setClienteSeleccionado(
                        clienteSeleccionado?.id === cliente.id ? null : cliente,
                      )
                    }
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* ── Paginación ───────────────────────────────────────────── */}
        {data && totalPaginas > 1 && (
          <div className="px-6 py-3 border-t border-zinc-200 bg-white flex items-center justify-between shrink-0">
            <p className="text-xs text-zinc-500">
              Página {pagina} de {totalPaginas} · {data.total} clientes
            </p>
            <div className="flex items-center gap-2">
              <button
                disabled={pagina === 1}
                onClick={() => setPagina(pagina - 1)}
                className="px-3 py-1.5 text-xs border border-zinc-200 rounded-lg hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                ← Anterior
              </button>
              <button
                disabled={pagina >= totalPaginas}
                onClick={() => setPagina(pagina + 1)}
                className="px-3 py-1.5 text-xs border border-zinc-200 rounded-lg hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Siguiente →
              </button>
            </div>
          </div>
        )}
      </main>

      {/* ── Drawer de detalle ────────────────────────────────────── */}
      {clienteSeleccionado && (
        <DrawerCliente
          cliente={clienteSeleccionado}
          propietarioId={propietarioFiltro}
          onClose={() => setClienteSeleccionado(null)}
        />
      )}
    </>
  )
}
