"use client"

import { useEffect, useState } from "react"
import { createPortal } from "react-dom"
import { useQuery } from "@tanstack/react-query"
import { Download, X } from "lucide-react"

import { api } from "@/lib/api"
import { VistaPreviaArchivo, mimeDesdeSubtipo } from "@/components/ui/file-preview"
import { cn } from "@/lib/utils"
import type { ArtefactoRepositorioItem } from "@/types"

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

interface ModalVisorArtefactoProps {
  artefacto: ArtefactoRepositorioItem | null
  onCerrar: () => void
}

export function ModalVisorArtefacto({ artefacto, onCerrar }: ModalVisorArtefactoProps) {
  const abierto = Boolean(artefacto)
  const [montado, setMontado] = useState(false)

  useEffect(() => { setMontado(true) }, [])

  // Cerrar con Escape
  useEffect(() => {
    if (!abierto) return
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onCerrar() }
    document.addEventListener("keydown", handler)
    return () => document.removeEventListener("keydown", handler)
  }, [abierto, onCerrar])

  // Bloquear scroll del body
  useEffect(() => {
    if (abierto) {
      document.body.style.overflow = "hidden"
    } else {
      document.body.style.overflow = ""
    }
    return () => { document.body.style.overflow = "" }
  }, [abierto])

  const detalleQuery = useQuery<DetalleArtefacto>({
    queryKey: ["artefacto-detalle", artefacto?.id],
    queryFn: async () => (await api.artefactos.detalle(String(artefacto!.id))) as DetalleArtefacto,
    enabled: Boolean(artefacto),
    staleTime: 20_000,
  })

  const blobQuery = useQuery<Blob | null>({
    queryKey: ["artefacto-modal-blob", artefacto?.id],
    queryFn: async () => {
      try { return await api.artefactos.blob(String(artefacto!.id)) } catch { return null }
    },
    enabled: Boolean(artefacto),
    staleTime: 20_000,
  })

  const subtipoBajo = (artefacto?.subtipo ?? "").toLowerCase()
  const esPptx = subtipoBajo === "pptx" || subtipoBajo === "deck"
  const esAudio = subtipoBajo === "briefing" || subtipoBajo === "audio"

  const origenTabla = String(detalleQuery.data?.artefacto?.origen_tabla ?? artefacto?.origen_tabla ?? "")
  const origenId = String(detalleQuery.data?.artefacto?.origen_id ?? artefacto?.origen_id ?? "")

  const slidesQuery = useQuery({
    queryKey: ["artefacto-modal-slides", artefacto?.id, origenId],
    queryFn: () => api.historial.slides(origenId),
    enabled: esPptx && origenTabla === "historial_documentos" && Boolean(origenId),
    staleTime: 60_000,
  })

  const resultadoTexto = String(
    detalleQuery.data?.version_actual?.resultado_texto ?? artefacto?.preview_texto ?? "",
  )
  const resultadoJson = detalleQuery.data?.version_actual?.resultado_json
  const transcripcionAudio = esAudio
    ? resultadoTexto || (typeof resultadoJson?.transcripcion === "string" ? resultadoJson.transcripcion : null)
    : null

  async function descargar() {
    if (!artefacto) return
    if (origenTabla === "historial_documentos" && origenId) {
      const nombre = `${artefacto.titulo || "artefacto"}.${artefacto.subtipo || "txt"}`
      await api.historial.descargar(origenId, nombre)
      return
    }
    if (origenTabla === "informes_generados" && origenId) {
      await api.informes.descargar(origenId, artefacto.titulo || "informe")
    }
  }

  async function abrir() {
    if (!artefacto) return
    if (origenTabla === "historial_documentos" && origenId) {
      try {
        await api.historial.abrir(origenId)
      } catch {
        const nombre = `${artefacto.titulo || "artefacto"}.${artefacto.subtipo || "txt"}`
        await api.historial.descargar(origenId, nombre)
      }
      return
    }
    if (origenTabla === "informes_generados" && origenId) {
      await api.informes.descargar(origenId, artefacto.titulo || "informe")
    }
  }

  if (!abierto || !montado) return null

  return createPortal(
    /* backdrop: scrollable, cubre viewport completo, clic fuera cierra */
    <div className="fixed inset-0 z-[9999] overflow-y-auto bg-black/75 backdrop-blur-sm">
      <div
        className="flex min-h-full items-start justify-center p-4 md:p-8 md:items-center"
        onClick={onCerrar}
      >
        {/* modal box: crece con el contenido, clic no cierra */}
        <div
          className="relative w-full max-w-4xl my-4 rounded-2xl border border-white/10 bg-zinc-950 shadow-[0_32px_80px_rgba(0,0,0,0.7)]"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-4 px-5 py-4 border-b border-white/10">
            <div className="min-w-0">
              <p className="text-[10px] uppercase tracking-[0.28em] text-zinc-400">
                {artefacto!.subtipo} · {fechaCorta(artefacto!.actualizado_en)}
              </p>
              <p className="mt-1 text-sm font-semibold text-white truncate">{artefacto!.titulo}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={abrir}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-white/20 text-zinc-200 hover:bg-white/10 transition-colors"
              >
                Abrir
              </button>
              <button
                onClick={descargar}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-white/20 text-zinc-200 hover:bg-white/10 transition-colors"
              >
                <Download className="h-3.5 w-3.5" />
                Descargar
              </button>
              <button
                onClick={onCerrar}
                aria-label="Cerrar"
                className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="p-5">
            {detalleQuery.isLoading || blobQuery.isLoading ? (
              <div className="flex items-center justify-center h-48 text-sm text-zinc-400">
                Cargando…
              </div>
            ) : blobQuery.data ? (
              <VistaPreviaArchivo
                blob={blobQuery.data}
                mime={blobQuery.data.type || mimeDesdeSubtipo(artefacto!.subtipo)}
                nombre={artefacto!.titulo || `artefacto.${artefacto!.subtipo}`}
                transcripcion={transcripcionAudio}
                slides={slidesQuery.data?.slides ?? undefined}
                modo="amplia"
              />
            ) : (
              <div className="rounded-xl border border-white/10 bg-black/25 p-4">
                <p className="text-[11px] uppercase tracking-wide text-zinc-400 mb-2">Vista previa</p>
                <p className="text-sm text-zinc-200 whitespace-pre-wrap leading-relaxed">
                  {resultadoTexto || "Sin previsualización disponible."}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  )
}
