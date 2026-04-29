"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { cn } from "@/lib/utils"
import { Topbar } from "@/components/layout/topbar"
import { KpiCard } from "@/components/ui/kpi-card"
import { GraficaPipelineEquipo } from "@/components/charts/grafica-pipeline-equipo"
import { api } from "@/lib/api"
import { formatearEuros, formatearPorcentaje, colorWinRate, ETIQUETAS_ETAPA } from "@/lib/utils"
import type { ComercialRanking, Oportunidad } from "@/types"

// ── Tipos con const objects (TypeScript skill) ─────────────────────────────

const COLUMNA = {
  IMPORTE_GANADO: "importe_ganado",
  PIPELINE_ABIERTO: "pipeline_abierto",
  WIN_RATE: "win_rate",
  CERRADAS: "cerradas",
} as const

type Columna = (typeof COLUMNA)[keyof typeof COLUMNA]

// ── Panel de detalle individual ───────────────────────────────────────────

interface PanelDetalleProps {
  comercial: ComercialRanking
  onCerrar: () => void
}

function PanelDetalle({ comercial, onCerrar }: PanelDetalleProps) {
  const { data: pipeline = [], isLoading } = useQuery<Oportunidad[]>({
    queryKey: ["equipo-pipeline", comercial.propietario_id],
    queryFn: () => api.equipo.pipeline(comercial.propietario_id) as Promise<Oportunidad[]>,
  })

  return (
    <aside className="fixed right-0 top-0 h-full w-96 bg-white border-l border-zinc-200 shadow-xl z-50 flex flex-col">
      <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-200">
        <div>
          <p className="text-sm font-semibold text-zinc-900">{comercial.nombre_completo}</p>
          <p className="text-xs text-zinc-400 mt-0.5">Detalle del comercial</p>
        </div>
        <button
          onClick={onCerrar}
          className="text-zinc-400 hover:text-zinc-700 transition-colors text-lg leading-none"
        >
          ✕
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 p-5 border-b border-zinc-100">
        <div className="bg-zinc-50 rounded-lg p-3">
          <p className="text-xs text-zinc-500">Ganado</p>
          <p className="text-sm font-semibold text-zinc-900 mt-0.5">{formatearEuros(comercial.importe_ganado)}</p>
        </div>
        <div className="bg-zinc-50 rounded-lg p-3">
          <p className="text-xs text-zinc-500">Pipeline abierto</p>
          <p className="text-sm font-semibold text-zinc-900 mt-0.5">{formatearEuros(comercial.pipeline_abierto)}</p>
        </div>
        <div className="bg-zinc-50 rounded-lg p-3">
          <p className="text-xs text-zinc-500">Win Rate</p>
          <p className={cn("text-sm font-semibold mt-0.5", colorWinRate(comercial.win_rate))}>
            {formatearPorcentaje(comercial.win_rate)}
          </p>
        </div>
        <div className="bg-zinc-50 rounded-lg p-3">
          <p className="text-xs text-zinc-500">Cerradas</p>
          <p className="text-sm font-semibold text-zinc-900 mt-0.5">{comercial.cerradas}</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        <p className="text-xs font-semibold text-zinc-600 uppercase tracking-wide mb-3">
          Pipeline activo ({pipeline.length})
        </p>

        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-12 bg-zinc-100 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : pipeline.length === 0 ? (
          <p className="text-xs text-zinc-400">Sin oportunidades activas</p>
        ) : (
          <div className="space-y-2">
            {pipeline.map((op) => (
              <div
                key={op.id}
                className="flex items-start justify-between bg-zinc-50 rounded-lg px-3 py-2.5"
              >
                <div className="min-w-0 flex-1 mr-2">
                  <p className="text-xs font-medium text-zinc-800 truncate">{op.nombre}</p>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    {ETIQUETAS_ETAPA[op.etapa] ?? op.etapa}
                  </p>
                </div>
                <p className="text-xs font-semibold text-zinc-700 whitespace-nowrap">
                  {formatearEuros(op.importe)}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  )
}

// ── Componente principal ──────────────────────────────────────────────────

export default function PaginaEquipo() {
  const [columnaOrden, setColumnaOrden] = useState<Columna>(COLUMNA.IMPORTE_GANADO)
  const [ascendente, setAscendente] = useState(false)
  const [seleccionado, setSeleccionado] = useState<ComercialRanking | null>(null)

  const { data: ranking = [], isLoading } = useQuery<ComercialRanking[]>({
    queryKey: ["equipo-ranking"],
    queryFn: () => api.equipo.ranking() as Promise<ComercialRanking[]>,
  })

  const rankingOrdenado = [...ranking].sort((a, b) => {
    const diff = Number(a[columnaOrden]) - Number(b[columnaOrden])
    return ascendente ? diff : -diff
  })

  const totalGanado = ranking.reduce((s, c) => s + Number(c.importe_ganado), 0)
  const mejorWR = ranking.length ? Math.max(...ranking.map((c) => Number(c.win_rate))) : 0
  const totalPipeline = ranking.reduce((s, c) => s + Number(c.pipeline_abierto), 0)

  function toggleOrden(col: Columna) {
    if (columnaOrden === col) setAscendente((v) => !v)
    else {
      setColumnaOrden(col)
      setAscendente(false)
    }
  }

  function ThCol({
    col,
    children,
    className = "",
  }: {
    col: Columna
    children: React.ReactNode
    className?: string
  }) {
    const activa = columnaOrden === col
    return (
      <th
        className={cn(
          "px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wide cursor-pointer select-none hover:text-zinc-800 transition-colors",
          className
        )}
        onClick={() => toggleOrden(col)}
      >
        {children}
        <span className="ml-1 opacity-60">{activa ? (ascendente ? "↑" : "↓") : "↕"}</span>
      </th>
    )
  }

  return (
    <>
      <Topbar titulo="Equipo" subtitulo="Ranking y rendimiento del equipo comercial" />

      <main className="flex-1 p-2.5 md:p-3.5 space-y-5">
        {/* ── KPI strip ── */}
        {isLoading ? (
          <div className="grid grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-24 rounded-xl bg-zinc-200 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <KpiCard
              etiqueta="Comerciales activos"
              valor={String(ranking.length)}
              subtexto="Con oportunidades registradas"
              acento="azul"
            />
            <KpiCard
              etiqueta="Total importe ganado"
              valor={formatearEuros(totalGanado)}
              subtexto="Suma del equipo completo"
              acento="verde"
            />
            <KpiCard
              etiqueta="Mejor Win Rate"
              valor={formatearPorcentaje(mejorWR)}
              subtexto={`Pipeline abierto: ${formatearEuros(totalPipeline)}`}
              acento={mejorWR >= 90 ? "verde" : "ambar"}
            />
          </div>
        )}

        {/* ── Gráfica ── */}
        {ranking.length > 0 && (
          <div className="ui-panel p-5">
            <h2 className="text-sm font-semibold text-zinc-800 mb-1">
              Importe ganado vs pipeline abierto por comercial
            </h2>
            <p className="text-xs text-zinc-400 mb-4">Haz clic en la tabla para resaltar un comercial</p>
            <GraficaPipelineEquipo
              datos={rankingOrdenado}
              comercialSeleccionado={seleccionado?.propietario_id ?? null}
            />
          </div>
        )}

        {/* ── Tabla de ranking ── */}
        <div className="ui-panel overflow-hidden">
          <div className="px-5 py-4 border-b border-zinc-100">
            <h2 className="text-sm font-semibold text-zinc-800">Ranking del equipo</h2>
          </div>

          {isLoading ? (
            <div className="p-5 space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-10 bg-zinc-100 rounded animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-zinc-50 border-b border-zinc-100">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wide w-8">#</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wide">Comercial</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wide">Opps</th>
                    <ThCol col={COLUMNA.IMPORTE_GANADO}>Ganado</ThCol>
                    <ThCol col={COLUMNA.PIPELINE_ABIERTO}>Pipeline abierto</ThCol>
                    <ThCol col={COLUMNA.WIN_RATE}>Win Rate</ThCol>
                    <ThCol col={COLUMNA.CERRADAS}>Cerradas</ThCol>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-50">
                  {rankingOrdenado.map((comercial, idx) => {
                    const estaSeleccionado = seleccionado?.propietario_id === comercial.propietario_id
                    return (
                      <tr
                        key={comercial.propietario_id}
                        onClick={() => setSeleccionado(estaSeleccionado ? null : comercial)}
                        className={cn(
                          "cursor-pointer transition-colors hover:bg-zinc-50",
                          estaSeleccionado && "bg-red-50 border-l-2 border-l-sgs-rojo"
                        )}
                      >
                        <td className="px-4 py-3 text-xs text-zinc-400 font-mono">{idx + 1}</td>
                        <td className="px-4 py-3">
                          <p className="font-medium text-zinc-900">{comercial.nombre_completo}</p>
                          <p className="text-xs text-zinc-400">{comercial.total_oportunidades} oportunidades totales</p>
                        </td>
                        <td className="px-4 py-3 text-right text-zinc-600">{comercial.total_oportunidades}</td>
                        <td className="px-4 py-3 text-right font-semibold text-zinc-900">{formatearEuros(comercial.importe_ganado)}</td>
                        <td className="px-4 py-3 text-right text-zinc-600">{formatearEuros(comercial.pipeline_abierto)}</td>
                        <td className={cn("px-4 py-3 text-right font-semibold", colorWinRate(comercial.win_rate))}>
                          {formatearPorcentaje(comercial.win_rate)}
                        </td>
                        <td className="px-4 py-3 text-right text-zinc-600">{comercial.cerradas}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {seleccionado && (
        <>
          <div className="fixed inset-0 overlay-strong z-40" onClick={() => setSeleccionado(null)} />
          <PanelDetalle comercial={seleccionado} onCerrar={() => setSeleccionado(null)} />
        </>
      )}
    </>
  )
}
