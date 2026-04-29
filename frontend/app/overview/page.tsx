"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Topbar } from "@/components/layout/topbar"
import { KpiCard } from "@/components/ui/kpi-card"
import { GraficaEvolucion } from "@/components/charts/grafica-evolucion"
import { api } from "@/lib/api"
import { formatearEuros, formatearPorcentaje, ETIQUETAS_ETAPA } from "@/lib/utils"
import { useAppStore } from "@/store/use-app-store"
import type { KpisDashboard, PuntoEvolucion, EtapaFunnel, BreakdownSbu } from "@/types"

export default function PaginaOverview() {
  const [incluirFantasmas, setIncluirFantasmas] = useState(true)
  const [propietarioId, setPropietarioId] = useState("")
  const isManager = useAppStore((s) => s.isManager)
  const puedeFiltrarComercial = isManager()
  const propietarioFiltro = puedeFiltrarComercial && propietarioId ? propietarioId : undefined

  const { data: comerciales = [] } = useQuery<Array<{ propietario_id: string; nombre_completo: string }>>({
    queryKey: ["equipo-ranking-selector-overview"],
    queryFn: () => api.equipo.ranking() as Promise<Array<{ propietario_id: string; nombre_completo: string }>>,
    enabled: puedeFiltrarComercial,
  })

  const { data: kpis, isLoading: cargandoKpis } = useQuery<KpisDashboard>({
    queryKey: ["dashboard-kpis", incluirFantasmas, propietarioFiltro],
    queryFn: () => api.dashboard.kpis(incluirFantasmas, propietarioFiltro) as unknown as Promise<KpisDashboard>,
    refetchInterval: 5 * 60 * 1000,
  })

  const { data: evolucion = [] } = useQuery<PuntoEvolucion[]>({
    queryKey: ["dashboard-evolucion", incluirFantasmas, propietarioFiltro],
    queryFn: () => api.dashboard.evolucion(incluirFantasmas, propietarioFiltro) as Promise<PuntoEvolucion[]>,
  })

  const { data: funnel = [] } = useQuery<EtapaFunnel[]>({
    queryKey: ["pipeline-funnel", propietarioFiltro],
    queryFn: () => api.pipeline.funnel(propietarioFiltro) as Promise<EtapaFunnel[]>,
  })

  const { data: sbuDatos = [] } = useQuery<BreakdownSbu[]>({
    queryKey: ["dashboard-sbu", incluirFantasmas, propietarioFiltro],
    queryFn: () => api.dashboard.sbu(incluirFantasmas, propietarioFiltro) as Promise<BreakdownSbu[]>,
  })

  const maxImporteSbu = Math.max(...sbuDatos.map((s) => s.pipeline_activo), 1)

  return (
    <>
      <Topbar titulo="Dashboard" subtitulo="Resumen ejecutivo del pipeline comercial" />

      <main className="flex-1 p-2.5 md:p-3.5 space-y-5">
        {/* ── Toggle calidad de datos ── */}
        <div className="flex items-center justify-end">
          {puedeFiltrarComercial && (
            <select
              value={propietarioId}
              onChange={(e) => setPropietarioId(e.target.value)}
              className="mr-2 h-9 rounded-lg border border-white/20 bg-black/20 px-2 text-xs text-white"
            >
              <option value="">Todos los comerciales</option>
              {comerciales.map((c) => (
                <option key={c.propietario_id} value={c.propietario_id}>{c.nombre_completo}</option>
              ))}
            </select>
          )}
          <button
            onClick={() => setIncluirFantasmas(!incluirFantasmas)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
              incluirFantasmas
                ? "chip-warn border-white/15"
                : "chip-success border-white/15"
            }`}
            title={incluirFantasmas
              ? "Mostrando datos con oportunidades importe=0. Clic para filtrar."
              : "Mostrando solo oportunidades con importe > 0. Clic para incluir todas."
            }
          >
            {incluirFantasmas ? (
              <>⚠ Incluyendo {293} ops fantasma</>
            ) : (
              <>✓ Solo datos reales</>
            )}
          </button>
        </div>

        {/* ── KPI Strip ── */}
        {cargandoKpis ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-24 rounded-2xl bg-[var(--color-card-soft)] animate-pulse" />
            ))}
          </div>
        ) : kpis ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <KpiCard
              etiqueta="Pipeline activo"
              valor={formatearEuros(kpis.pipeline_activo)}
              valorRaw={kpis.pipeline_activo}
              formato={{ style: "currency", currency: "EUR", notation: "compact", maximumFractionDigits: 1 }}
              subtexto={`${kpis.oportunidades_activas} oportunidades`}
              acento="rojo"
            />
            <KpiCard
              etiqueta="Cerrado ganado"
              valor={formatearEuros(kpis.importe_ganado)}
              valorRaw={kpis.importe_ganado}
              formato={{ style: "currency", currency: "EUR", notation: "compact", maximumFractionDigits: 1 }}
              subtexto={`${kpis.oportunidades_ganadas} operaciones`}
              acento="verde"
            />
            <KpiCard
              etiqueta="Win Rate"
              valor={formatearPorcentaje(kpis.win_rate_global)}
              valorRaw={kpis.win_rate_global / 100}
              formato={{ style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 }}
              subtexto="Won / (Won + Lost)"
              acento={kpis.win_rate_global >= 70 ? "verde" : "rojo"}
            />
            <KpiCard
              etiqueta="Ticket medio"
              valor={formatearEuros(kpis.ticket_medio_ganado)}
              valorRaw={kpis.ticket_medio_ganado}
              formato={{ style: "currency", currency: "EUR", notation: "compact", maximumFractionDigits: 0 }}
              subtexto="En oportunidades ganadas"
              acento="ambar"
            />
            <KpiCard
              etiqueta="Pipeline total"
              valor={formatearEuros(kpis.pipeline_total)}
              valorRaw={kpis.pipeline_total}
              formato={{ style: "currency", currency: "EUR", notation: "compact", maximumFractionDigits: 1 }}
              subtexto={`${kpis.total_oportunidades} oportunidades`}
              acento="rojo"
            />
          </div>
        ) : null}

        {/* ── Fila central ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Evolución mensual */}
          <div className="glass-panel-strong glass-border rounded-2xl p-5">
            <h2 className="text-sm font-semibold surface-title mb-4">Evolución mensual</h2>
            {evolucion.length > 0
              ? <GraficaEvolucion datos={evolucion} />
              : <div className="h-52 flex items-center justify-center surface-subtitle text-sm">Sin datos</div>
            }
          </div>

          {/* Funnel activo */}
          <div className="glass-panel-strong glass-border rounded-2xl p-5">
            <h2 className="text-sm font-semibold surface-title mb-4">Funnel activo</h2>
            <div className="space-y-3">
              {funnel.length === 0 && (
                <p className="text-sm surface-subtitle">Sin datos</p>
              )}
              {funnel.map((etapa) => {
                const maxImporte = Math.max(...funnel.map((e) => Number(e.importe_total)), 1)
                const pct = (Number(etapa.importe_total) / maxImporte) * 100
                return (
                  <div key={etapa.etapa}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="surface-subtitle">
                        {ETIQUETAS_ETAPA[etapa.etapa] ?? etapa.etapa}
                      </span>
                      <span className="font-medium surface-title">
                        {formatearEuros(Number(etapa.importe_total))}
                        <span className="surface-subtitle ml-1">· {etapa.num_oportunidades}</span>
                      </span>
                    </div>
                    <div className="h-1.5 bg-[var(--color-card-soft-2)] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all bg-gradient-to-r from-sgs-rojo via-[#e05063] to-[#f2c0c7]"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* ── Breakdown SBU ── */}
        <div className="glass-panel-strong glass-border rounded-2xl p-5">
          <h2 className="text-sm font-semibold surface-title mb-4">Pipeline activo por SBU</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sbuDatos.filter((s) => s.pipeline_activo > 0).map((sbu) => {
              const pct = (sbu.pipeline_activo / maxImporteSbu) * 100
              return (
                <div key={sbu.sbu} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium surface-title">{sbu.sbu}</span>
                    <span className="surface-subtitle">{formatearEuros(sbu.pipeline_activo)}</span>
                  </div>
                  <div className="h-2 bg-[var(--color-card-soft-2)] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-sgs-rojo to-[#d72a45]"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <p className="text-xs surface-subtitle">
                    WR {formatearPorcentaje(sbu.win_rate)} · {sbu.oportunidades_activas} activas
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      </main>
    </>
  )
}
