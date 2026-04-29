"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { ChevronRight } from "lucide-react"
import { Topbar } from "@/components/layout/topbar"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import { useAppStore } from "@/store/use-app-store"
import type { ForecastResult, ForecastEquipo, CrossSellQueueItem, CuentaResumen } from "@/types"

// =============================================================================
// Helpers
// =============================================================================

function euros(v: number) {
  return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(v)
}

function mesLabel(yyyymm: string) {
  const [y, m] = yyyymm.split("-")
  const d = new Date(Number(y), Number(m) - 1, 1)
  return d.toLocaleDateString("es-ES", { month: "short", year: "2-digit" }).replace(" ", " '")
}

const ESCENARIOS = [
  { key: "pesimista", label: "Pesimista", color: "#ef4444", bg: "bg-red-50", border: "border-red-200", text: "text-red-700" },
  { key: "base",      label: "Base",      color: "#3b82f6", bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700" },
  { key: "optimista", label: "Optimista", color: "#22c55e", bg: "bg-green-50", border: "border-green-200", text: "text-green-700" },
] as const

type EscenarioKey = "pesimista" | "base" | "optimista"

const CONFIANZA_COLOR: Record<string, string> = {
  Alta: "bg-green-100 text-green-700",
  "Media-Alta": "bg-emerald-100 text-emerald-700",
  Media: "bg-amber-100 text-amber-700",
  "Media-Baja": "bg-orange-100 text-orange-700",
  Baja: "bg-red-100 text-red-700",
}

// =============================================================================
// Supuestos del modelo
// =============================================================================

function Supuestos() {
  const [abierto, setAbierto] = useState(false)
  return (
    <div className="border border-zinc-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setAbierto(!abierto)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm text-zinc-600 hover:bg-zinc-50 transition-colors"
      >
        <span className="font-medium">ℹ Supuestos del modelo</span>
        <span>{abierto ? "▲" : "▼"}</span>
      </button>
      {abierto && (
        <div className="px-4 pb-4 space-y-1.5 text-xs text-zinc-500 border-t border-zinc-100 pt-3">
          <p>· <strong>Pesimista:</strong> Baseline histórico (mediana mensual Won × 3 meses). Sin conversión de pipeline.</p>
          <p>· <strong>Base:</strong> Baseline × 3 + 10% del pipeline maduro convertido.</p>
          <p>· <strong>Optimista:</strong> Baseline × 3 + 20% pipeline maduro + 15% aceleración por cross-sell.</p>
          <p>· <strong>Pipeline maduro:</strong> Etapas Technically Approved + Estimation Sent + Contract Offer + Estimation Accepted.</p>
          <p>· <strong>Distribución mensual:</strong> 20% mes 1 · 35% mes 2 · 45% mes 3 (rampa, no lineal).</p>
          <p>· <strong>Ciclo mediana Won:</strong> 22 días · Datos: últimos 12 meses del histórico real.</p>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Barra de mes con valor
// =============================================================================

function BarraMes({
  label, valor, maximo, color,
}: { label: string; valor: number; maximo: number; color: string }) {
  const pct = maximo > 0 ? Math.round((valor / maximo) * 100) : 0
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-end gap-2">
        <div className="flex-1 bg-zinc-100 rounded-t-md overflow-hidden" style={{ height: 120 }}>
          <div
            className="w-full rounded-t-md transition-all duration-500"
            style={{ height: `${pct}%`, backgroundColor: color, marginTop: `${100 - pct}%` }}
          />
        </div>
      </div>
      <div className="text-center">
        <p className="text-xs font-semibold text-zinc-800">{euros(valor)}</p>
        <p className="text-[10px] text-zinc-400 uppercase tracking-wide">{label}</p>
      </div>
    </div>
  )
}

// =============================================================================
// Card de forecast personal
// =============================================================================

function ForecastCard({
  forecast,
  escenario,
}: {
  forecast: ForecastResult
  escenario: EscenarioKey
}) {
  const esc = ESCENARIOS.find((e) => e.key === escenario)!
  const data = forecast[escenario]
  const maximo = Math.max(data.m1, data.m2, data.m3, 1)

  return (
    <div className="bg-white rounded-xl border border-zinc-200 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-zinc-100">
        <h2 className="text-sm font-semibold text-zinc-800">Mi forecast — próximos 3 meses</h2>
        <p className="text-xs text-zinc-400 mt-0.5">{forecast.usuario_nombre}</p>
      </div>

      {/* Inputs del modelo */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 px-5 py-4 border-b border-zinc-100 bg-zinc-50">
        <div>
          <p className="text-[10px] uppercase tracking-widest text-zinc-400 mb-0.5">Pipeline maduro</p>
          <p className="text-sm font-semibold text-zinc-800">{euros(forecast.pipeline_maduro)}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-zinc-400 mb-0.5">Baseline mensual</p>
          <p className="text-sm font-semibold text-zinc-800">{euros(forecast.baseline_mediana)}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-zinc-400 mb-0.5">SBU dominante</p>
          <p className="text-sm font-semibold text-zinc-800 truncate">{forecast.sbu_dominante ?? "—"}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-zinc-400 mb-0.5">Win Rate histórico</p>
          <p className="text-sm font-semibold text-zinc-800">{forecast.wr_sbu.toFixed(1)}%</p>
        </div>
      </div>

      {/* Gráfica de barras */}
      <div className="px-5 py-5">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <BarraMes label={mesLabel(forecast.mes_1)} valor={data.m1} maximo={maximo} color={esc.color} />
          <BarraMes label={mesLabel(forecast.mes_2)} valor={data.m2} maximo={maximo} color={esc.color} />
          <BarraMes label={mesLabel(forecast.mes_3)} valor={data.m3} maximo={maximo} color={esc.color} />
        </div>
      </div>

      {/* Total */}
      <div className={cn("px-5 py-3 border-t border-zinc-100 flex items-center justify-between", esc.bg)}>
        <span className={cn("text-xs font-medium", esc.text)}>Total 3 meses · escenario {esc.label}</span>
        <span className={cn("text-lg font-bold", esc.text)}>{euros(data.total)}</span>
      </div>
    </div>
  )
}

// =============================================================================
// Tabla de equipo (admin / manager)
// =============================================================================

function TablaEquipo({ data, escenario }: { data: ForecastEquipo; escenario: EscenarioKey }) {
  const esc = ESCENARIOS.find((e) => e.key === escenario)!
  const campo = `${escenario}_total` as "pesimista_total" | "base_total" | "optimista_total"
  const total = data[`totales_${escenario}` as keyof ForecastEquipo] as number

  return (
    <div className="bg-white rounded-xl border border-zinc-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-zinc-100 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-800">Forecast de equipo</h2>
        <span className={cn("text-xs font-semibold px-2 py-0.5 rounded-full", esc.bg, esc.text)}>
          {esc.label} · {euros(total)}
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-xs">
          <thead>
            <tr className="bg-zinc-50 border-b border-zinc-100">
              <th className="text-left px-4 py-2.5 font-medium text-zinc-500">Comercial</th>
              <th className="text-left px-4 py-2.5 font-medium text-zinc-500">SBU</th>
              <th className="text-right px-4 py-2.5 font-medium text-zinc-500">Baseline/mes</th>
              <th className="text-right px-4 py-2.5 font-medium text-zinc-500">Pipeline maduro</th>
              <th className="text-right px-4 py-2.5 font-medium text-zinc-500">Forecast 3m</th>
            </tr>
          </thead>
          <tbody>
            {data.comerciales.map((c, i) => (
              <tr key={i} className="border-b border-zinc-50 hover:bg-zinc-50 transition-colors">
                <td className="px-4 py-2.5 font-medium text-zinc-800 truncate max-w-[160px]">{c.usuario_nombre}</td>
                <td className="px-4 py-2.5 text-zinc-500 truncate max-w-[120px]">{c.sbu_dominante ?? "—"}</td>
                <td className="px-4 py-2.5 text-right text-zinc-700">{euros(c.baseline_mediana)}</td>
                <td className="px-4 py-2.5 text-right text-zinc-700">{euros(c.pipeline_maduro)}</td>
                <td className={cn("px-4 py-2.5 text-right font-semibold", esc.text)}>{euros(c[campo])}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className={cn("border-t-2", esc.border)}>
              <td colSpan={4} className="px-4 py-3 text-xs font-semibold text-zinc-600">Total equipo</td>
              <td className={cn("px-4 py-3 text-right font-bold text-sm", esc.text)}>{euros(total)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

// =============================================================================
// Cola de cross-sell
// =============================================================================

function ColaCrossSell({
  items,
  recalculando,
  onRecalcular,
}: {
  items: CrossSellQueueItem[]
  recalculando: boolean
  onRecalcular: () => void
}) {
  const router = useRouter()

  if (!items.length) {
    return (
      <div className="bg-white rounded-xl border border-zinc-200 px-5 py-8 text-center">
        <p className="text-sm text-zinc-400">Sin cuentas de cross-sell identificadas esta semana.</p>
        <button
          onClick={onRecalcular}
          className="mt-3 text-xs text-blue-600 hover:underline"
        >
          Recalcular ahora
        </button>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-zinc-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-zinc-100 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-800">Cross-sell · mis cuentas prioritarias esta semana</h2>
          <p className="text-xs text-zinc-400 mt-0.5">Cuentas con 1 sola SBU ganada · ordenadas por potencial</p>
        </div>
        <button
          onClick={onRecalcular}
          disabled={recalculando}
          className="text-xs text-zinc-500 hover:text-zinc-800 border border-zinc-200 rounded-md px-2.5 py-1 transition-colors disabled:opacity-40"
        >
          {recalculando ? "Calculando…" : "↻ Recalcular"}
        </button>
      </div>

      <div className="divide-y divide-zinc-50">
        {items.map((item, i) => (
          <div key={item.id ?? i} className="px-5 py-4 hover:bg-zinc-50 transition-colors">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-semibold text-zinc-800 truncate">{item.cuenta_nombre}</span>
                  {item.confianza && (
                    <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded-full whitespace-nowrap", CONFIANZA_COLOR[item.confianza] ?? "bg-zinc-100 text-zinc-600")}>
                      {item.confianza}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-xs text-zinc-500 mb-2">
                  <span>SBU: <strong className="text-zinc-700">{item.sbu_actual ?? "—"}</strong></span>
                  <span>·</span>
                  <span>{item.ops_abiertas} ops abiertas</span>
                  <span>·</span>
                  <span>{euros(item.pipeline_abierto)} pipeline</span>
                </div>
                {item.productos_won && (
                  <p className="text-xs text-zinc-400 mb-1">Won: {item.productos_won}</p>
                )}
                {item.oportunidades_top && (
                  <p className="text-xs text-zinc-600 mb-1">
                    <span className="font-medium text-zinc-500">Potencial: </span>{item.oportunidades_top}
                  </p>
                )}
                {item.mensaje_comercial && (
                  <div className="mt-2 bg-blue-50 border border-blue-100 rounded-md px-3 py-2">
                    <p className="text-[11px] text-blue-700 leading-relaxed">{item.mensaje_comercial}</p>
                  </div>
                )}
              </div>
              <div className="flex flex-col gap-1.5 shrink-0">
                <button
                  onClick={() => router.push(`/cuentas?q=${encodeURIComponent(item.cuenta_nombre)}`)}
                  className="text-xs px-2.5 py-1 border border-zinc-200 rounded-md hover:bg-zinc-100 transition-colors text-zinc-600"
                >
                  Ver cuenta →
                </button>
                <button
                  onClick={() => router.push(`/deck?empresa=${encodeURIComponent(item.cuenta_nombre)}`)}
                  className="text-xs px-2.5 py-1 border border-zinc-200 rounded-md hover:bg-zinc-100 transition-colors text-zinc-600"
                >
                  Preparar deck →
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="px-5 py-2.5 border-t border-zinc-100 bg-zinc-50">
        <p className="text-[10px] text-zinc-400">Actualizado semanalmente · Score = ops×10 + pipeline/1000 + Top50×50</p>
      </div>
    </div>
  )
}

// =============================================================================
// Tabla de cartera del comercial
// =============================================================================

function TablaCartera({ propietarioId }: { propietarioId?: string }) {
  const router = useRouter()
  const [pagina, setPagina] = useState(1)
  const POR_PAGINA = 20

  const { data, isLoading } = useQuery<{
    total: number
    pagina: number
    por_pagina: number
    datos: CuentaResumen[]
  }>({
    queryKey: ["forecast-cartera", pagina, propietarioId],
    queryFn: () =>
      api.cuentas.listar({ pagina, por_pagina: POR_PAGINA, propietario_id: propietarioId }) as Promise<{
        total: number
        pagina: number
        por_pagina: number
        datos: CuentaResumen[]
      }>,
  })

  const totalPaginas = data ? Math.ceil(data.total / POR_PAGINA) : 1

  return (
    <div className="bg-white rounded-xl border border-zinc-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-zinc-100 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-800">Mi cartera</h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            {data ? `${data.total} cuentas · pipeline e histórico` : "Cargando..."}
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <div className="h-6 w-6 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
        </div>
      ) : !data?.datos.length ? (
        <div className="flex items-center justify-center h-32">
          <p className="text-sm text-zinc-400">No tienes cuentas asignadas.</p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-xs">
              <thead>
                <tr className="bg-zinc-50 border-b border-zinc-100">
                  <th className="text-left px-4 py-2.5 font-medium text-zinc-500">Cuenta</th>
                  <th className="text-right px-4 py-2.5 font-medium text-zinc-500">Pipeline activo</th>
                  <th className="text-right px-4 py-2.5 font-medium text-zinc-500">Ganado</th>
                  <th className="text-right px-4 py-2.5 font-medium text-zinc-500">Win rate</th>
                  <th className="text-right px-4 py-2.5 font-medium text-zinc-500">Ops activas</th>
                  <th className="text-right px-4 py-2.5 font-medium text-zinc-500">Última actividad</th>
                  <th className="w-8" />
                </tr>
              </thead>
              <tbody>
                {data.datos.map((cuenta) => (
                  <tr
                    key={cuenta.id}
                    onClick={() => router.push(`/cuentas/${cuenta.id}`)}
                    className="border-b border-zinc-50 hover:bg-zinc-50 transition-colors cursor-pointer group"
                  >
                    <td className="px-4 py-2.5 font-medium text-zinc-800 max-w-[200px] truncate">
                      {cuenta.nombre}
                    </td>
                    <td className="px-4 py-2.5 text-right text-zinc-700 tabular-nums">
                      {cuenta.pipeline_activo > 0
                        ? new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(cuenta.pipeline_activo)
                        : <span className="text-zinc-300">—</span>}
                    </td>
                    <td className="px-4 py-2.5 text-right text-zinc-600 tabular-nums">
                      {new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(cuenta.importe_ganado)}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <span className={cn(
                        "font-semibold px-1.5 py-0.5 rounded-full",
                        cuenta.win_rate >= 70 ? "bg-emerald-100 text-emerald-700"
                          : cuenta.win_rate >= 40 ? "bg-amber-100 text-amber-700"
                          : "bg-red-100 text-red-700",
                      )}>
                        {Number(cuenta.win_rate).toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right text-zinc-600">
                      {cuenta.oportunidades_activas > 0
                        ? <span className="text-emerald-600 font-medium">{cuenta.oportunidades_activas}</span>
                        : <span className="text-zinc-300">0</span>}
                    </td>
                    <td className="px-4 py-2.5 text-right text-zinc-400">
                      {cuenta.ultima_actividad ?? "—"}
                    </td>
                    <td className="px-3 py-2.5 text-zinc-300 group-hover:text-zinc-500 transition-colors">
                      <ChevronRight size={14} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPaginas > 1 && (
            <div className="px-5 py-2.5 border-t border-zinc-100 flex items-center justify-between">
              <p className="text-[10px] text-zinc-400">Pág. {pagina} de {totalPaginas}</p>
              <div className="flex gap-2">
                <button
                  disabled={pagina === 1}
                  onClick={() => setPagina(pagina - 1)}
                  className="px-2.5 py-1 text-[10px] border border-zinc-200 rounded hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  ← Ant.
                </button>
                <button
                  disabled={pagina >= totalPaginas}
                  onClick={() => setPagina(pagina + 1)}
                  className="px-2.5 py-1 text-[10px] border border-zinc-200 rounded hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Sig. →
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// =============================================================================
// Página principal
// =============================================================================

export default function PaginaForecast() {
  const queryClient = useQueryClient()
  const [escenario, setEscenario] = useState<EscenarioKey>("base")
  const [propietarioId, setPropietarioId] = useState("")
  const { isManager } = useAppStore()
  const propietarioFiltro = isManager() && propietarioId ? propietarioId : undefined

  const { data: comerciales = [] } = useQuery<Array<{ propietario_id: string; nombre_completo: string }>>({
    queryKey: ["equipo-ranking-selector-forecast"],
    queryFn: () => api.equipo.ranking() as Promise<Array<{ propietario_id: string; nombre_completo: string }>>,
    enabled: isManager(),
  })

  const { data: forecast, isLoading: cargandoForecast } = useQuery<ForecastResult>({
    queryKey: ["forecast-me", propietarioFiltro],
    queryFn: () => api.forecast.me(false, propietarioFiltro),
    enabled: !isManager() || Boolean(propietarioFiltro),
  })

  const { data: equipo, isLoading: cargandoEquipo } = useQuery<ForecastEquipo>({
    queryKey: ["forecast-equipo"],
    queryFn: () => api.forecast.equipo(),
    enabled: isManager(),
  })

  const { data: queue = [], isLoading: cargandoQueue } = useQuery<CrossSellQueueItem[]>({
    queryKey: ["forecast-crosssell-queue"],
    queryFn: () => api.forecast.crossSellQueue(10),
  })

  const mutRecalcularForecast = useMutation({
    mutationFn: () => api.forecast.me(true, propietarioFiltro),
    onSuccess: (data) => {
      queryClient.setQueryData(["forecast-me"], data)
      if (isManager()) queryClient.invalidateQueries({ queryKey: ["forecast-equipo"] })
    },
  })

  const mutRecalcularQueue = useMutation({
    mutationFn: () => api.forecast.crossSellQueue(10, true),
    onSuccess: (data) => queryClient.setQueryData(["forecast-crosssell-queue"], data),
  })

  return (
    <>
      <Topbar
        titulo="Forecast"
        subtitulo="Predicción de ingresos a 3 meses · modelo basado en datos reales del pipeline"
      />

      <main className="flex-1 p-2.5 md:p-3.5 space-y-5">
        {/* Selector de escenario + botón recalcular */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1 bg-white border border-zinc-200 rounded-lg p-1">
            {ESCENARIOS.map((e) => (
              <button
                key={e.key}
                onClick={() => setEscenario(e.key)}
                className={cn(
                  "px-4 py-1.5 rounded-md text-xs font-medium transition-all",
                  escenario === e.key
                    ? cn(e.bg, e.text, e.border, "border shadow-sm")
                    : "text-zinc-500 hover:text-zinc-700"
                )}
              >
                {e.label}
              </button>
            ))}
          </div>
          {isManager() && (
            <select
              value={propietarioId}
              onChange={(e) => setPropietarioId(e.target.value)}
              className="h-8 rounded-lg border border-zinc-300 bg-white px-2 text-xs text-zinc-700"
            >
              <option value="">Todos los comerciales</option>
              {comerciales.map((c) => (
                <option key={c.propietario_id} value={c.propietario_id}>{c.nombre_completo}</option>
              ))}
            </select>
          )}
          <button
            onClick={() => mutRecalcularForecast.mutate()}
            disabled={mutRecalcularForecast.isPending}
            className="text-xs px-3 py-1.5 border border-zinc-200 rounded-lg hover:bg-zinc-100 transition-colors text-zinc-600 disabled:opacity-40"
          >
            {mutRecalcularForecast.isPending ? "Recalculando…" : "↻ Recalcular con datos actuales"}
          </button>
        </div>

        {/* Forecast personal */}
        {isManager() && !propietarioFiltro ? (
          <div className="rounded-xl border border-zinc-200 bg-white px-5 py-8 text-sm text-zinc-500">
            Selecciona un comercial para ver su forecast detallado.
          </div>
        ) : cargandoForecast ? (
          <div className="h-64 rounded-xl bg-zinc-200 animate-pulse" />
        ) : forecast ? (
          <ForecastCard forecast={forecast} escenario={escenario} />
        ) : null}

        {/* Tabla de equipo (solo admin/manager) */}
        {isManager() && (
          cargandoEquipo ? (
            <div className="h-48 rounded-xl bg-zinc-200 animate-pulse" />
          ) : equipo ? (
            <TablaEquipo data={equipo} escenario={escenario} />
          ) : null
        )}

        {/* Cartera del comercial */}
        <TablaCartera propietarioId={propietarioFiltro} />

        {/* Cola de cross-sell */}
        {cargandoQueue ? (
          <div className="h-48 rounded-xl bg-zinc-200 animate-pulse" />
        ) : (
          <ColaCrossSell
            items={queue}
            recalculando={mutRecalcularQueue.isPending}
            onRecalcular={() => mutRecalcularQueue.mutate()}
          />
        )}

        {/* Supuestos */}
        <Supuestos />
      </main>
    </>
  )
}
