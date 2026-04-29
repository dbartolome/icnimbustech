"use client"

import { useState, useRef, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import { Topbar } from "@/components/layout/topbar"
import type { NotaRead } from "@/types"

// =============================================================================
// Const types
// =============================================================================

const ESTADO_GRAB = {
  IDLE: "idle",
  GRABANDO: "grabando",
  DETENIDO: "detenido",
} as const

type EstadoGrab = (typeof ESTADO_GRAB)[keyof typeof ESTADO_GRAB]

// =============================================================================
// Panel de grabación — MediaRecorder (todos los browsers)
// =============================================================================

function formatDuracion(seg: number): string {
  const m = Math.floor(seg / 60)
  const s = seg % 60
  return m > 0 ? `${m}:${s.toString().padStart(2, "0")}` : `${s}s`
}

function PanelGrabacion({ onGuardada }: { onGuardada: () => void }) {
  const [estado, setEstado] = useState<EstadoGrab>(ESTADO_GRAB.IDLE)
  const [titulo, setTitulo] = useState("")
  const [duracionSeg, setDuracionSeg] = useState(0)
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [blob, setBlob] = useState<Blob | null>(null)
  const [procesando, setProcesando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const inicioRef = useRef<number>(0)

  useEffect(() => {
    return () => {
      recorderRef.current?.state === "recording" && recorderRef.current.stop()
      if (timerRef.current) clearInterval(timerRef.current)
      if (blobUrl) URL.revokeObjectURL(blobUrl)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function iniciarGrabacion() {
    setError(null)
    setBlobUrl(null)
    setBlob(null)
    setDuracionSeg(0)
    chunksRef.current = []

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setError("No se pudo acceder al micrófono. Verifica los permisos del navegador.")
      return
    }

    // Elegir el tipo soportado más compatible
    const tipo = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg", "audio/mp4", ""]
      .find((t) => !t || MediaRecorder.isTypeSupported(t)) ?? ""

    const recorder = new MediaRecorder(stream, tipo ? { mimeType: tipo } : undefined)
    recorderRef.current = recorder

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }

    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop())
      const grabado = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" })
      const url = URL.createObjectURL(grabado)
      setBlob(grabado)
      setBlobUrl(url)
      setEstado(ESTADO_GRAB.DETENIDO)
    }

    recorder.start(250) // chunk cada 250ms
    inicioRef.current = Date.now()
    timerRef.current = setInterval(() => {
      setDuracionSeg(Math.floor((Date.now() - inicioRef.current) / 1000))
    }, 1000)
    setEstado(ESTADO_GRAB.GRABANDO)
  }

  function detenerGrabacion() {
    recorderRef.current?.stop()
    if (timerRef.current) clearInterval(timerRef.current)
    setDuracionSeg(Math.floor((Date.now() - inicioRef.current) / 1000))
  }

  async function transcribirYGuardar() {
    if (!blob) return
    setProcesando(true)
    setError(null)
    const ext = blob.type.includes("ogg") ? ".ogg" : blob.type.includes("mp4") ? ".mp4" : ".webm"
    const archivo = new File([blob], `grabacion${ext}`, { type: blob.type })
    try {
      await api.notas.subirAudio(archivo, { titulo: titulo.trim() || undefined })
      descartar()
      onGuardada()
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo transcribir el audio.")
    } finally {
      setProcesando(false)
    }
  }

  function descartar() {
    recorderRef.current?.state === "recording" && recorderRef.current.stop()
    if (timerRef.current) clearInterval(timerRef.current)
    if (blobUrl) URL.revokeObjectURL(blobUrl)
    setBlobUrl(null)
    setBlob(null)
    setDuracionSeg(0)
    setTitulo("")
    setEstado(ESTADO_GRAB.IDLE)
    setError(null)
  }

  return (
    <div className="bg-white rounded-xl border border-zinc-200 p-5 space-y-4">
      <h2 className="text-sm font-semibold text-zinc-800">Nueva nota de voz</h2>

      {/* Título */}
      <input
        type="text"
        placeholder="Título de la nota (opcional)"
        value={titulo}
        onChange={(e) => setTitulo(e.target.value)}
        maxLength={200}
        disabled={estado === ESTADO_GRAB.GRABANDO}
        className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent disabled:opacity-50"
      />

      {/* Visualización de estado */}
      {estado === ESTADO_GRAB.GRABANDO && (
        <div className="flex items-center gap-3 px-3 py-3 rounded-lg bg-red-50 border border-red-100">
          <span className="w-2.5 h-2.5 rounded-full bg-sgs-rojo animate-pulse shrink-0" />
          <span className="text-sm font-medium text-red-700">Grabando — {formatDuracion(duracionSeg)}</span>
        </div>
      )}

      {estado === ESTADO_GRAB.DETENIDO && blobUrl && (
        <div className="space-y-2">
          <p className="text-xs text-zinc-500">
            Grabación completada · {formatDuracion(duracionSeg)} · revisa antes de transcribir
          </p>
          <audio controls src={blobUrl} className="w-full" />
        </div>
      )}

      {/* Controles */}
      <div className="flex items-center gap-2 flex-wrap">
        {estado === ESTADO_GRAB.IDLE && (
          <button
            onClick={iniciarGrabacion}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-sgs-rojo rounded-lg hover:bg-red-700 transition-colors"
          >
            ● Iniciar grabación
          </button>
        )}

        {estado === ESTADO_GRAB.GRABANDO && (
          <button
            onClick={detenerGrabacion}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium border border-zinc-300 text-zinc-700 rounded-lg hover:bg-zinc-50 transition-colors"
          >
            ■ Detener
          </button>
        )}

        {estado === ESTADO_GRAB.DETENIDO && (
          <>
            <button
              onClick={transcribirYGuardar}
              disabled={procesando || !blob}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-sgs-rojo rounded-lg disabled:opacity-50 transition-opacity"
            >
              {procesando ? (
                <>
                  <span className="w-3 h-3 border border-white/40 border-t-white rounded-full animate-spin" />
                  Transcribiendo…
                </>
              ) : (
                "Transcribir y guardar"
              )}
            </button>
            <button
              onClick={iniciarGrabacion}
              disabled={procesando}
              className="px-4 py-2 text-sm font-medium border border-zinc-300 text-zinc-700 rounded-lg hover:bg-zinc-50 disabled:opacity-50 transition-colors"
            >
              ● Volver a grabar
            </button>
            <button
              onClick={descartar}
              disabled={procesando}
              className="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-zinc-700 disabled:opacity-50 transition-colors"
            >
              Descartar
            </button>
          </>
        )}
      </div>

      {error && (
        <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
      )}
    </div>
  )
}

function PanelSubidaAudio({ onGuardada }: { onGuardada: () => void }) {
  const [archivo, setArchivo] = useState<File | null>(null)
  const [titulo, setTitulo] = useState("")
  const [subiendo, setSubiendo] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function subirYTranscribir() {
    if (!archivo) {
      setError("Selecciona un archivo de audio.")
      return
    }
    setSubiendo(true)
    setError(null)
    try {
      await api.notas.subirAudio(archivo, { titulo: titulo.trim() || undefined })
      setArchivo(null)
      setTitulo("")
      onGuardada()
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo transcribir el audio.")
    } finally {
      setSubiendo(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-zinc-200 p-5 space-y-4">
      <h2 className="text-sm font-semibold text-zinc-800">Subir audio y transcribir</h2>

      <input
        type="text"
        placeholder="Título de la nota (opcional)"
        value={titulo}
        onChange={(e) => setTitulo(e.target.value)}
        maxLength={200}
        className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
      />

      <input
        type="file"
        accept="audio/*,.mp3,.wav,.m4a,.ogg,.webm,.mp4,.mpeg"
        onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
        className="w-full text-sm border border-zinc-200 rounded-lg bg-white file:mr-3 file:px-3 file:py-2 file:border-0 file:bg-zinc-100 file:text-zinc-700"
      />

      {archivo && (
        <p className="text-xs text-zinc-500">
          Archivo: <span className="font-medium text-zinc-700">{archivo.name}</span> · {(archivo.size / 1024 / 1024).toFixed(2)} MB
        </p>
      )}

      <div className="flex items-center gap-2">
        <button
          onClick={subirYTranscribir}
          disabled={subiendo || !archivo}
          className="px-4 py-2 text-sm font-medium text-white bg-sgs-rojo rounded-lg disabled:opacity-50 transition-opacity"
        >
          {subiendo ? "Transcribiendo..." : "Subir y transcribir"}
        </button>
      </div>

      {error && (
        <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
      )}
    </div>
  )
}

// =============================================================================
// Tarjeta de nota
// =============================================================================

function TarjetaNota({
  nota,
  onEliminar,
}: {
  nota: NotaRead
  onEliminar: (id: string) => void
}) {
  const [expandida, setExpandida] = useState(false)
  const palabras = nota.transcripcion.split(" ").length
  const preview = nota.transcripcion.slice(0, 160)
  const tieneMore = nota.transcripcion.length > 160

  return (
    <div className="bg-white rounded-xl border border-zinc-200 p-4 hover:border-zinc-300 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-zinc-900 truncate">{nota.titulo}</h3>
            {nota.oportunidad_nombre && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-700 shrink-0">
                {nota.oportunidad_nombre.slice(0, 30)}{nota.oportunidad_nombre.length > 30 ? "…" : ""}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-[10px] text-zinc-400">{nota.creado_en.slice(0, 10)}</span>
            {nota.duracion_seg && (
              <span className="text-[10px] text-zinc-400">{nota.duracion_seg}s de grabación</span>
            )}
            <span className="text-[10px] text-zinc-400">{palabras} palabras</span>
          </div>
        </div>
        <button
          onClick={() => onEliminar(nota.id)}
          className="text-zinc-300 hover:text-red-500 transition-colors shrink-0 text-sm"
          title="Eliminar nota"
        >
          ✕
        </button>
      </div>

      <div className="mt-3">
        <p className="text-sm text-zinc-600 leading-relaxed">
          {expandida ? nota.transcripcion : preview}
          {tieneMore && !expandida && "…"}
        </p>
        {tieneMore && (
          <button
            onClick={() => setExpandida(!expandida)}
            className="mt-1 text-xs text-sgs-rojo hover:underline"
          >
            {expandida ? "Ver menos" : "Ver más"}
          </button>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Página principal
// =============================================================================

export default function NotasPage() {
  const [busqueda, setBusqueda] = useState("")
  const [pagina, setPagina] = useState(1)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery<{
    total: number
    pagina: number
    por_pagina: number
    datos: NotaRead[]
  }>({
    queryKey: ["notas", busqueda, pagina],
    queryFn: () =>
      api.notas.listar({ busqueda: busqueda || undefined, pagina }) as Promise<{
        total: number
        pagina: number
        por_pagina: number
        datos: NotaRead[]
      }>,
  })

  const mutEliminar = useMutation({
    mutationFn: (id: string) => api.notas.eliminar(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notas"] }),
  })

  const totalPaginas = data ? Math.ceil(data.total / data.por_pagina) : 1

  return (
    <div className="flex-1 flex flex-col">
      <Topbar
        titulo="Notas de Voz"
        subtitulo={data ? `${data.total} notas guardadas` : "Captura y organiza notas comerciales por voz"}
      />
      {/* Header */}
      <header className="px-6 py-5 border-b border-zinc-200 bg-white">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-zinc-900">Notas de Voz</h1>
            <p className="text-sm text-zinc-500 mt-0.5">
              {data ? `${data.total} notas guardadas` : "Cargando..."}
            </p>
          </div>
          <div className="relative w-64">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 text-sm">◎</span>
            <input
              type="text"
              placeholder="Buscar en notas..."
              value={busqueda}
              onChange={(e) => { setBusqueda(e.target.value); setPagina(1) }}
              className="w-full pl-8 pr-3 py-2 text-sm border border-zinc-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
            />
          </div>
        </div>
      </header>

      <main className="flex-1 p-2.5 md:p-3.5 w-full space-y-5">
        {/* Panel de grabación */}
        <PanelGrabacion
          onGuardada={() => {
            queryClient.invalidateQueries({ queryKey: ["notas"] })
            setPagina(1)
          }}
        />
        <PanelSubidaAudio
          onGuardada={() => {
            queryClient.invalidateQueries({ queryKey: ["notas"] })
            setPagina(1)
          }}
        />

        {/* Lista de notas */}
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="h-7 w-7 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
          </div>
        ) : !data?.datos.length ? (
          <div className="flex flex-col items-center justify-center h-32 gap-2">
            <span className="text-3xl text-zinc-300">◎</span>
            <p className="text-sm text-zinc-500">
              {busqueda ? "Sin resultados para tu búsqueda." : "Aún no tienes notas guardadas."}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {data.datos.map((nota) => (
              <TarjetaNota
                key={nota.id}
                nota={nota}
                onEliminar={(id) => mutEliminar.mutate(id)}
              />
            ))}
          </div>
        )}

        {/* Paginación */}
        {data && totalPaginas > 1 && (
          <div className="flex items-center justify-between pt-2">
            <p className="text-xs text-zinc-500">
              Página {pagina} de {totalPaginas}
            </p>
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
      </main>
    </div>
  )
}
