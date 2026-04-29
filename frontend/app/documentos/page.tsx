"use client"

export const dynamic = "force-dynamic"

import { Suspense, useEffect, useMemo, useState, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import { Topbar } from "@/components/layout/topbar"
import { ArtefactoPicker } from "@/components/ui/artefacto-picker"
import { VistaPreviaArchivo, mimeDesdeSubtipo } from "@/components/ui/file-preview"
import type { DocumentoRead, DocumentoHistorial } from "@/types"
import { FileText, Presentation, Mic, Search, Brain, Download, Trash2, Upload, ChevronRight } from "lucide-react"
import { BotonCompartirArtefacto } from "@/components/ui/boton-compartir-artefacto"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { useAppStore } from "@/store/use-app-store"

// =============================================================================
// Helpers
// =============================================================================

const ICONOS_MIME: Record<string, string> = {
  "application/pdf": "📄",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "📝",
  "application/msword": "📝",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "📊",
  "application/vnd.ms-excel": "📊",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": "📑",
  "text/plain": "📃",
  "text/csv": "📊",
  "image/png": "🖼️",
  "image/jpeg": "🖼️",
  "application/zip": "🗜️",
  "audio/mpeg": "🎙️",
  "audio/mp3": "🎙️",
  "audio/wav": "🎙️",
  "audio/x-wav": "🎙️",
  "audio/m4a": "🎙️",
  "audio/ogg": "🎙️",
  "audio/webm": "🎙️",
}

function esAudioMime(mime: string | null, nombre: string): boolean {
  if ((mime ?? "").startsWith("audio/")) return true
  return /\.(mp3|wav|m4a|ogg|webm)$/i.test(nombre)
}

function iconoMime(mime: string | null) {
  if (!mime) return "📎"
  return ICONOS_MIME[mime] ?? "📎"
}

function formatBytes(bytes: number | null) {
  if (!bytes) return "—"
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function exportarCsvAnalisis(nombre: string, filas: DocumentoHistorial[]) {
  const cabeceras = [
    "id",
    "tipo",
    "contexto_tipo",
    "contexto_id",
    "cuenta_nombre",
    "nombre_fichero",
    "tamano_bytes",
    "usuario_nombre",
    "creado_en",
  ]

  const escapar = (valor: string | number | null | undefined) => {
    const texto = String(valor ?? "")
    return `"${texto.replace(/"/g, '""')}"`
  }

  const lineas = [
    cabeceras.join(","),
    ...filas.map((f) =>
      [
        escapar(f.id),
        escapar(f.tipo),
        escapar(f.contexto_tipo ?? ""),
        escapar(f.contexto_id ?? ""),
        escapar(f.cuenta_nombre ?? ""),
        escapar(f.nombre_fichero),
        escapar(f.tamano_bytes ?? ""),
        escapar(f.usuario_nombre),
        escapar(f.creado_en),
      ].join(","),
    ),
  ]

  const blob = new Blob([lineas.join("\n")], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = nombre
  a.click()
  URL.revokeObjectURL(url)
}

const EXTENSIONES_ACEPTADAS =
  ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.png,.jpg,.jpeg,.gif,.zip,.mp3,.wav,.m4a,.ogg,.webm"

// =============================================================================
// Config de tipos de análisis IC
// =============================================================================

const TIPO_CONFIG: Record<string, { label: string; color: string; Icon: React.ComponentType<{ className?: string }> }> = {
  investigacion: { label: "Investigación", color: "bg-blue-50 text-blue-700 border-blue-100", Icon: Search },
  propuesta: { label: "Propuesta", color: "bg-purple-50 text-purple-700 border-purple-100", Icon: Brain },
  pdf: { label: "PDF", color: "bg-red-50 text-red-700 border-red-100", Icon: FileText },
  pptx: { label: "Deck", color: "bg-orange-50 text-orange-700 border-orange-100", Icon: Presentation },
  briefing: { label: "Briefing audio", color: "bg-green-50 text-green-700 border-green-100", Icon: Mic },
}

// =============================================================================
// Zona de subida (drag & drop)
// =============================================================================

function ZonaSubida({ onSubido }: { onSubido: () => void }) {
  const [arrastrando, setArrastrando] = useState(false)
  const [subiendo, setSubiendo] = useState(false)
  const [progreso, setProgreso] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [archivoSeleccionado, setArchivoSeleccionado] = useState<File | null>(null)
  const [cuentaId, setCuentaId] = useState<string>("")
  const inputRef = useRef<HTMLInputElement>(null)

  const esAudio = archivoSeleccionado ? esAudioMime(archivoSeleccionado.type, archivoSeleccionado.name) : false

  const { data: catalogoCuentas = [] } = useQuery({
    queryKey: ["cuentas-catalogo"],
    queryFn: () => api.cuentas.catalogo(),
    staleTime: 60_000,
    enabled: esAudio,
  })

  async function subirArchivo(archivo: File) {
    setSubiendo(true)
    setError(null)
    setProgreso(`Subiendo ${archivo.name}…`)
    try {
      const doc = await api.documentos.subir(archivo, undefined, cuentaId || undefined)
      if (esAudioMime(archivo.type, archivo.name) && doc?.id) {
        setProgreso("Transcribiendo audio… (la primera vez puede tardar 1-2 min mientras se carga el modelo)")
        try {
          await api.documentos.transcribir(doc.id)
        } catch (e) {
          setError(`Audio subido correctamente, pero la transcripción falló: ${e instanceof Error ? e.message : "Error desconocido"}`)
        }
      }
      setProgreso(null)
      setArchivoSeleccionado(null)
      setCuentaId("")
      onSubido()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al subir el archivo.")
      setProgreso(null)
    } finally {
      setSubiendo(false)
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setArrastrando(false)
    const archivo = e.dataTransfer.files[0]
    if (archivo) setArchivoSeleccionado(archivo)
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const archivo = e.target.files?.[0]
    if (archivo) setArchivoSeleccionado(archivo)
    if (inputRef.current) inputRef.current.value = ""
  }

  function cancelar() {
    setArchivoSeleccionado(null)
    setCuentaId("")
    setError(null)
  }

  return (
    <div className="bg-white rounded-xl border border-zinc-200 p-5">
      <h2 className="text-sm font-semibold text-zinc-800 mb-4">Subir documento</h2>

      {!archivoSeleccionado ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setArrastrando(true) }}
          onDragLeave={() => setArrastrando(false)}
          onDrop={onDrop}
          onClick={() => !subiendo && inputRef.current?.click()}
          className={cn(
            "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors",
            arrastrando
              ? "border-sgs-rojo bg-red-50"
              : "border-zinc-200 hover:border-zinc-400 hover:bg-zinc-50",
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept={EXTENSIONES_ACEPTADAS}
            className="hidden"
            onChange={onInputChange}
          />
          <div className="flex flex-col items-center gap-2">
            <Upload className="h-8 w-8 text-zinc-300" />
            <p className="text-sm font-medium text-zinc-700">
              Arrastra un archivo o haz clic para seleccionar
            </p>
            <p className="text-xs text-zinc-400">
              PDF, Word, Excel, PowerPoint, imágenes, ZIP, audio · Máx. 10 MB
            </p>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{iconoMime(archivoSeleccionado.type)}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-zinc-900 truncate">{archivoSeleccionado.name}</p>
              <p className="text-xs text-zinc-400">{formatBytes(archivoSeleccionado.size)}</p>
            </div>
          </div>

          {esAudio && (
            <div>
              <label className="block text-xs font-medium text-zinc-600 mb-1">
                Vincular a cuenta <span className="text-zinc-400">(opcional — para usar en informes y briefings)</span>
              </label>
              <select
                value={cuentaId}
                onChange={(e) => setCuentaId(e.target.value)}
                className="w-full text-sm border border-zinc-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
              >
                <option value="">Sin vincular</option>
                {catalogoCuentas.map((c) => (
                  <option key={c.id} value={c.id}>{c.nombre}</option>
                ))}
              </select>
              {cuentaId && (
                <p className="mt-1.5 text-[11px] text-violet-600">
                  La transcripción quedará disponible como contexto al generar informes, briefings y presentaciones para esta cuenta.
                </p>
              )}
            </div>
          )}

          {subiendo ? (
            <div className="flex items-center gap-3 pt-1">
              <div className="h-5 w-5 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin shrink-0" />
              <p className="text-sm text-zinc-500">{progreso}</p>
            </div>
          ) : (
            <div className="flex gap-2 pt-1">
              <button
                onClick={() => subirArchivo(archivoSeleccionado)}
                className="flex-1 py-2 text-sm font-medium bg-sgs-rojo text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Subir{esAudio ? " y transcribir" : ""}
              </button>
              <button
                onClick={cancelar}
                className="px-4 py-2 text-sm font-medium border border-zinc-200 text-zinc-600 rounded-lg hover:bg-zinc-100 transition-colors"
              >
                Cancelar
              </button>
            </div>
          )}
        </div>
      )}

      {error && (
        <p className="mt-3 text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
      )}
    </div>
  )
}

// =============================================================================
// Fila de documento manual
// =============================================================================

function FilaDocumento({
  doc,
  onEliminar,
  onAbrir,
  onTranscripcionActualizada,
}: {
  doc: DocumentoRead
  onEliminar: (id: string) => void
  onAbrir: (doc: DocumentoRead) => void
  onTranscripcionActualizada?: () => void
}) {
  const [descargando, setDescargando] = useState(false)
  const [errorDescarga, setErrorDescarga] = useState<string | null>(null)
  const [transcribiendo, setTranscribiendo] = useState(false)
  const [errorTranscripcion, setErrorTranscripcion] = useState<string | null>(null)
  const esAudio = esAudioMime(doc.tipo_mime, doc.nombre_original)

  async function descargar() {
    setDescargando(true)
    setErrorDescarga(null)
    try {
      await api.documentos.descargar(doc.id, doc.nombre_original)
    } catch (e) {
      setErrorDescarga(e instanceof Error ? e.message : "Error al descargar")
    } finally {
      setDescargando(false)
    }
  }

  async function transcribir() {
    setTranscribiendo(true)
    setErrorTranscripcion(null)
    try {
      await api.documentos.transcribir(doc.id)
      onTranscripcionActualizada?.()
    } catch (e) {
      setErrorTranscripcion(e instanceof Error ? e.message : "No se pudo transcribir el audio.")
    } finally {
      setTranscribiendo(false)
    }
  }

  return (
    <div
      className="bg-white rounded-xl border border-zinc-200 px-4 py-3 hover:border-zinc-300 transition-colors cursor-pointer"
      onClick={() => onAbrir(doc)}
    >
      <div className="flex items-center gap-4">
        <span className="text-2xl shrink-0">{iconoMime(doc.tipo_mime)}</span>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-zinc-900 truncate">{doc.nombre_original}</p>
          <div className="flex items-center gap-3 mt-0.5 flex-wrap">
            <span className="text-xs text-zinc-400">{formatBytes(doc.tamaño_bytes)}</span>
            <span className="text-xs text-zinc-400">{doc.creado_en.slice(0, 10)}</span>
            {doc.oportunidad_nombre && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-700">
                {doc.oportunidad_nombre.slice(0, 35)}{doc.oportunidad_nombre.length > 35 ? "…" : ""}
              </span>
            )}
            {doc.cuenta_nombre && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-amber-50 text-amber-700">
                {doc.cuenta_nombre.slice(0, 30)}{doc.cuenta_nombre.length > 30 ? "…" : ""}
              </span>
            )}
            {esAudio && doc.tiene_transcripcion && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-violet-50 text-violet-700">
                Transcrito
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={(e) => {
              e.stopPropagation()
              descargar()
            }}
            disabled={descargando}
            className="px-3 py-1.5 text-xs font-medium border border-zinc-200 text-zinc-700 rounded-lg hover:bg-zinc-50 disabled:opacity-50 transition-colors"
          >
            {descargando ? "…" : "↓ Descargar"}
          </button>
          {esAudio && !doc.tiene_transcripcion && (
            <button
              onClick={(e) => { e.stopPropagation(); transcribir() }}
              disabled={transcribiendo}
              className="px-3 py-1.5 text-xs font-medium border border-violet-200 text-violet-700 rounded-lg hover:bg-violet-50 disabled:opacity-50 transition-colors"
              title="Generar transcripción"
            >
              {transcribiendo ? "Transcribiendo…" : "Transcribir"}
            </button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation()
              onAbrir(doc)
            }}
            className="px-3 py-1.5 text-xs font-medium border border-zinc-200 text-zinc-700 rounded-lg hover:bg-zinc-50 transition-colors"
          >
            Ver
          </button>
          <div onClick={(e) => e.stopPropagation()} className="[&_button]:!text-zinc-400 [&_button]:hover:!text-zinc-700 [&_button]:hover:!bg-zinc-100">
            <BotonCompartirArtefacto
              obtenerToken={() => api.documentos.compartir(doc.id)}
              titulo={doc.nombre_original}
            />
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onEliminar(doc.id)
            }}
            className="text-zinc-300 hover:text-red-500 transition-colors"
            title="Eliminar"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
      {errorDescarga && (
        <p className="mt-2 text-xs text-red-600 bg-red-50 px-3 py-1.5 rounded-lg">{errorDescarga}</p>
      )}
      {errorTranscripcion && (
        <p className="mt-2 text-xs text-red-600 bg-red-50 px-3 py-1.5 rounded-lg">{errorTranscripcion}</p>
      )}
    </div>
  )
}

function ModalDetalleDocumento({
  doc,
  onClose,
  onEliminar,
}: {
  doc: DocumentoRead
  onClose: () => void
  onEliminar: (id: string) => void
}) {
  const esPptx =
    (doc.tipo_mime ?? "").toLowerCase().includes("presentation") ||
    /\.(pptx?)$/i.test(doc.nombre_original)
  const esAudioDoc = esAudioMime(doc.tipo_mime, doc.nombre_original)

  const { data: blob, isLoading } = useQuery({
    queryKey: ["documento-preview", doc.id],
    queryFn: () => api.documentos.blob(doc.id),
    enabled: Boolean(doc.id),
    retry: false,
  })

  const { data: slidesData } = useQuery({
    queryKey: ["documento-slides", doc.id],
    queryFn: () => api.documentos.slides(doc.id),
    enabled: esPptx && Boolean(doc.id),
    retry: false,
  })

  const { data: transcripcionData } = useQuery({
    queryKey: ["documento-transcripcion", doc.id],
    queryFn: () => api.documentos.transcripcion(doc.id),
    enabled: esAudioDoc && doc.tiene_transcripcion,
    retry: false,
  })

  async function abrir() {
    try {
      await api.documentos.abrir(doc.id)
    } catch {
      await api.documentos.descargar(doc.id, doc.nombre_original)
    }
  }

  async function descargar() {
    await api.documentos.descargar(doc.id, doc.nombre_original)
  }

  async function eliminar() {
    onEliminar(doc.id)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-[140]">
      <button className="absolute inset-0 bg-black/50" onClick={onClose} aria-label="Cerrar detalle" />
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[95vw] max-w-7xl max-h-[calc(100vh-2rem)] flex flex-col overflow-hidden rounded-3xl border border-white/10 bg-zinc-950/95 shadow-[0_30px_90px_rgba(0,0,0,0.6)] backdrop-blur-xl">
          <div className="shrink-0 flex flex-col gap-3 border-b border-white/10 px-4 py-4 md:px-6 md:py-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <h3 className="text-base font-semibold text-white md:text-lg">{doc.nombre_original}</h3>
              <p className="mt-1 text-xs text-zinc-400">
                {doc.tipo_mime ?? "archivo"} · {formatBytes(doc.tamaño_bytes)} · {doc.creado_en.slice(0, 10)}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button onClick={abrir} className="px-3 py-1.5 text-xs font-medium border border-white/20 text-zinc-200 rounded-lg hover:bg-white/10">
                Abrir
              </button>
              <button onClick={descargar} className="px-3 py-1.5 text-xs font-medium border border-white/20 text-zinc-200 rounded-lg hover:bg-white/10">
                Descargar
              </button>
              <button onClick={eliminar} className="px-3 py-1.5 text-xs font-medium border border-red-500/40 text-red-400 rounded-lg hover:bg-red-500/10">
                Eliminar
              </button>
              <button onClick={onClose} className="px-3 py-1.5 text-xs font-medium border border-white/20 text-zinc-200 rounded-lg hover:bg-white/10">
                Cerrar
              </button>
            </div>
          </div>

          <div className="grid min-h-0 flex-1 gap-4 overflow-hidden p-4 md:p-5 lg:grid-cols-[minmax(0,1.7fr)_minmax(18rem,0.7fr)]">
            <div className="min-h-0 overflow-auto rounded-2xl bg-zinc-950/90 p-3 md:p-4">
              {isLoading ? (
                <div className="flex h-[72vh] items-center justify-center">
                  <div className="h-7 w-7 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
                </div>
              ) : !blob ? (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
                  No se ha podido cargar la previsualización de este archivo. Puede que el fichero ya no exista en el repositorio.
                </div>
              ) : (
                <VistaPreviaArchivo
                  blob={blob}
                  mime={doc.tipo_mime}
                  nombre={doc.nombre_original}
                  slides={slidesData?.slides ?? undefined}
                  modo="amplia"
                />
              )}
            </div>

            <aside className="min-h-0 overflow-auto rounded-2xl border border-white/10 bg-white/5 p-4 md:p-5">
              <p className="text-[10px] uppercase tracking-[0.3em] text-zinc-400">Detalles</p>
              <div className="mt-3 space-y-3 text-sm">
                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <p className="text-xs font-semibold text-zinc-400">Nombre</p>
                  <p className="mt-1 break-words text-zinc-100">{doc.nombre_original}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <p className="text-xs font-semibold text-zinc-400">Tipo</p>
                  <p className="mt-1 text-zinc-100">{doc.tipo_mime ?? "archivo"}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <p className="text-xs font-semibold text-zinc-400">Peso</p>
                  <p className="mt-1 text-zinc-100">{formatBytes(doc.tamaño_bytes)}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <p className="text-xs font-semibold text-zinc-400">Creado</p>
                  <p className="mt-1 text-zinc-100">{doc.creado_en.slice(0, 10)}</p>
                </div>
                {doc.oportunidad_nombre ? (
                  <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                    <p className="text-xs font-semibold text-zinc-400">Oportunidad</p>
                    <p className="mt-1 text-zinc-100">{doc.oportunidad_nombre}</p>
                  </div>
                ) : null}
                {doc.cuenta_nombre ? (
                  <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                    <p className="text-xs font-semibold text-zinc-400">Cuenta vinculada</p>
                    <p className="mt-1 text-zinc-100">{doc.cuenta_nombre}</p>
                    <p className="mt-1 text-[10px] text-zinc-500">La transcripción está disponible como contexto para informes y briefings de esta cuenta.</p>
                  </div>
                ) : null}
                {esAudioDoc && transcripcionData?.transcripcion ? (
                  <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                    <p className="text-xs font-semibold text-zinc-400 mb-2">Transcripción</p>
                    <p className="text-xs leading-relaxed text-zinc-200 whitespace-pre-wrap max-h-64 overflow-y-auto">
                      {transcripcionData.transcripcion}
                    </p>
                  </div>
                ) : null}
              </div>
            </aside>
          </div>
        </div>
    </div>
  )
}

// =============================================================================
// Fila de análisis IC
// =============================================================================

function FilaAnalisis({
  doc,
  onEliminar,
  onAbrir,
}: {
  doc: DocumentoHistorial
  onEliminar: (id: string) => void
  onAbrir: (id: string) => void
}) {
  const [descargando, setDescargando] = useState(false)
  const [eliminando, setEliminando] = useState(false)
  const config = TIPO_CONFIG[doc.tipo] ?? TIPO_CONFIG.pdf
  const Icon = config.Icon
  const metadatos = (doc.metadatos ?? {}) as Record<string, unknown>
  const origenTabla = String(metadatos.origen_tabla ?? "")
  const origenId = String(metadatos.origen_id ?? "")

  async function descargar() {
    setDescargando(true)
    try {
      if (origenTabla === "historial_documentos" && origenId) {
        await api.historial.descargar(origenId, doc.nombre_fichero)
        return
      }
      if (origenTabla === "informes_generados" && origenId) {
        await api.informes.descargar(origenId, doc.nombre_fichero.replace(/\.pdf$/i, ""))
        return
      }
    } finally {
      setDescargando(false)
    }
  }

  async function eliminar() {
    setEliminando(true)
    try {
      await api.artefactos.eliminar(doc.id)
      onEliminar(doc.id)
    } finally {
      setEliminando(false)
    }
  }

  return (
    <div
      className="flex items-center gap-4 bg-white rounded-xl border border-zinc-200 px-4 py-3 hover:border-zinc-300 transition-colors cursor-pointer"
      onClick={() => onAbrir(doc.id)}
    >
      {/* Icono tipo */}
      <div className={cn("p-2 rounded-lg border", config.color)}>
        <Icon className="h-4 w-4" />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-zinc-900 truncate">{doc.cuenta_nombre}</p>
          <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded-full border", config.color)}>
            {config.label}
          </span>
          {doc.contexto_tipo && (
            <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full border border-zinc-200 text-zinc-600 bg-zinc-50">
              {doc.contexto_tipo}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-0.5 flex-wrap">
          <span className="text-xs text-zinc-400 truncate max-w-[200px]">{doc.nombre_fichero}</span>
          <span className="text-xs text-zinc-400">{formatBytes(doc.tamano_bytes)}</span>
          <span className="text-xs text-zinc-400">{doc.creado_en.slice(0, 10)}</span>
          <span className="text-xs text-zinc-400">por {doc.usuario_nombre}</span>
        </div>
      </div>

      {/* Acciones */}
      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={(e) => {
            e.stopPropagation()
            descargar()
          }}
          disabled={descargando}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-zinc-200 text-zinc-700 rounded-lg hover:bg-zinc-50 disabled:opacity-50 transition-colors"
        >
          <Download className="h-3.5 w-3.5" />
          {descargando ? "…" : "Descargar"}
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onAbrir(doc.id)
          }}
          className="px-3 py-1.5 text-xs font-medium border border-zinc-200 text-zinc-700 rounded-lg hover:bg-zinc-50 transition-colors"
        >
          Ver
        </button>
        {origenTabla === "historial_documentos" && origenId && (
          <div onClick={(e) => e.stopPropagation()} className="[&_button]:!text-zinc-400 [&_button]:hover:!text-zinc-700 [&_button]:hover:!bg-zinc-100">
            <BotonCompartirArtefacto
              obtenerToken={() => api.historial.compartir(origenId)}
              titulo={doc.nombre_fichero}
            />
          </div>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation()
            eliminar()
          }}
          disabled={eliminando}
          className="text-zinc-300 hover:text-red-500 transition-colors disabled:opacity-40"
          title="Eliminar"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}

function ModalDetalleArtefacto({
  artefactoId,
  onClose,
}: {
  artefactoId: string
  onClose: () => void
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["artefacto-detalle-modal", artefactoId],
    queryFn: () => api.artefactos.detalle(artefactoId) as Promise<Record<string, unknown>>,
    enabled: Boolean(artefactoId),
  })

  const artefacto = (data?.artefacto as Record<string, unknown> | undefined) ?? {}
  const version = (data?.version_actual as Record<string, unknown> | undefined) ?? {}
  const origenTabla = String(artefacto.origen_tabla ?? "")
  const origenId = String(artefacto.origen_id ?? "")
  const subtipo = String(artefacto.subtipo ?? artefacto.tipo ?? "artefacto")
  const resultadoTexto = String(version.resultado_texto ?? "")
  const resultadoJson = (version.resultado_json as Record<string, unknown> | undefined) ?? null
  const esAudio = ["audio", "briefing"].includes(subtipo.toLowerCase())
  const transcripcionAudio = esAudio
    ? resultadoTexto || (typeof resultadoJson?.transcripcion === "string" ? resultadoJson.transcripcion : null)
    : null

  const { data: blobVista, isLoading: isLoadingBlob } = useQuery<Blob | null>({
    queryKey: ["artefacto-blob-modal", artefactoId],
    queryFn: async () => {
      try {
        return await api.artefactos.blob(artefactoId)
      } catch {
        return null
      }
    },
    enabled: Boolean(artefactoId),
  })

  const { data: slidesPptx } = useQuery({
    queryKey: ["artefacto-slides-modal", artefactoId, origenId],
    queryFn: () => api.historial.slides(origenId),
    enabled: origenTabla === "historial_documentos" && Boolean(origenId) && subtipo.toLowerCase() === "pptx",
  })

  async function descargar() {
    const titulo = String(artefacto.titulo ?? "artefacto")

    if (origenTabla === "historial_documentos" && origenId) {
      await api.historial.descargar(origenId, titulo)
      return
    }
    if (origenTabla === "informes_generados" && origenId) {
      await api.informes.descargar(origenId, titulo)
    }
  }

  async function abrir() {
    if (origenTabla === "historial_documentos" && origenId) {
      try {
        await api.historial.abrir(origenId)
      } catch {
        await api.historial.descargar(origenId, String(artefacto.titulo ?? "artefacto"))
      }
      return
    }
    await descargar()
  }

  return (
    <div className="fixed inset-0 z-[140]">
      <button className="absolute inset-0 bg-black/50" onClick={onClose} aria-label="Cerrar detalle" />
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[95vw] max-w-7xl max-h-[calc(100vh-2rem)] flex flex-col overflow-hidden rounded-3xl border border-white/10 bg-zinc-950/95 shadow-[0_30px_90px_rgba(0,0,0,0.6)] backdrop-blur-xl">
          <div className="shrink-0 flex flex-col gap-3 border-b border-zinc-200 px-4 py-4 md:px-6 md:py-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <h3 className="text-base font-semibold text-zinc-900 md:text-lg">{String(artefacto.titulo ?? "Detalle de artefacto")}</h3>
              <p className="mt-1 text-xs text-zinc-500">
                {String(artefacto.subtipo ?? artefacto.tipo ?? "artefacto")} · v{String(artefacto.version_actual ?? "1")}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={abrir}
                className="px-3 py-1.5 text-xs font-medium border border-zinc-200 text-zinc-700 rounded-lg hover:bg-zinc-50"
              >
                Abrir
              </button>
              <button
                onClick={descargar}
                className="px-3 py-1.5 text-xs font-medium border border-zinc-200 text-zinc-700 rounded-lg hover:bg-zinc-50"
              >
                Descargar
              </button>
              <button onClick={onClose} className="px-3 py-1.5 text-xs font-medium border border-zinc-200 rounded-lg hover:bg-zinc-50">
                Cerrar
              </button>
            </div>
          </div>

          {isLoading ? (
            <div className="flex min-h-[64vh] items-center justify-center">
              <p className="text-sm text-zinc-500">Cargando detalle...</p>
            </div>
          ) : (
            <div className="grid min-h-0 flex-1 gap-4 overflow-hidden p-4 md:p-5 lg:grid-cols-[minmax(0,1.7fr)_minmax(19rem,0.75fr)]">
              <div className="min-h-0 overflow-auto rounded-2xl bg-zinc-50 p-3 md:p-4">
                {blobVista ? (
                  <VistaPreviaArchivo
                    blob={blobVista}
                    mime={blobVista.type || mimeDesdeSubtipo(subtipo)}
                    nombre={String(artefacto.titulo ?? `artefacto.${subtipo}`)}
                    transcripcion={transcripcionAudio}
                    slides={slidesPptx?.slides ?? undefined}
                    modo="amplia"
                  />
                ) : isLoadingBlob ? (
                  <div className="flex min-h-[68vh] items-center justify-center rounded-2xl border border-zinc-200 bg-white">
                    <div className="h-7 w-7 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
                  </div>
                ) : (
                  <div className="rounded-2xl border border-zinc-200 bg-white p-4 text-sm text-zinc-500">
                    No se ha podido cargar el binario de este artefacto.
                  </div>
                )}
              </div>

              <aside className="min-h-0 overflow-auto rounded-2xl border border-zinc-200 bg-white p-4 md:p-5">
                <p className="text-[10px] uppercase tracking-[0.3em] text-zinc-500">Contexto</p>
                <div className="mt-3 space-y-3 text-sm">
                  <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3">
                    <p className="text-xs font-semibold text-zinc-500">Texto generado</p>
                    <p className="mt-1 max-h-56 overflow-auto whitespace-pre-wrap text-zinc-800">
                      {resultadoTexto || "Sin texto de previsualización disponible."}
                    </p>
                  </div>

                  {transcripcionAudio ? (
                    <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3">
                      <p className="text-xs font-semibold text-zinc-500">Transcripción audio</p>
                      <p className="mt-1 max-h-56 overflow-auto whitespace-pre-wrap text-zinc-800">
                        {transcripcionAudio}
                      </p>
                    </div>
                  ) : null}

                  {slidesPptx?.slides?.length ? (
                    <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3">
                      <p className="text-xs font-semibold text-zinc-500">Diapositivas extraídas</p>
                      <div className="mt-2 max-h-72 space-y-2 overflow-auto">
                        {slidesPptx.slides.map((slide) => (
                          <div key={slide.index} className="rounded-lg border border-zinc-200 bg-white p-3">
                            <p className="text-xs font-semibold text-zinc-700">
                              Slide {slide.index}: {slide.titulo || "Sin título"}
                            </p>
                            <p className="mt-1 whitespace-pre-wrap text-xs text-zinc-600">
                              {slide.cuerpo || "Sin cuerpo textual"}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {resultadoJson && Object.keys(resultadoJson).length > 0 ? (
                    <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3">
                      <p className="text-xs font-semibold text-zinc-500">Datos estructurados</p>
                      <pre className="mt-1 max-h-72 overflow-auto whitespace-pre-wrap break-words text-xs text-zinc-700">
                        {JSON.stringify(resultadoJson, null, 2)}
                      </pre>
                    </div>
                  ) : null}
                </div>
              </aside>
            </div>
          )}
        </div>
    </div>
  )
}

// =============================================================================
// Tab: Mis documentos (subidos manualmente)
// =============================================================================

function TabMisDocumentos({ puedeFiltrarComercial, propietarioId }: { puedeFiltrarComercial: boolean; propietarioId?: string }) {
  const [busqueda, setBusqueda] = useState("")
  const [pagina, setPagina] = useState(1)
  const [docAbierto, setDocAbierto] = useState<DocumentoRead | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery<{
    total: number
    pagina: number
    por_pagina: number
    datos: DocumentoRead[]
  }>({
    queryKey: ["documentos", busqueda, pagina, propietarioId ?? "self"],
    queryFn: () =>
      api.documentos.listar({ busqueda: busqueda || undefined, pagina, propietario_id: propietarioId }) as Promise<{
        total: number; pagina: number; por_pagina: number; datos: DocumentoRead[]
      }>,
  })

  const mutEliminar = useMutation({
    mutationFn: (id: string) => api.documentos.eliminar(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documentos"] }),
  })

  const totalPaginas = data ? Math.ceil(data.total / data.por_pagina) : 1
  // Siempre usar el doc fresco del listado para que tiene_transcripcion se actualice sin reabrir
  const docModal = docAbierto ? (data?.datos.find((d) => d.id === docAbierto.id) ?? docAbierto) : null

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
          <input
            type="text"
            placeholder="Buscar documento..."
            value={busqueda}
            onChange={(e) => { setBusqueda(e.target.value); setPagina(1) }}
            className="w-full pl-9 pr-3 py-2 text-sm border border-zinc-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
          />
        </div>
          <p className="text-xs text-zinc-400 shrink-0">
            {data ? `${data.total} archivos` : ""}
          </p>
          {puedeFiltrarComercial && (
            <p className="text-[11px] text-zinc-500 shrink-0">Filtrado por comercial</p>
          )}
      </div>

      <ZonaSubida onSubido={() => { queryClient.invalidateQueries({ queryKey: ["documentos"] }); setPagina(1) }} />

      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <div className="h-7 w-7 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
        </div>
      ) : !data?.datos.length ? (
        <div className="flex flex-col items-center justify-center h-32 gap-2">
          <Upload className="h-8 w-8 text-zinc-300" />
          <p className="text-sm text-zinc-500">
            {busqueda ? "Sin resultados." : "Aún no tienes documentos subidos."}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {data.datos.map((doc) => (
            <FilaDocumento key={doc.id} doc={doc} onEliminar={(id) => mutEliminar.mutate(id)} onAbrir={setDocAbierto} onTranscripcionActualizada={() => queryClient.invalidateQueries({ queryKey: ["documentos"] })} />
          ))}
        </div>
      )}

      {data && totalPaginas > 1 && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-xs text-zinc-500">Página {pagina} de {totalPaginas}</p>
          <div className="flex gap-2">
            <button
              disabled={pagina === 1}
              onClick={() => setPagina(pagina - 1)}
              className="px-3 py-1.5 text-xs border border-zinc-200 rounded hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              ← Anterior
            </button>
            <button
              disabled={pagina >= totalPaginas}
              onClick={() => setPagina(pagina + 1)}
              className="px-3 py-1.5 text-xs border border-zinc-200 rounded hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Siguiente →
            </button>
          </div>
        </div>
      )}

      {docModal ? (
        <ModalDetalleDocumento
          doc={docModal}
          onClose={() => setDocAbierto(null)}
          onEliminar={(id) => mutEliminar.mutate(id)}
        />
      ) : null}
    </div>
  )
}

// =============================================================================
// Tab: Análisis generados por IC
// =============================================================================

const TIPOS_FILTRO = [
  { value: "", label: "Todos" },
  { value: "investigacion", label: "Investigaciones" },
  { value: "propuesta", label: "Propuestas" },
  { value: "pdf", label: "PDFs" },
  { value: "pptx", label: "Decks" },
  { value: "briefing", label: "Briefings" },
  { value: "informe", label: "Informes" },
  { value: "chat", label: "Chats IC" },
  { value: "audio", label: "Audios" },
]

const CONTEXTO_FILTRO = [
  { value: "", label: "Todos los contextos" },
  { value: "cuenta", label: "Cuenta" },
  { value: "cliente", label: "Cliente" },
  { value: "producto", label: "Producto" },
  { value: "oportunidad", label: "Oportunidad" },
]

function TabAnalisisIA({ puedeFiltrarComercial, propietarioId }: { puedeFiltrarComercial: boolean; propietarioId?: string }) {
  const [filtroBusqueda, setFiltroBusqueda] = useState("")
  const [filtroTipo, setFiltroTipo] = useState("")
  const [artefactoAbiertoId, setArtefactoAbiertoId] = useState<string | null>(null)
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const contextoTipo = searchParams.get("contexto_tipo") as "cuenta" | "cliente" | "producto" | "oportunidad" | null
  const contextoId = searchParams.get("contexto_id")
  const queryClient = useQueryClient()

  const { data = [], isLoading } = useQuery<DocumentoHistorial[]>({
    queryKey: ["historial-ia", contextoTipo ?? "all", contextoId ?? "all", propietarioId ?? "all"],
    queryFn: async () => {
      const respuesta = await api.artefactos.listar({
        entidad_tipo: contextoTipo ?? undefined,
        entidad_id: contextoId ?? undefined,
        propietario_id: propietarioId,
        por_pagina: 200,
      })
      const datos = (respuesta.datos ?? []) as Array<Record<string, unknown>>
      return datos.map((item) => {
        const subtipo = String(item.subtipo ?? item.tipo ?? "documento")
        const entidad = String(item.entidad_nombre ?? "N/A")
        const titulo = String(item.titulo ?? "Artefacto IC")
        const creadoEn = String(item.creado_en ?? new Date().toISOString())
        return {
          id: String(item.id),
          tipo: subtipo,
          nombre_fichero: titulo,
          tamano_bytes: null,
          metadatos: {
            ...(item.extra ?? {}),
            origen_tabla: item.origen_tabla ?? null,
            origen_id: item.origen_id ?? null,
          },
          contexto_tipo: String(item.entidad_tipo ?? "cuenta"),
          contexto_id: String(item.entidad_id ?? ""),
          creado_en: creadoEn,
          cuenta_nombre: entidad,
          usuario_nombre: String(item.usuario_nombre ?? "N/A"),
        } as DocumentoHistorial
      })
    },
    staleTime: 30_000,
  })

  const { data: resumenData = [] } = useQuery<DocumentoHistorial[]>({
    queryKey: ["historial-ia-resumen", propietarioId ?? "all"],
    queryFn: async () => {
      const respuesta = await api.artefactos.listar({ por_pagina: 200, propietario_id: propietarioId })
      const datos = (respuesta.datos ?? []) as Array<Record<string, unknown>>
      return datos.map((item) => ({
        id: String(item.id),
        tipo: String(item.subtipo ?? item.tipo ?? "documento"),
        nombre_fichero: String(item.titulo ?? "Artefacto IC"),
        tamano_bytes: null,
        metadatos: {
          ...(item.extra ?? {}),
          origen_tabla: item.origen_tabla ?? null,
          origen_id: item.origen_id ?? null,
        },
        contexto_tipo: String(item.entidad_tipo ?? "cuenta"),
        contexto_id: String(item.entidad_id ?? ""),
        creado_en: String(item.creado_en ?? new Date().toISOString()),
        cuenta_nombre: String(item.entidad_nombre ?? "N/A"),
        usuario_nombre: String(item.usuario_nombre ?? "N/A"),
      })) as DocumentoHistorial[]
    },
    staleTime: 30_000,
  })

  const metricas = useMemo(() => {
    const ahora = Date.now()
    const hace7dias = ahora - 7 * 24 * 60 * 60 * 1000
    const ultimos7Dias = resumenData.filter((d) => Date.parse(d.creado_en) >= hace7dias).length
    const porContexto = resumenData.reduce<Record<string, number>>((acc, d) => {
      const key = d.contexto_tipo ?? "sin_contexto"
      acc[key] = (acc[key] ?? 0) + 1
      return acc
    }, {})
    return {
      total: resumenData.length,
      ultimos7Dias,
      porContexto,
    }
  }, [resumenData])

  function cambiarFiltroContexto(tipo: string) {
    const params = new URLSearchParams(searchParams.toString())
    params.set("tab", "ia")
    if (tipo) {
      params.set("contexto_tipo", tipo)
      params.delete("contexto_id")
    } else {
      params.delete("contexto_tipo")
      params.delete("contexto_id")
    }
    router.push(`${pathname}?${params.toString()}`)
  }

  const analisis = data.filter((d) => {
    const matchTipo = !filtroTipo || d.tipo === filtroTipo
    const cuentaNombre = (d.cuenta_nombre ?? "").toLowerCase()
    const nombreFichero = d.nombre_fichero.toLowerCase()
    const busqueda = filtroBusqueda.toLowerCase()
    const matchBusqueda = !filtroBusqueda ||
      cuentaNombre.includes(busqueda) ||
      nombreFichero.includes(busqueda)
    return matchTipo && matchBusqueda
  })

  const nombreCsv = `trazabilidad_ia_${new Date().toISOString().slice(0, 10)}.csv`

  function handleEliminar(id: string) {
    queryClient.setQueriesData<DocumentoHistorial[]>({ queryKey: ["historial-ia"] }, (prev) =>
      prev ? prev.filter((d) => d.id !== id) : []
    )
    queryClient.invalidateQueries({ queryKey: ["historial-ia-resumen"] })
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="rounded-xl border border-zinc-200 bg-white px-4 py-3">
          <p className="text-[10px] uppercase tracking-widest text-zinc-400">Total artefactos IC</p>
          <p className="text-lg font-semibold text-zinc-900">{metricas.total}</p>
        </div>
        <div className="rounded-xl border border-zinc-200 bg-white px-4 py-3">
          <p className="text-[10px] uppercase tracking-widest text-zinc-400">Últimos 7 días</p>
          <p className="text-lg font-semibold text-zinc-900">{metricas.ultimos7Dias}</p>
        </div>
        <div className="rounded-xl border border-zinc-200 bg-white px-4 py-3">
          <p className="text-[10px] uppercase tracking-widest text-zinc-400">Contexto dominante</p>
          <p className="text-lg font-semibold text-zinc-900">
            {Object.entries(metricas.porContexto).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—"}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {CONTEXTO_FILTRO.map((ctx) => {
          const activo = (contextoTipo ?? "") === ctx.value
          const total = ctx.value ? (metricas.porContexto[ctx.value] ?? 0) : metricas.total
          return (
            <button
              key={ctx.value}
              onClick={() => cambiarFiltroContexto(ctx.value)}
              className={cn(
                "px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors",
                activo
                  ? "bg-sgs-rojo text-white border-sgs-rojo"
                  : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-300",
              )}
            >
              {ctx.label} ({total})
            </button>
          )
        })}
      </div>

      {(contextoTipo || contextoId) && (
        <div className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-600">
          Trazabilidad IC filtrada por contexto:
          <span className="ml-1 font-semibold">{contextoTipo ?? "—"}</span>
          {contextoId ? <span className="ml-1 text-zinc-500">({contextoId.slice(0, 8)}…)</span> : null}
          <Link href="/documentos?tab=ia" className="ml-2 text-sgs-rojo hover:underline">Quitar filtro</Link>
        </div>
      )}

      <div className="rounded-xl border border-zinc-200 bg-white p-3.5">
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-zinc-900">Repositorio IC agrupado por origen</h3>
          <p className="text-xs text-zinc-500 mt-1">
            Selecciona cualquier artefacto para previsualizarlo y reutilizar su contenido en nuevas consultas.
          </p>
        </div>
        <ArtefactoPicker
          contextoTipo={contextoTipo ?? undefined}
          contextoId={contextoId ?? undefined}
          propietarioId={propietarioId}
          modoModal
        />
      </div>

      {/* Filtros */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
          <input
            type="text"
            placeholder="Buscar por empresa o fichero..."
            value={filtroBusqueda}
            onChange={(e) => setFiltroBusqueda(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-zinc-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
          />
        </div>

        <div className="flex gap-1">
          {TIPOS_FILTRO.map((t) => (
            <button
              key={t.value}
              onClick={() => setFiltroTipo(t.value)}
              className={cn(
                "px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors",
                filtroTipo === t.value
                  ? "bg-sgs-rojo text-white border-sgs-rojo"
                  : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-300"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        <p className="text-xs text-zinc-400 ml-auto shrink-0">
          {analisis.length} {analisis.length === 1 ? "análisis" : "análisis"}
        </p>
        {puedeFiltrarComercial && (
          <span className="text-[11px] text-zinc-500 shrink-0">Filtrado por comercial</span>
        )}
        <button
          onClick={() => exportarCsvAnalisis(nombreCsv, analisis)}
          disabled={analisis.length === 0}
          className="px-3 py-1.5 text-xs font-medium rounded-lg border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Exportar CSV
        </button>
      </div>

      {/* Lista */}
      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <div className="h-7 w-7 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
        </div>
      ) : analisis.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 gap-3">
          <Brain className="h-10 w-10 text-zinc-200" />
          <p className="text-sm text-zinc-400">
            {filtroBusqueda || filtroTipo
              ? "Sin resultados para estos filtros."
              : "Aún no hay análisis generados. Genera PDFs, decks o briefings desde la ficha de una cuenta."}
          </p>
          {!filtroBusqueda && !filtroTipo && (
            <Link
              href="/cuentas"
              className="flex items-center gap-1 text-xs text-sgs-rojo hover:underline"
            >
              Ir a cuentas <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {analisis.map((doc) => (
            <FilaAnalisis key={doc.id} doc={doc} onEliminar={handleEliminar} onAbrir={setArtefactoAbiertoId} />
          ))}
        </div>
      )}

      {artefactoAbiertoId ? (
        <ModalDetalleArtefacto artefactoId={artefactoAbiertoId} onClose={() => setArtefactoAbiertoId(null)} />
      ) : null}
    </div>
  )
}

// =============================================================================
// Página principal con tabs
// =============================================================================

type Tab = "archivos" | "ia"

function DocumentosPageContent() {
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()
  const tabQuery = searchParams.get("tab")
  const contextoTipo = searchParams.get("contexto_tipo")
  const contextoId = searchParams.get("contexto_id")
  const tabInicial: Tab = tabQuery === "ia" || contextoTipo || contextoId ? "ia" : "archivos"
  const [tab, setTab] = useState<Tab>(tabInicial)
  const { isManager } = useAppStore()
  const [propietarioId, setPropietarioId] = useState("")
  const puedeFiltrarComercial = isManager()
  const propietarioFiltro = puedeFiltrarComercial && propietarioId ? propietarioId : undefined

  const { data: comerciales = [] } = useQuery<Array<{ propietario_id: string; nombre_completo: string }>>({
    queryKey: ["equipo-ranking-selector-documentos"],
    queryFn: () => api.equipo.ranking() as Promise<Array<{ propietario_id: string; nombre_completo: string }>>,
    enabled: puedeFiltrarComercial,
  })

  useEffect(() => {
    setTab(tabInicial)
  }, [tabInicial])

  function cambiarTab(siguiente: Tab) {
    setTab(siguiente)
    const params = new URLSearchParams(searchParams.toString())
    if (siguiente === "ia") {
      params.set("tab", "ia")
    } else {
      params.delete("tab")
      params.delete("contexto_tipo")
      params.delete("contexto_id")
    }
    const query = params.toString()
    router.replace(query ? `${pathname}?${query}` : pathname)
  }

  return (
    <div className="flex-1 flex flex-col">
      <Topbar
        titulo="Documentos"
        subtitulo="Archivos manuales y análisis generados por IC"
      />
      <main className="flex-1 p-2.5 md:p-3.5 w-full">
        {puedeFiltrarComercial && (
          <div className="mb-3.5 rounded-xl border border-zinc-200 bg-white p-3">
            <label className="block text-[11px] font-semibold uppercase tracking-wide text-zinc-500 mb-1">
              Filtrar por comercial
            </label>
            <select
              value={propietarioId}
              onChange={(e) => setPropietarioId(e.target.value)}
              className="w-full max-w-sm px-3 py-2 text-sm border border-zinc-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
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
        <div className="glass-card mb-3.5 p-1.5 inline-flex gap-1">
          {(
            [
              { key: "archivos", label: "Mis archivos" },
              { key: "ia", label: "Análisis IC" },
            ] as { key: Tab; label: string }[]
          ).map(({ key, label }) => (
            <button
              key={key}
              onClick={() => cambiarTab(key)}
              className={cn(
                "px-3 py-1.5 text-sm font-medium rounded-lg transition-colors",
                tab === key
                  ? "bg-white/15 text-white border border-white/20"
                  : "text-zinc-300 hover:text-white hover:bg-white/5"
              )}
            >
              {label}
            </button>
          ))}
        </div>
        {tab === "archivos" ? (
          <TabMisDocumentos puedeFiltrarComercial={puedeFiltrarComercial} propietarioId={propietarioFiltro} />
        ) : (
          <TabAnalisisIA puedeFiltrarComercial={puedeFiltrarComercial} propietarioId={propietarioFiltro} />
        )}
      </main>
    </div>
  )
}

export default function DocumentosPage() {
  return (
    <Suspense fallback={<div className="flex-1 p-6 text-sm text-zinc-500">Cargando documentos...</div>}>
      <DocumentosPageContent />
    </Suspense>
  )
}
