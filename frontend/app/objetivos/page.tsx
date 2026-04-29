"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Topbar } from "@/components/layout/topbar"
import { ArtefactoPicker } from "@/components/ui/artefacto-picker"
import { api } from "@/lib/api"
import { formatearEuros } from "@/lib/utils"
import { useDocumentoJob } from "@/hooks/use-documento-job"
import { useAppStore } from "@/store/use-app-store"
import type { ObjetivoComercial, ObjetivoDetalle } from "@/types"

type Orden = "asc" | "desc"

export default function ObjetivosPage() {
  const { isManager } = useAppStore()
  const qc = useQueryClient()
  const { lanzar } = useDocumentoJob()
  const [pagina, setPagina] = useState(1)
  const [estado, setEstado] = useState<string>("")
  const [busqueda, setBusqueda] = useState("")
  const [sortBy, setSortBy] = useState("score_impacto")
  const [sortDir, setSortDir] = useState<Orden>("desc")
  const [propietarioId, setPropietarioId] = useState("")
  const [objetivoDetalleId, setObjetivoDetalleId] = useState<string | null>(null)
  const [artefactSortBy, setArtefactSortBy] = useState<"fecha" | "tipo" | "titulo">("fecha")
  const [artefactSortDir, setArtefactSortDir] = useState<Orden>("desc")

  const { data: comerciales = [] } = useQuery<Array<{ propietario_id: string; nombre_completo: string }>>({
    queryKey: ["equipo-ranking-selector-objetivos"],
    queryFn: () => api.equipo.ranking() as Promise<Array<{ propietario_id: string; nombre_completo: string }>>,
    enabled: isManager(),
  })
  const propietarioFiltro = isManager() && propietarioId ? propietarioId : undefined

  const { data, isLoading } = useQuery({
    queryKey: ["objetivos", pagina, estado, busqueda, sortBy, sortDir, propietarioFiltro],
    queryFn: () =>
      api.objetivos.listar({
        propietario_id: propietarioFiltro,
        pagina,
        por_pagina: 20,
        estado: estado || undefined,
        busqueda: busqueda || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
      }) as Promise<{ total: number; pagina: number; por_pagina: number; datos: ObjetivoComercial[] }>,
  })

  const { mutate: sugerir, isPending: sugiriendo } = useMutation({
    mutationFn: () => api.objetivos.sugerir(20, true),
    onSuccess: (rows) => {
      const total = Array.isArray(rows) ? rows.length : 0
      toast.success(`Sugerencias generadas: ${total}`)
      qc.invalidateQueries({ queryKey: ["objetivos"] })
    },
    onError: (e: Error) => toast.error(e.message || "No se pudieron generar sugerencias."),
  })

  const { mutate: actualizarEstado } = useMutation({
    mutationFn: ({ id, nuevoEstado }: { id: string; nuevoEstado: string }) => api.objetivos.actualizar(id, { estado: nuevoEstado }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["objetivos"] }),
    onError: (e: Error) => toast.error(e.message || "No se pudo actualizar el objetivo."),
  })

  const { data: detalleData, isLoading: cargandoDetalle } = useQuery({
    queryKey: ["objetivo-detalle", objetivoDetalleId],
    queryFn: () => api.objetivos.detalle(objetivoDetalleId as string) as Promise<ObjetivoDetalle>,
    enabled: Boolean(objetivoDetalleId),
  })

  const datos = data?.datos ?? []
  const artefactosOrdenados = useMemo(() => {
    const artefactos = [...(detalleData?.artefactos ?? [])]
    artefactos.sort((a, b) => {
      if (artefactSortBy === "tipo") return String(a.tipo).localeCompare(String(b.tipo))
      if (artefactSortBy === "titulo") return String(a.titulo ?? "").localeCompare(String(b.titulo ?? ""))
      return new Date(a.actualizado_en).getTime() - new Date(b.actualizado_en).getTime()
    })
    if (artefactSortDir === "desc") artefactos.reverse()
    return artefactos
  }, [detalleData?.artefactos, artefactSortBy, artefactSortDir])

  const totalPaginas = useMemo(() => {
    const total = data?.total ?? 0
    const porPagina = data?.por_pagina ?? 20
    return Math.max(1, Math.ceil(total / porPagina))
  }, [data?.total, data?.por_pagina])

  const lanzarGeneracionObjetivo = async (
    objetivo: ObjetivoComercial,
    tipo: "pdf" | "pptx" | "briefing",
  ) => {
    if (!objetivo.cuenta_id) {
      toast.error("El objetivo no tiene cuenta asociada.")
      return
    }

    const contextoTipo = objetivo.oportunidad_id ? ("oportunidad" as const) : ("cuenta" as const)
    const contextoId = objetivo.oportunidad_id ?? objetivo.cuenta_id ?? undefined
    const contexto = {
      contextoTipo,
      contextoId,
      contexto: objetivo.titulo,
    }

    const lanzarFn = () => {
      if (tipo === "pdf") return api.documentosJobs.generarPdf(objetivo.cuenta_id as string, contexto)
      if (tipo === "pptx") return api.documentosJobs.generarPptx(objetivo.cuenta_id as string, contexto)
      return api.documentosJobs.generarBriefing(objetivo.cuenta_id as string, contexto)
    }

    const etiqueta = tipo === "pdf" ? "PDF" : tipo === "pptx" ? "Presentación" : "Briefing"

    await lanzar(
      tipo,
      lanzarFn,
      async (estadoFinal) => {
        const artefactoIdRaw = (estadoFinal as { artefacto_id?: unknown }).artefacto_id
        const artefactoId = typeof artefactoIdRaw === "string" ? artefactoIdRaw : null
        if (artefactoId) {
          try {
            await api.objetivos.vincularArtefacto(objetivo.id, artefactoId, "generado")
            toast.success(`${etiqueta} generado y vinculado al objetivo.`)
            qc.invalidateQueries({ queryKey: ["objetivos"] })
            return
          } catch {
            // Si falla la vinculación, mantenemos éxito de generación.
          }
        }
        toast.success(`${etiqueta} generado.`)
      },
      (error) => toast.error(error || `No se pudo generar ${etiqueta}.`),
    )
  }

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setObjetivoDetalleId(null)
    }
    if (objetivoDetalleId) window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [objetivoDetalleId])

  return (
    <>
      <Topbar titulo="Objetivos" subtitulo="Prioriza oportunidades y lanza acciones IC por objetivo" />

      <main className="flex-1 p-2.5 md:p-3.5 space-y-4 w-full">
        <section className="glass-panel glass-border rounded-2xl p-4 md:p-5 flex flex-col md:flex-row md:items-center gap-3 md:gap-4">
          <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-2">
            <input
              value={busqueda}
              onChange={(e) => { setPagina(1); setBusqueda(e.target.value) }}
              placeholder="Buscar por título o descripción"
              className="h-10 rounded-xl border border-white/20 bg-black/20 px-3 text-sm text-white placeholder:text-zinc-400"
            />
            <select
              value={estado}
              onChange={(e) => { setPagina(1); setEstado(e.target.value) }}
              className="h-10 rounded-xl border border-white/20 bg-black/20 px-3 text-sm text-white"
            >
              <option value="">Todos los estados</option>
              <option value="abierto">Abierto</option>
              <option value="en_progreso">En progreso</option>
              <option value="bloqueado">Bloqueado</option>
              <option value="completado">Completado</option>
            </select>
            <select
              value={`${sortBy}:${sortDir}`}
              onChange={(e) => {
                const [col, dir] = e.target.value.split(":")
                setSortBy(col)
                setSortDir((dir as Orden) || "desc")
              }}
              className="h-10 rounded-xl border border-white/20 bg-black/20 px-3 text-sm text-white"
            >
              <option value="score_impacto:desc">Impacto ↓</option>
              <option value="score_confianza:desc">Confianza ↓</option>
              <option value="prioridad:asc">Prioridad ↑</option>
              <option value="actualizado_en:desc">Actualizado ↓</option>
              <option value="fecha_objetivo:asc">Fecha objetivo ↑</option>
            </select>
            {isManager() && (
              <select
                value={propietarioId}
                onChange={(e) => { setPagina(1); setPropietarioId(e.target.value) }}
                className="h-10 rounded-xl border border-white/20 bg-black/20 px-3 text-sm text-white"
              >
                <option value="">Todos los comerciales</option>
                {comerciales.map((c) => (
                  <option key={c.propietario_id} value={c.propietario_id}>{c.nombre_completo}</option>
                ))}
              </select>
            )}
          </div>
          <button
            type="button"
            onClick={() => sugerir()}
            disabled={sugiriendo}
            className="h-10 px-4 rounded-xl bg-sgs-rojo text-white text-sm font-semibold disabled:opacity-50"
          >
            {sugiriendo ? "Analizando..." : "Sugerir objetivos IC"}
          </button>
        </section>

        <section className="glass-panel glass-border rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-zinc-300 border-b border-white/15">
                  <th className="px-4 py-3 font-semibold">Objetivo</th>
                  <th className="px-4 py-3 font-semibold">Cuenta</th>
                  <th className="px-4 py-3 font-semibold">Impacto</th>
                  <th className="px-4 py-3 font-semibold">Confianza</th>
                  <th className="px-4 py-3 font-semibold">Artefactos IC</th>
                  <th className="px-4 py-3 font-semibold">Estado</th>
                  <th className="px-4 py-3 font-semibold">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-zinc-400">Cargando objetivos...</td></tr>
                ) : datos.length === 0 ? (
                  <tr><td colSpan={7} className="px-4 py-10 text-center text-zinc-400">No hay objetivos. Pulsa “Sugerir objetivos IC”.</td></tr>
                ) : (
                  datos.map((obj) => (
                    <tr key={obj.id} className="border-b border-white/10 last:border-b-0">
                      <td className="px-4 py-3 align-top">
                        <p className="font-semibold text-white">{obj.titulo}</p>
                        <p className="text-xs text-zinc-400 mt-1">{obj.tipo_objetivo} · prioridad {obj.prioridad}</p>
                        {obj.oportunidad_id && (
                          <p className="text-xs text-zinc-400 mt-1">{obj.oportunidad_nombre}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-zinc-200">{obj.cuenta_nombre ?? "—"}</td>
                      <td className="px-4 py-3 text-zinc-100 font-semibold">{formatearEuros(obj.score_impacto || 0)}</td>
                      <td className="px-4 py-3 text-zinc-100">{Number(obj.score_confianza || 0).toFixed(1)}%</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex min-w-6 justify-center px-2 py-0.5 rounded-full text-xs font-semibold border border-white/20 bg-white/10 text-zinc-100">
                            {obj.artefactos_total ?? 0}
                          </span>
                          <Link
                            href={
                              obj.oportunidad_id
                                ? `/documentos?tab=ia&contexto_tipo=oportunidad&contexto_id=${obj.oportunidad_id}`
                                : obj.cuenta_id
                                  ? `/documentos?tab=ia&contexto_tipo=cuenta&contexto_id=${obj.cuenta_id}`
                                  : "/documentos?tab=ia"
                            }
                            className="px-2 py-1 rounded-md border border-white/20 text-xs text-zinc-100 hover:bg-white/10"
                          >
                            Ver IC
                          </Link>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={obj.estado}
                          onChange={(e) => actualizarEstado({ id: obj.id, nuevoEstado: e.target.value })}
                          className="h-8 rounded-lg border border-white/20 bg-black/20 px-2 text-xs text-white"
                        >
                          <option value="abierto">abierto</option>
                          <option value="en_progreso">en_progreso</option>
                          <option value="bloqueado">bloqueado</option>
                          <option value="completado">completado</option>
                          <option value="descartado">descartado</option>
                        </select>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          {obj.cuenta_id ? (
                            <>
                              <button
                                onClick={() => { void lanzarGeneracionObjetivo(obj, "pdf") }}
                                className="px-2 py-1 rounded-md border border-white/20 text-xs text-zinc-100 hover:bg-white/10"
                              >PDF</button>
                              <button
                                onClick={() => { void lanzarGeneracionObjetivo(obj, "pptx") }}
                                className="px-2 py-1 rounded-md border border-white/20 text-xs text-zinc-100 hover:bg-white/10"
                              >Deck</button>
                              <button
                                onClick={() => { void lanzarGeneracionObjetivo(obj, "briefing") }}
                                className="px-2 py-1 rounded-md border border-white/20 text-xs text-zinc-100 hover:bg-white/10"
                              >Audio</button>
                              <Link
                                href={`/cuentas/${obj.cuenta_id}`}
                                className="px-2 py-1 rounded-md border border-white/20 text-xs text-zinc-100 hover:bg-white/10"
                              >Cuenta</Link>
                              <button
                                onClick={() => setObjetivoDetalleId(obj.id)}
                                className="px-2 py-1 rounded-md border border-white/20 text-xs text-zinc-100 hover:bg-white/10"
                              >Detalle</button>
                            </>
                          ) : (
                            <span className="text-xs text-zinc-500">Sin cuenta asociada</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between px-4 py-3 border-t border-white/10 text-xs text-zinc-300">
            <span>Total: {data?.total ?? 0}</span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPagina((p) => Math.max(1, p - 1))}
                disabled={pagina <= 1}
                className="px-2 py-1 rounded-md border border-white/20 disabled:opacity-40"
              >Anterior</button>
              <span>Página {pagina} / {totalPaginas}</span>
              <button
                onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))}
                disabled={pagina >= totalPaginas}
                className="px-2 py-1 rounded-md border border-white/20 disabled:opacity-40"
              >Siguiente</button>
            </div>
          </div>
        </section>
      </main>

      {objetivoDetalleId && (
        <div
          style={{
            position: "fixed", inset: 0, zIndex: 120,
            display: "flex", alignItems: "center", justifyContent: "center",
            padding: "1rem",
          }}
        >
          <button
            style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.6)" }}
            onClick={() => setObjetivoDetalleId(null)}
            aria-label="Cerrar detalle"
          />
            <aside
              style={{
                position: "relative", zIndex: 10,
                width: "95vw", maxWidth: "1400px",
                maxHeight: "calc(100vh - 2rem)",
                display: "flex", flexDirection: "column",
                overflow: "hidden", borderRadius: "1.5rem",
              }}
              className="glass-panel glass-border p-4 md:p-5"
            >
              <div className="flex items-center justify-between gap-3 sticky top-0 z-10 pb-3 mb-1 bg-black/60 backdrop-blur-sm md:bg-transparent md:backdrop-blur-0">
                <h2 className="text-base md:text-lg font-semibold text-white">Detalle de objetivo</h2>
                <button
                  onClick={() => setObjetivoDetalleId(null)}
                  className="h-8 px-3 rounded-lg border border-white/20 text-xs text-zinc-100 hover:bg-white/10"
                >
                  Cerrar
                </button>
              </div>

              <div className="min-h-0 flex-1 overflow-auto pr-1">
                {cargandoDetalle || !detalleData ? (
                  <p className="text-sm text-zinc-300 mt-4">Cargando detalle...</p>
                ) : (
                  <div className="mt-4 flex flex-col gap-4">
                    {/* Columna 1: Consolidar */}
                    <div className="glass-panel rounded-2xl p-4 border border-white/10">
                      <p className="text-white font-semibold text-lg">{detalleData.objetivo.titulo}</p>
                      <p className="text-xs text-zinc-400 mt-1">
                        {detalleData.objetivo.tipo_objetivo} · prioridad {detalleData.objetivo.prioridad} · {detalleData.objetivo.estado}
                      </p>
                      {detalleData.objetivo.descripcion && (
                        <p className="text-sm text-zinc-200 mt-3 whitespace-pre-wrap leading-relaxed">
                          {detalleData.objetivo.descripcion}
                        </p>
                      )}
                      <div className="grid grid-cols-2 gap-2 mt-4 text-xs">
                        <p className="text-zinc-300"><span className="text-zinc-400">Impacto:</span> {formatearEuros(detalleData.objetivo.score_impacto || 0)}</p>
                        <p className="text-zinc-300"><span className="text-zinc-400">Confianza:</span> {Number(detalleData.objetivo.score_confianza || 0).toFixed(1)}%</p>
                        <p className="text-zinc-300"><span className="text-zinc-400">Cuenta:</span> {detalleData.objetivo.cuenta_nombre ?? "—"}</p>
                        <p className="text-zinc-300"><span className="text-zinc-400">Oportunidad:</span> {detalleData.objetivo.oportunidad_nombre ?? "—"}</p>
                      </div>
                    </div>

                    {/* Columna 2: Repositorio IC Contextual */}
                    <div className="glass-panel rounded-2xl p-4 border border-white/10">
                      <h3 className="text-sm font-semibold text-white">Repositorio IC contextual</h3>
                      <p className="text-xs text-zinc-400 mt-1 mb-3">
                        Selección y previsualización de artefactos para esta oportunidad/cuenta.
                      </p>
                      <ArtefactoPicker
                        contextoTipo={
                          detalleData.objetivo.oportunidad_id
                            ? "oportunidad"
                            : detalleData.objetivo.cuenta_id
                              ? "cuenta"
                              : undefined
                        }
                        contextoId={detalleData.objetivo.oportunidad_id ?? detalleData.objetivo.cuenta_id ?? undefined}
                      />
                    </div>

                    {/* Columna 3: Artefactos vinculados */}
                    <div className="glass-panel rounded-2xl p-4 border border-white/10">
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="text-sm font-semibold text-white">
                          Artefactos vinculados ({detalleData.artefactos.length})
                        </h3>
                        <Link
                          href={
                            detalleData.objetivo.oportunidad_id
                              ? `/documentos?tab=ia&contexto_tipo=oportunidad&contexto_id=${detalleData.objetivo.oportunidad_id}`
                              : detalleData.objetivo.cuenta_id
                                ? `/documentos?tab=ia&contexto_tipo=cuenta&contexto_id=${detalleData.objetivo.cuenta_id}`
                                : "/documentos?tab=ia"
                          }
                          className="px-2 py-1 rounded-md border border-white/20 text-xs text-zinc-100 hover:bg-white/10"
                        >
                          Abrir historial IC
                        </Link>
                      </div>
                      {detalleData.artefactos.length > 0 && (
                        <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
                          <select
                            value={artefactSortBy}
                            onChange={(e) => setArtefactSortBy(e.target.value as "fecha" | "tipo" | "titulo")}
                            className="text-xs border border-white/20 rounded-md px-2 py-1 bg-black/20 text-zinc-200"
                          >
                            <option value="fecha">Orden: fecha</option>
                            <option value="tipo">Orden: tipo</option>
                            <option value="titulo">Orden: título</option>
                          </select>
                          <select
                            value={artefactSortDir}
                            onChange={(e) => setArtefactSortDir((e.target.value as Orden) || "desc")}
                            className="text-xs border border-white/20 rounded-md px-2 py-1 bg-black/20 text-zinc-200"
                          >
                            <option value="desc">Descendente</option>
                            <option value="asc">Ascendente</option>
                          </select>
                        </div>
                      )}
                      {detalleData.artefactos.length === 0 ? (
                        <p className="text-xs text-zinc-400 mt-3">Aún no hay artefactos vinculados a este objetivo.</p>
                      ) : (
                        <div className="mt-3 grid gap-2">
                          {artefactosOrdenados.map((artefacto) => (
                            <div key={artefacto.id} className="rounded-xl border border-white/10 bg-black/20 px-3 py-3">
                              <p className="text-sm text-zinc-100">{artefacto.titulo || `Artefacto ${artefacto.tipo}`}</p>
                              <p className="text-xs text-zinc-400 mt-1">
                                {artefacto.tipo}{artefacto.subtipo ? ` · ${artefacto.subtipo}` : ""} · {artefacto.tipo_relacion}
                              </p>
                              <p className="text-[11px] text-zinc-500 mt-1">{new Date(artefacto.actualizado_en).toLocaleString("es-ES")}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </aside>
        </div>
      )}
    </>
  )
}
