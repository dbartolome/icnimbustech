"use client"

import { useEffect, useMemo, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Download, Eye, FileText, Search, Trash2 } from "lucide-react"

import { api } from "@/lib/api"
import { VistaPreviaArchivo, mimeDesdeSubtipo } from "@/components/ui/file-preview"
import { ModalVisorArtefacto } from "@/components/ui/modal-visor-artefacto"
import { BotonCompartirArtefacto } from "@/components/ui/boton-compartir-artefacto"
import { cn } from "@/lib/utils"
import type { ArtefactoRepositorioGrupo, ArtefactoRepositorioItem } from "@/types"

interface ArtefactoPickerProps {
  contextoTipo?: "cuenta" | "cliente" | "producto" | "oportunidad"
  contextoId?: string
  propietarioId?: string
  className?: string
  modoModal?: boolean
  onSeleccionar?: (artefacto: ArtefactoRepositorioItem) => void
}

const SUBTIPOS = [
  { value: "", label: "Todos" },
  { value: "investigacion", label: "Investigación" },
  { value: "propuesta", label: "Propuesta" },
  { value: "pdf", label: "PDF" },
  { value: "pptx", label: "Deck" },
  { value: "briefing", label: "Audio" },
  { value: "informe", label: "Informe" },
  { value: "chat", label: "Chat" },
]

type DetalleArtefacto = {
  artefacto?: {
    titulo?: string
    subtipo?: string
    origen_tabla?: string | null
    origen_id?: string | null
  }
  version_actual?: {
    resultado_texto?: string | null
    resultado_json?: Record<string, unknown> | null
    storage_key?: string | null
  }
} | null

function fechaCorta(valor: string) {
  const date = new Date(valor)
  if (Number.isNaN(date.getTime())) return valor
  return date.toLocaleDateString("es-ES")
}

export function ArtefactoPicker({ contextoTipo, contextoId, propietarioId, className, modoModal = false, onSeleccionar }: ArtefactoPickerProps) {
  const qc = useQueryClient()
  const [busqueda, setBusqueda] = useState("")
  const [subtipo, setSubtipo] = useState("")
  const [seleccionadoId, setSeleccionadoId] = useState<string | null>(null)
  const [artefactoModal, setArtefactoModal] = useState<ArtefactoRepositorioItem | null>(null)
  const [eliminandoId, setEliminandoId] = useState<string | null>(null)    // doc_id en confirm
  const [borrandoId, setBorrandoId] = useState<string | null>(null)        // en proceso

  const { data, isLoading } = useQuery({
    queryKey: ["artefactos-repositorio", contextoTipo ?? "all", contextoId ?? "all", propietarioId ?? "all", busqueda, subtipo],
    queryFn: () =>
      api.artefactos.repositorio({
        entidad_tipo: contextoTipo,
        entidad_id: contextoId,
        propietario_id: propietarioId,
        q: busqueda || undefined,
        subtipo: subtipo || undefined,
        por_pagina: 200,
      }),
    staleTime: 20_000,
  })

  const grupos = useMemo<ArtefactoRepositorioGrupo[]>(
    () => data?.datos ?? [],
    [data?.datos],
  )
  const items = useMemo(() => grupos.flatMap((g) => g.items), [grupos])

  useEffect(() => {
    if (!items.length) {
      setSeleccionadoId(null)
      return
    }
    if (!seleccionadoId || !items.some((item) => item.id === seleccionadoId)) {
      setSeleccionadoId(items[0].id)
      onSeleccionar?.(items[0])
    }
  }, [items, onSeleccionar, seleccionadoId])

  const seleccionado = useMemo(
    () => items.find((item) => item.id === seleccionadoId) ?? null,
    [items, seleccionadoId],
  )

  const detalleQuery = useQuery<DetalleArtefacto>({
    queryKey: ["artefacto-detalle", seleccionadoId],
    queryFn: async () => (await api.artefactos.detalle(String(seleccionadoId))) as DetalleArtefacto,
    enabled: Boolean(seleccionadoId),
    staleTime: 20_000,
  })

  const blobQuery = useQuery<Blob | null>({
    queryKey: ["artefacto-picker-blob", seleccionadoId],
    queryFn: async () => {
      try {
        return await api.artefactos.blob(String(seleccionadoId))
      } catch {
        return null
      }
    },
    enabled: Boolean(seleccionadoId),
    staleTime: 20_000,
  })

  async function descargarSeleccionado() {
    if (!seleccionado) return
    const detalle = detalleQuery.data
    const origenTabla = String(detalle?.artefacto?.origen_tabla ?? seleccionado.origen_tabla ?? "")
    const origenId = String(detalle?.artefacto?.origen_id ?? seleccionado.origen_id ?? "")

    if (origenTabla === "historial_documentos" && origenId) {
      const nombre = `${seleccionado.titulo || "artefacto"}.${seleccionado.subtipo || "txt"}`
      await api.historial.descargar(origenId, nombre)
      return
    }

    if (origenTabla === "informes_generados" && origenId) {
      await api.informes.descargar(origenId, seleccionado.titulo || "informe")
    }
  }

  async function abrirSeleccionado() {
    if (!seleccionado) return
    const detalle = detalleQuery.data
    const origenTabla = String(detalle?.artefacto?.origen_tabla ?? seleccionado.origen_tabla ?? "")
    const origenId = String(detalle?.artefacto?.origen_id ?? seleccionado.origen_id ?? "")

    if (origenTabla === "historial_documentos" && origenId) {
      try {
        await api.historial.abrir(origenId)
      } catch {
        const nombre = `${seleccionado.titulo || "artefacto"}.${seleccionado.subtipo || "txt"}`
        await api.historial.descargar(origenId, nombre)
      }
      return
    }
    if (origenTabla === "informes_generados" && origenId) {
      await api.informes.descargar(origenId, seleccionado.titulo || "informe")
    }
  }

  const resultadoTexto = String(
    detalleQuery.data?.version_actual?.resultado_texto ?? seleccionado?.preview_texto ?? "",
  )
  const resultadoJson = detalleQuery.data?.version_actual?.resultado_json

  const subtipoBajo = (seleccionado?.subtipo ?? "").toLowerCase()
  const esAudio = subtipoBajo === "briefing" || subtipoBajo === "audio"
  const esPptx = subtipoBajo === "pptx" || subtipoBajo === "deck"
  const origenTabla = String(detalleQuery.data?.artefacto?.origen_tabla ?? seleccionado?.origen_tabla ?? "")
  const origenId = String(detalleQuery.data?.artefacto?.origen_id ?? seleccionado?.origen_id ?? "")

  const transcripcionAudio = esAudio
    ? resultadoTexto || (typeof resultadoJson?.transcripcion === "string" ? resultadoJson.transcripcion : null)
    : null

  const slidesQuery = useQuery({
    queryKey: ["artefacto-picker-slides", seleccionadoId, origenId],
    queryFn: () => api.historial.slides(origenId),
    enabled: esPptx && origenTabla === "historial_documentos" && Boolean(origenId),
    staleTime: 60_000,
  })

  async function eliminarArtefacto(docId: string) {
    if (eliminandoId !== docId) { setEliminandoId(docId); return }
    setBorrandoId(docId)
    setEliminandoId(null)
    try {
      await api.historial.eliminar(docId)
      qc.invalidateQueries({ queryKey: ["artefactos-repositorio"] })
    } finally {
      setBorrandoId(null)
    }
  }

  return (
    <>
    <ModalVisorArtefacto artefacto={artefactoModal} onCerrar={() => setArtefactoModal(null)} />
    <div className={cn(modoModal ? "flex flex-col gap-3" : "grid grid-cols-1 lg:grid-cols-[1.05fr_1fr] gap-3", className)}>
      <section className="rounded-xl border border-white/10 bg-black/20 p-3">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <div className="relative flex-1 min-w-44">
            <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <input
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Buscar artefacto..."
              className="w-full pl-8 pr-2 py-2 text-sm border border-white/10 rounded-lg bg-white/5 text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
            />
          </div>
          <select
            value={subtipo}
            onChange={(e) => setSubtipo(e.target.value)}
            className="px-2 py-2 text-sm border border-white/10 rounded-lg bg-white/5 text-zinc-200"
          >
            {SUBTIPOS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <p className="text-sm text-zinc-500">Cargando repositorio IC...</p>
        ) : grupos.length === 0 ? (
          <p className="text-sm text-zinc-500">No hay artefactos para los filtros actuales.</p>
        ) : (
          <div className="space-y-3 max-h-[32rem] overflow-auto pr-1">
            {grupos.map((grupo) => (
              <div key={grupo.origen_key} className="rounded-lg border border-white/10 bg-white/5 p-2">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <p className="text-xs font-semibold text-zinc-300 truncate">{grupo.origen_nombre}</p>
                  <span className="text-[10px] text-zinc-500 whitespace-nowrap">{grupo.total} artefactos</span>
                </div>
                <div className="space-y-1.5">
                  {grupo.items.map((item) => {
                    const activo = !modoModal && item.id === seleccionadoId
                    const docId = item.origen_tabla === "historial_documentos" ? item.origen_id : null
                    const enConfirm = eliminandoId === docId
                    const enBorrando = borrandoId === docId

                    if (modoModal) {
                      return (
                        <div key={item.id} className="flex items-center gap-1 group rounded-lg border border-white/10 bg-black/20 hover:bg-white/5 transition-colors">
                          <button
                            onClick={() => setArtefactoModal(item)}
                            className="flex-1 text-left px-2.5 py-2 min-w-0"
                          >
                            <p className="text-xs font-medium text-zinc-200 truncate">{item.titulo}</p>
                            <p className="text-[11px] text-zinc-500 mt-0.5">
                              {item.subtipo} · {fechaCorta(item.actualizado_en)}
                            </p>
                          </button>
                          <div className="flex items-center gap-0.5 pr-1.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => setArtefactoModal(item)}
                              title="Previsualizar"
                              className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-white/10 transition-colors"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                            {docId && (
                              <>
                                <BotonCompartirArtefacto obtenerToken={() => api.historial.compartir(docId)} titulo={item.titulo} />
                                <button
                                  onClick={() => eliminarArtefacto(docId)}
                                  disabled={enBorrando}
                                  title={enConfirm ? "Confirmar eliminación" : "Eliminar"}
                                  className={cn(
                                    "p-1.5 rounded-lg transition-colors disabled:opacity-50",
                                    enConfirm
                                      ? "text-red-400 bg-red-500/20 hover:bg-red-500/30"
                                      : "text-zinc-400 hover:text-red-400 hover:bg-red-500/10",
                                  )}
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      )
                    }

                    return (
                      <button
                        key={item.id}
                        onClick={() => {
                          setSeleccionadoId(item.id)
                          onSeleccionar?.(item)
                        }}
                        className={cn(
                          "w-full text-left rounded-lg border px-2.5 py-2 transition-colors",
                          activo
                            ? "border-sgs-rojo bg-sgs-rojo/20"
                            : "border-white/10 bg-black/20 hover:bg-white/5",
                        )}
                      >
                        <p className="text-xs font-medium text-zinc-200 truncate">{item.titulo}</p>
                        <p className="text-[11px] text-zinc-500 mt-0.5">
                          {item.subtipo} · {fechaCorta(item.actualizado_en)}
                        </p>
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {!modoModal && (
        <section className="rounded-xl border border-white/10 bg-black/20 p-3">
          {!seleccionado ? (
            <div className="h-full min-h-48 flex items-center justify-center text-sm text-zinc-400">
              Selecciona un artefacto para ver su previsualización.
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-zinc-100">{seleccionado.titulo}</p>
                  <p className="text-xs text-zinc-400 mt-1">
                    {seleccionado.subtipo} · Actualizado {fechaCorta(seleccionado.actualizado_en)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={abrirSeleccionado}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg border border-white/20 text-zinc-200 hover:bg-white/10"
                  >
                    Abrir
                  </button>
                  <button
                    onClick={descargarSeleccionado}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg border border-white/20 text-zinc-200 hover:bg-white/10"
                  >
                    <Download className="h-3.5 w-3.5" /> Descargar
                  </button>
                </div>
              </div>

              {detalleQuery.isLoading ? (
                <p className="text-sm text-zinc-500">Cargando detalle…</p>
              ) : (
                <>
                  {blobQuery.isLoading ? (
                    <div className="rounded-lg border border-white/10 bg-black/20 p-4 text-sm text-zinc-400 text-center">
                      Cargando documento…
                    </div>
                  ) : blobQuery.data ? (
                    <VistaPreviaArchivo
                      blob={blobQuery.data}
                      mime={blobQuery.data.type || mimeDesdeSubtipo(seleccionado.subtipo)}
                      nombre={seleccionado.titulo || `artefacto.${seleccionado.subtipo}`}
                      transcripcion={transcripcionAudio}
                      slides={slidesQuery.data?.slides ?? undefined}
                      modo="amplia"
                    />
                  ) : (
                    <div className="rounded-lg border border-white/10 bg-black/20 p-3">
                      <p className="text-[11px] uppercase tracking-wide text-zinc-400 mb-2">Vista previa</p>
                      <p className="text-sm text-zinc-200 whitespace-pre-wrap leading-relaxed max-h-60 overflow-auto">
                        {resultadoTexto || "Sin previsualización disponible."}
                      </p>
                    </div>
                  )}
                </>
              )}

              <div className="inline-flex items-center gap-2 text-[11px] text-zinc-400">
                <FileText className="h-3.5 w-3.5" />
                Artefacto vinculado por origen: {seleccionado.entidad_tipo || "sin_origen"}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
    </>
  )
}
