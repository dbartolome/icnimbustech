"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { ChevronRight, AlertTriangle, TrendingUp, Building2, Target } from "lucide-react"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import { Topbar } from "@/components/layout/topbar"
import { useAppStore } from "@/store/use-app-store"
import type { CuentaResumen, KpisDashboard } from "@/types"

// =============================================================================
// Helpers
// =============================================================================

function formatEur(n: number) {
  return new Intl.NumberFormat("es-ES", {
    style: "currency", currency: "EUR",
    notation: "compact", maximumFractionDigits: 1,
  }).format(n)
}

function formatEurExacto(n: number) {
  return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n)
}

function formatPct(n: number) {
  return `${Number(n).toFixed(1)}%`
}

// =============================================================================
// Strip KPIs del comercial
// =============================================================================

function KpiStrip({ totalCuentas }: { totalCuentas: number }) {
  const { data: kpis } = useQuery<KpisDashboard>({
    queryKey: ["dashboard-kpis-comercial"],
    queryFn: () => api.dashboard.kpis(true) as unknown as Promise<KpisDashboard>,
    staleTime: 5 * 60 * 1000,
  })

  const { data: criticos = [] } = useQuery<{ oportunidad_id: string }[]>({
    queryKey: ["scoring-criticos-comercial"],
    queryFn: () => api.scoring.criticos(40) as Promise<{ oportunidad_id: string }[]>,
    staleTime: 5 * 60 * 1000,
  })

  const kpis4 = [
    {
      label: "Mis cuentas",
      valor: String(totalCuentas || "—"),
      icono: Building2,
      color: "text-blue-600",
      bg: "bg-blue-50",
    },
    {
      label: "Pipeline activo",
      valor: kpis ? formatEur(kpis.pipeline_activo) : "—",
      icono: TrendingUp,
      color: "text-emerald-600",
      bg: "bg-emerald-50",
    },
    {
      label: "Mi Win Rate",
      valor: kpis ? formatPct(kpis.win_rate_global) : "—",
      icono: Target,
      color: kpis && kpis.win_rate_global >= 70 ? "text-emerald-600" : "text-amber-600",
      bg: kpis && kpis.win_rate_global >= 70 ? "bg-emerald-50" : "bg-amber-50",
    },
    {
      label: "Ops en riesgo",
      valor: String(criticos.length),
      icono: AlertTriangle,
      color: criticos.length > 0 ? "text-sgs-rojo" : "text-zinc-400",
      bg: criticos.length > 0 ? "bg-red-50" : "bg-zinc-50",
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 px-6 py-4 bg-white border-b border-zinc-200">
      {kpis4.map(({ label, valor, icono: Icono, color, bg }) => (
        <div key={label} className="flex items-center gap-3">
          <div className={cn("w-9 h-9 rounded-lg flex items-center justify-center shrink-0", bg)}>
            <Icono size={16} className={color} />
          </div>
          <div>
            <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">{label}</p>
            <p className={cn("text-lg font-bold leading-tight", color)}>{valor}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

// =============================================================================
// Fila de tabla
// =============================================================================

function FilaCuenta({ cuenta, propietarioId }: { cuenta: CuentaResumen; propietarioId?: string }) {
  const router = useRouter()

  return (
    <tr
      onClick={() => {
        const qs = propietarioId ? `?propietario_id=${encodeURIComponent(propietarioId)}` : ""
        router.push(`/cuentas/${cuenta.id}${qs}`)
      }}
      className="cursor-pointer border-b border-zinc-100 transition-colors hover:bg-zinc-50 group"
    >
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 bg-zinc-100 text-zinc-600 group-hover:bg-sgs-rojo/10 group-hover:text-sgs-rojo transition-colors">
            {cuenta.nombre.charAt(0).toUpperCase()}
          </div>
          <span className="text-sm font-medium text-zinc-900 truncate max-w-[220px]">{cuenta.nombre}</span>
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-zinc-600 text-right tabular-nums">
        {formatEurExacto(cuenta.pipeline_activo)}
      </td>
      <td className="px-4 py-3 text-sm text-zinc-600 text-right tabular-nums">
        {formatEurExacto(cuenta.importe_ganado)}
      </td>
      <td className="px-4 py-3 text-right">
        <span className={cn(
          "text-xs font-semibold px-2 py-0.5 rounded-full",
          cuenta.win_rate >= 70 ? "bg-emerald-100 text-emerald-700"
            : cuenta.win_rate >= 40 ? "bg-amber-100 text-amber-700"
            : "bg-red-100 text-red-700",
        )}>
          {formatPct(cuenta.win_rate)}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-zinc-500 text-right tabular-nums">
        {cuenta.total_oportunidades}
        {cuenta.oportunidades_activas > 0 && (
          <span className="text-xs text-emerald-600 ml-1">({cuenta.oportunidades_activas} activas)</span>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-zinc-400 text-right">
        {cuenta.ultima_actividad ?? "—"}
      </td>
      <td className="px-3 py-3 text-zinc-300 group-hover:text-zinc-500 transition-colors">
        <ChevronRight size={15} />
      </td>
    </tr>
  )
}

// =============================================================================
// Página principal
// =============================================================================

export default function CuentasPage() {
  const { isManager } = useAppStore()
  const [busqueda, setBusqueda] = useState("")
  const [propietarioId, setPropietarioId] = useState("")
  const [pagina, setPagina] = useState(1)
  const [sortBy, setSortBy] = useState("pipeline_activo")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")

  const { data: comerciales = [] } = useQuery<Array<{ propietario_id: string; nombre_completo: string }>>({
    queryKey: ["equipo-ranking-selector-cuentas"],
    queryFn: () => api.equipo.ranking() as Promise<Array<{ propietario_id: string; nombre_completo: string }>>,
    enabled: isManager(),
  })
  const propietarioFiltro = isManager() && propietarioId ? propietarioId : undefined

  const { data, isLoading, isError } = useQuery<{
    total: number
    pagina: number
    por_pagina: number
    datos: CuentaResumen[]
  }>({
    queryKey: ["cuentas", busqueda, pagina, sortBy, sortDir, propietarioFiltro],
    queryFn: () =>
      api.cuentas.listar({
        busqueda: busqueda || undefined,
        propietario_id: propietarioFiltro,
        pagina,
        por_pagina: 20,
        sort_by: sortBy,
        sort_dir: sortDir,
      }) as Promise<{
        total: number
        pagina: number
        por_pagina: number
        datos: CuentaResumen[]
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

  return (
    <div className="flex flex-1 min-h-screen">
      <div className="flex-1 flex flex-col overflow-hidden">
        <Topbar
          titulo="Mis Cuentas"
          subtitulo="Clientes asignados y acceso a herramientas IC por cuenta"
        />

        {/* Header */}
        <header className="px-6 py-5 border-b border-zinc-200 bg-white">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold text-zinc-900">Mis Cuentas</h1>
              <p className="text-sm text-zinc-500 mt-0.5">
                Busca un cliente y accede a todas sus herramientas IC
              </p>
            </div>
            <div className="relative w-72">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 text-sm">⌕</span>
              <input
                type="text"
                placeholder="Buscar empresa cliente..."
                value={busqueda}
                onChange={(e) => { setBusqueda(e.target.value); setPagina(1) }}
                className="w-full pl-8 pr-14 py-2.5 text-sm border border-zinc-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-zinc-400 bg-zinc-100 px-1.5 py-0.5 rounded">
                ⌘K
              </span>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <select
              value={sortBy}
              onChange={(e) => cambiarOrden(e.target.value)}
              className="text-sm border border-zinc-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
            >
              <option value="pipeline_activo">Orden: pipeline activo</option>
              <option value="importe_ganado">Orden: importe ganado</option>
              <option value="win_rate">Orden: win rate</option>
              <option value="total_oportunidades">Orden: oportunidades</option>
              <option value="ultima_actividad">Orden: última actividad</option>
            </select>
            <select
              value={sortDir}
              onChange={(e) => { setSortDir(e.target.value as "asc" | "desc"); setPagina(1) }}
              className="text-sm border border-zinc-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
            >
              <option value="desc">Descendente</option>
              <option value="asc">Ascendente</option>
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
          </div>
        </header>

        {/* KPI strip */}
        <KpiStrip totalCuentas={data?.total ?? 0} />

        {/* Tabla */}
        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="h-8 w-8 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
            </div>
          ) : isError ? (
            <div className="flex items-center justify-center h-64">
              <p className="text-sm text-zinc-500">Error al cargar las cuentas.</p>
            </div>
          ) : !data?.datos.length ? (
            <div className="flex flex-col items-center justify-center h-64 gap-2">
              <span className="text-3xl text-zinc-300">◯</span>
              <p className="text-sm text-zinc-500">
                {busqueda ? "Sin resultados para tu búsqueda." : "No tienes cuentas asignadas aún."}
              </p>
            </div>
          ) : (
            <table className="w-full text-left">
              <thead className="sticky top-0 bg-zinc-50 border-b border-zinc-200 z-10">
                <tr>
                  <th className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Cuenta</th>
                  <th className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide text-right">
                    <button type="button" onClick={() => cambiarOrden("pipeline_activo")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                      Pipeline activo <span>{iconoOrden("pipeline_activo")}</span>
                    </button>
                  </th>
                  <th className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide text-right">
                    <button type="button" onClick={() => cambiarOrden("importe_ganado")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                      Importe ganado <span>{iconoOrden("importe_ganado")}</span>
                    </button>
                  </th>
                  <th className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide text-right">
                    <button type="button" onClick={() => cambiarOrden("win_rate")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                      Win rate <span>{iconoOrden("win_rate")}</span>
                    </button>
                  </th>
                  <th className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide text-right">
                    <button type="button" onClick={() => cambiarOrden("total_oportunidades")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                      Oportunidades <span>{iconoOrden("total_oportunidades")}</span>
                    </button>
                  </th>
                  <th className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide text-right">
                    <button type="button" onClick={() => cambiarOrden("ultima_actividad")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                      Última actividad <span>{iconoOrden("ultima_actividad")}</span>
                    </button>
                  </th>
                  <th className="px-3 py-3" />
                </tr>
              </thead>
              <tbody className="bg-white">
                {data.datos.map((cuenta) => (
                  <FilaCuenta key={cuenta.id} cuenta={cuenta} propietarioId={propietarioFiltro} />
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Paginación */}
        {data && totalPaginas > 1 && (
          <div className="px-6 py-3 border-t border-zinc-200 bg-white flex items-center justify-between">
            <p className="text-xs text-zinc-500">
              Página {pagina} de {totalPaginas} · {data.total} cuentas
            </p>
            <div className="flex items-center gap-2">
              <button
                disabled={pagina === 1}
                onClick={() => setPagina(pagina - 1)}
                className="px-3 py-1.5 text-xs border border-zinc-200 rounded hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                ← Anterior
              </button>
              <button
                disabled={pagina >= totalPaginas}
                onClick={() => setPagina(pagina + 1)}
                className="px-3 py-1.5 text-xs border border-zinc-200 rounded hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Siguiente →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
