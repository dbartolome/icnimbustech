"use client"

import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { FileText, Presentation, Mic } from "lucide-react"
import { Topbar } from "@/components/layout/topbar"
import { KpiCard } from "@/components/ui/kpi-card"
import { GraficaProductos } from "@/components/charts/grafica-productos"
import { ArtefactoPicker } from "@/components/ui/artefacto-picker"
import { api } from "@/lib/api"
import { formatearEuros, formatearPorcentaje } from "@/lib/utils"
import { cn } from "@/lib/utils"
import { useDocumentoJob } from "@/hooks/use-documento-job"
import type { ProductoAnalisis, OportunidadEnProducto } from "@/types"

// ── Badge win rate ───────────────────────────────────────────────────────────

function BadgeWR({ wr }: { wr: number }) {
  const color =
    wr >= 80
      ? "bg-green-50 text-green-700"
      : wr >= 60
      ? "bg-amber-50 text-amber-700"
      : "bg-red-50 text-red-700"
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${color}`}>
      {formatearPorcentaje(wr)}
    </span>
  )
}

// ── Badge etapa ──────────────────────────────────────────────────────────────

function BadgeEtapa({ etapa }: { etapa: string }) {
  const estilos: Record<string, string> = {
    closed_won: "bg-green-50 text-green-700",
    closed_lost: "bg-red-50 text-red-600 opacity-70",
  }
  const estilo = estilos[etapa] ?? "bg-zinc-100 text-zinc-600"
  const etiqueta = etapa.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs ${estilo}`}>
      {etiqueta}
    </span>
  )
}

// ── Drawer de oportunidades del producto ─────────────────────────────────────

interface DrawerProductoProps {
  producto: ProductoAnalisis
  onClose: () => void
}

function DrawerProducto({ producto, onClose }: DrawerProductoProps) {
  const [tab, setTab] = useState<"oportunidades" | "repositorio">("oportunidades")
  const [sortByOpp, setSortByOpp] = useState<"importe" | "fecha" | "nombre" | "etapa">("importe")
  const [sortDirOpp, setSortDirOpp] = useState<"asc" | "desc">("desc")
  const { data: oportunidades = [], isLoading } = useQuery<OportunidadEnProducto[]>({
    queryKey: ["producto-oportunidades", producto.id],
    queryFn: () => api.productos.oportunidades(producto.id, 20) as Promise<OportunidadEnProducto[]>,
    enabled: !!producto.id,
  })
  const oportunidadesOrdenadas = useMemo(() => {
    const arr = [...oportunidades]
    arr.sort((a, b) => {
      if (sortByOpp === "importe") return Number(a.importe) - Number(b.importe)
      if (sortByOpp === "etapa") return String(a.etapa).localeCompare(String(b.etapa))
      if (sortByOpp === "nombre") return String(a.nombre).localeCompare(String(b.nombre))
      const da = new Date(a.fecha_decision ?? a.fecha_creacion ?? "1970-01-01").getTime()
      const db = new Date(b.fecha_decision ?? b.fecha_creacion ?? "1970-01-01").getTime()
      return da - db
    })
    if (sortDirOpp === "desc") arr.reverse()
    return arr
  }, [oportunidades, sortByOpp, sortDirOpp])
  const { lanzar } = useDocumentoJob()
  const [lanzando, setLanzando] = useState<string | null>(null) // "{opId}-{tipo}"

  async function generarDoc(opId: string, cuentaId: string, tipo: "pdf" | "pptx" | "briefing") {
    const key = `${opId}-${tipo}`
    setLanzando(key)
    try {
      const fn = tipo === "pdf"
        ? () => api.documentosJobs.generarPdf(cuentaId, { contexto: producto.nombre, contextoTipo: "producto", contextoId: producto.id })
        : tipo === "pptx"
        ? () => api.documentosJobs.generarPptx(cuentaId, { contexto: producto.nombre, contextoTipo: "producto", contextoId: producto.id })
        : () => api.documentosJobs.generarBriefing(cuentaId, { contexto: producto.nombre, contextoTipo: "producto", contextoId: producto.id })
      await lanzar(tipo, fn)
    } finally {
      setLanzando(null)
    }
  }

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 overlay-strong z-40"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed top-0 right-0 h-full w-full sm:w-[480px] bg-white shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="px-5 py-4 border-b border-zinc-100 flex items-center justify-between shrink-0">
          <div>
            <h2 className="text-sm font-semibold text-zinc-900">{producto.nombre}</h2>
            <p className="text-xs text-zinc-400 mt-0.5">Top oportunidades · últimas 20</p>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-700 text-xl leading-none transition-colors"
          >
            ×
          </button>
        </div>

        {/* Resumen del producto */}
        <div className="px-5 py-4 bg-zinc-50 border-b border-zinc-100 grid grid-cols-1 sm:grid-cols-3 gap-3 shrink-0">
          <div>
            <p className="text-xs text-zinc-400">Win Rate</p>
            <BadgeWR wr={Number(producto.win_rate)} />
          </div>
          <div>
            <p className="text-xs text-zinc-400">Importe ganado</p>
            <p className="text-sm font-semibold text-zinc-900">{formatearEuros(producto.importe_ganado)}</p>
          </div>
          <div>
            <p className="text-xs text-zinc-400">Total opps</p>
            <p className="text-sm font-semibold text-zinc-900">
              {producto.total_oportunidades}
              <span className="text-xs font-normal text-zinc-400 ml-1">({producto.oportunidades_ganadas} ganadas)</span>
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-zinc-100 shrink-0">
          <button
            onClick={() => setTab("oportunidades")}
            className={cn(
              "flex-1 py-2.5 text-xs font-medium transition-colors",
              tab === "oportunidades"
                ? "text-sgs-rojo border-b-2 border-sgs-rojo -mb-px"
                : "text-zinc-500 hover:text-zinc-700",
            )}
          >
            Oportunidades
          </button>
          <button
            onClick={() => setTab("repositorio")}
            className={cn(
              "flex-1 py-2.5 text-xs font-medium transition-colors",
              tab === "repositorio"
                ? "text-sgs-rojo border-b-2 border-sgs-rojo -mb-px"
                : "text-zinc-500 hover:text-zinc-700",
            )}
          >
            Repositorio IA
          </button>
        </div>

        {/* Contenido */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {tab === "repositorio" ? (
            <ArtefactoPicker contextoTipo="producto" contextoId={producto.id} modoModal />
          ) : (
            <>
          <div className="mb-3 flex items-center justify-end gap-2">
            <select
              value={sortByOpp}
              onChange={(e) => setSortByOpp(e.target.value as "importe" | "fecha" | "nombre" | "etapa")}
              className="text-[11px] border border-zinc-200 rounded-md px-2 py-1 bg-white text-zinc-600"
            >
              <option value="importe">Orden: importe</option>
              <option value="fecha">Orden: fecha</option>
              <option value="nombre">Orden: nombre</option>
              <option value="etapa">Orden: etapa</option>
            </select>
            <select
              value={sortDirOpp}
              onChange={(e) => setSortDirOpp(e.target.value as "asc" | "desc")}
              className="text-[11px] border border-zinc-200 rounded-md px-2 py-1 bg-white text-zinc-600"
            >
              <option value="desc">Descendente</option>
              <option value="asc">Ascendente</option>
            </select>
          </div>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-16 rounded-lg bg-zinc-100 animate-pulse" />
              ))}
            </div>
          ) : oportunidadesOrdenadas.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-sm text-zinc-400">Sin oportunidades registradas para este producto.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {oportunidadesOrdenadas.map((op) => {
                const fecha = op.fecha_decision
                  ? new Date(op.fecha_decision).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })
                  : op.fecha_creacion
                  ? new Date(op.fecha_creacion).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })
                  : "—"
                return (
                  <div
                    key={op.id}
                    className="p-3 rounded-lg border border-zinc-100 hover:border-zinc-200 transition-colors bg-white"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium text-zinc-900 leading-snug line-clamp-2">
                        {op.nombre}
                      </p>
                      <p className="text-sm font-semibold text-zinc-900 shrink-0">
                        {formatearEuros(op.importe)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                      <BadgeEtapa etapa={op.etapa} />
                      {op.cuenta_nombre && (
                        <span className="text-xs text-zinc-500">{op.cuenta_nombre}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-1">
                      {op.propietario_nombre && (
                        <span className="text-xs text-zinc-400">{op.propietario_nombre}</span>
                      )}
                      <span className="text-xs text-zinc-300">·</span>
                      <span className="text-xs text-zinc-400">{fecha}</span>
                    </div>
                    {op.cuenta_id && (
                      <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-zinc-50">
                        {(["pdf", "pptx", "briefing"] as const).map((tipo) => {
                          const key = `${op.id}-${tipo}`
                          const cargando = lanzando === key
                          const Icono = tipo === "pdf" ? FileText : tipo === "pptx" ? Presentation : Mic
                          const titulo = tipo === "pdf" ? "PDF" : tipo === "pptx" ? "Presentación" : "Audio"
                          return (
                            <button
                              key={tipo}
                              onClick={() => generarDoc(op.id, op.cuenta_id!, tipo)}
                              disabled={!!lanzando}
                              title={`Generar ${titulo} para ${op.cuenta_nombre ?? "cuenta"}`}
                              className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded-md border border-zinc-200 text-zinc-500 hover:border-zinc-400 hover:text-zinc-800 disabled:opacity-40 transition-colors"
                            >
                              {cargando ? (
                                <span className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
                              ) : (
                                <Icono size={10} />
                              )}
                              {titulo}
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
            </>
          )}
        </div>
      </div>
    </>
  )
}

// ── Página principal ─────────────────────────────────────────────────────────

export default function PaginaProductos() {
  const [productoSeleccionado, setProductoSeleccionado] = useState<ProductoAnalisis | null>(null)
  const [sortBy, setSortBy] = useState<"win_rate" | "importe_ganado" | "ticket_medio" | "total_oportunidades" | "oportunidades_ganadas" | "nombre">("win_rate")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")

  const { data: productos = [], isLoading } = useQuery<ProductoAnalisis[]>({
    queryKey: ["productos-analisis", sortBy, sortDir],
    queryFn: () => api.productos.analisis({ sort_by: sortBy, sort_dir: sortDir }) as Promise<ProductoAnalisis[]>,
  })

  function cambiarOrden(columna: typeof sortBy) {
    if (sortBy === columna) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"))
      return
    }
    setSortBy(columna)
    setSortDir(columna === "nombre" ? "asc" : "desc")
  }

  function iconoOrden(columna: typeof sortBy) {
    if (sortBy !== columna) return "↕"
    return sortDir === "asc" ? "↑" : "↓"
  }

  const activos = productos.filter((p) => p.total_oportunidades > 0)
  const mejorWR = activos.length ? Math.max(...activos.map((p) => Number(p.win_rate))) : 0
  const totalGanado = activos.reduce((s, p) => s + Number(p.importe_ganado), 0)
  const ticketMedio =
    activos.reduce((s, p) => s + Number(p.ticket_medio), 0) / (activos.length || 1)

  const productoDestacado = activos.find((p) => Number(p.win_rate) === mejorWR)
  const productosOrdenados = useMemo(() => productos, [productos])

  return (
    <>
      <Topbar titulo="Productos" subtitulo="Win rate y volumen por norma / producto" />

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
              etiqueta="Mejor Win Rate"
              valor={formatearPorcentaje(mejorWR)}
              subtexto={productoDestacado?.nombre ?? ""}
              acento="verde"
            />
            <KpiCard
              etiqueta="Total importe ganado"
              valor={formatearEuros(totalGanado)}
              subtexto={`${activos.length} productos activos`}
              acento="azul"
            />
            <KpiCard
              etiqueta="Ticket medio ganado"
              valor={formatearEuros(ticketMedio)}
              subtexto="Promedio entre productos activos"
              acento="ambar"
            />
          </div>
        )}

        {/* ── Gráfica WR por producto ── */}
        {activos.length > 0 && (
          <div className="ui-panel p-5">
            <h2 className="text-sm font-semibold text-zinc-800 mb-1">
              Win Rate por producto / norma
            </h2>
            <p className="text-xs text-zinc-400 mb-4">
              Verde ≥ 80% · Ámbar ≥ 60% · Rojo &lt; 60% · Clic en fila para ver oportunidades
            </p>
            <GraficaProductos datos={activos} />
          </div>
        )}

        {/* ── Tabla detallada ── */}
        <div className="ui-panel overflow-hidden">
          <div className="px-5 py-4 border-b border-zinc-100">
            <h2 className="text-sm font-semibold text-zinc-800">Análisis por producto</h2>
            <p className="text-xs text-zinc-400 mt-0.5">Haz clic en una fila para ver sus oportunidades</p>
            <div className="mt-2 flex items-center gap-2">
              <select
                value={sortBy}
                onChange={(e) => cambiarOrden(e.target.value as typeof sortBy)}
                className="text-xs border border-zinc-200 rounded-md px-2 py-1 bg-white"
              >
                <option value="win_rate">Orden: win rate</option>
                <option value="importe_ganado">Orden: importe ganado</option>
                <option value="ticket_medio">Orden: ticket medio</option>
                <option value="total_oportunidades">Orden: total opps</option>
                <option value="oportunidades_ganadas">Orden: ganadas</option>
                <option value="nombre">Orden: nombre</option>
              </select>
              <select
                value={sortDir}
                onChange={(e) => setSortDir(e.target.value as "asc" | "desc")}
                className="text-xs border border-zinc-200 rounded-md px-2 py-1 bg-white"
              >
                <option value="desc">Descendente</option>
                <option value="asc">Ascendente</option>
              </select>
            </div>
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
                    <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                      <button type="button" onClick={() => cambiarOrden("nombre")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                        Producto / Norma <span>{iconoOrden("nombre")}</span>
                      </button>
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                      <button type="button" onClick={() => cambiarOrden("total_oportunidades")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                        Total opps <span>{iconoOrden("total_oportunidades")}</span>
                      </button>
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                      <button type="button" onClick={() => cambiarOrden("oportunidades_ganadas")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                        Ganadas <span>{iconoOrden("oportunidades_ganadas")}</span>
                      </button>
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                      <button type="button" onClick={() => cambiarOrden("importe_ganado")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                        Importe ganado <span>{iconoOrden("importe_ganado")}</span>
                      </button>
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                      <button type="button" onClick={() => cambiarOrden("ticket_medio")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                        Ticket medio <span>{iconoOrden("ticket_medio")}</span>
                      </button>
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                      <button type="button" onClick={() => cambiarOrden("win_rate")} className="inline-flex items-center gap-1 hover:text-zinc-700">
                        Win Rate <span>{iconoOrden("win_rate")}</span>
                      </button>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-50">
                  {productosOrdenados.map((producto) => {
                    const sinDatos = producto.total_oportunidades === 0
                    const seleccionado = productoSeleccionado?.id === producto.id
                    return (
                      <tr
                        key={producto.id}
                        onClick={() => !sinDatos && setProductoSeleccionado(seleccionado ? null : producto)}
                        className={
                          sinDatos
                            ? "opacity-40"
                            : seleccionado
                            ? "bg-red-50 border-l-2 border-l-red-400"
                            : "hover:bg-zinc-50 cursor-pointer transition-colors"
                        }
                      >
                        <td className="px-4 py-3">
                          <p className="font-medium text-zinc-900">{producto.nombre}</p>
                          {sinDatos && (
                            <p className="text-xs text-zinc-400">Sin oportunidades registradas</p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right text-zinc-600">
                          {producto.total_oportunidades}
                        </td>
                        <td className="px-4 py-3 text-right text-zinc-600">
                          {producto.oportunidades_ganadas}
                        </td>
                        <td className="px-4 py-3 text-right font-semibold text-zinc-900">
                          {sinDatos ? "—" : formatearEuros(producto.importe_ganado)}
                        </td>
                        <td className="px-4 py-3 text-right text-zinc-600">
                          {sinDatos ? "—" : formatearEuros(producto.ticket_medio)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {sinDatos ? (
                            <span className="text-zinc-300 text-xs">—</span>
                          ) : (
                            <BadgeWR wr={Number(producto.win_rate)} />
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {productoSeleccionado && (
        <DrawerProducto
          producto={productoSeleccionado}
          onClose={() => setProductoSeleccionado(null)}
        />
      )}
    </>
  )
}
