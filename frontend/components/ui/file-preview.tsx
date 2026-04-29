"use client"

import Image from "next/image"
import { useEffect, useMemo, useState } from "react"

import { cn } from "@/lib/utils"

function esTextoPrevisualizable(mime: string | null, nombre: string) {
  const tipo = (mime ?? "").toLowerCase()
  if (tipo.startsWith("text/")) return true
  if (tipo.includes("json") || tipo.includes("xml")) return true
  return /\.(txt|csv|json|xml|md|log)$/i.test(nombre)
}

export function detectarTipoVista(
  mime: string | null,
  nombre: string,
): "pdf" | "audio" | "image" | "text" | "pptx" | "generic" {
  const tipo = (mime ?? "").toLowerCase()
  if (tipo.includes("pdf") || /\.pdf$/i.test(nombre)) return "pdf"
  if (tipo.startsWith("audio/") || /\.(mp3|wav|m4a|ogg|webm|mpeg)$/i.test(nombre)) return "audio"
  if (tipo.startsWith("image/") || /\.(png|jpe?g|gif|webp|svg)$/i.test(nombre)) return "image"
  if (tipo.includes("presentation") || /\.(pptx?)$/i.test(nombre)) return "pptx"
  if (esTextoPrevisualizable(mime, nombre)) return "text"
  return "generic"
}

export function mimeDesdeSubtipo(subtipo: string) {
  const valor = subtipo.toLowerCase()
  if (valor === "pdf" || valor === "informe") return "application/pdf"
  if (valor === "pptx" || valor === "deck") return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
  if (valor === "briefing" || valor === "audio") return "audio/mpeg"
  if (valor === "chat" || valor === "transcripcion") return "text/plain"
  if (valor === "investigacion" || valor === "propuesta") return "application/json"
  return "application/octet-stream"
}

export interface DiapositivaPrevia {
  index: number
  titulo: string
  cuerpo: string
  notas: string
}

type VistaPreviaModo = "compacta" | "amplia"

function VisorPresentacion({
  nombre,
  slides,
  modo,
}: {
  nombre: string
  slides: DiapositivaPrevia[]
  modo: VistaPreviaModo
}) {
  const [indice, setIndice] = useState(0)

  useEffect(() => { setIndice(0) }, [nombre, slides.length])

  const slide = slides[Math.min(indice, Math.max(0, slides.length - 1))]

  return (
    <div className="flex flex-col gap-4">
      {/* Slide activa — ancho completo */}
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-zinc-950 text-white shadow-[0_20px_60px_rgba(0,0,0,0.35)]">
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
          <div>
            <p className="text-[10px] uppercase tracking-[0.28em] text-zinc-400">Presentación PPTX</p>
            <p className="mt-1 text-sm font-semibold text-white">{nombre}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIndice((i) => Math.max(0, i - 1))}
              disabled={indice === 0}
              className="rounded-lg border border-white/10 px-2.5 py-1 text-xs text-zinc-400 hover:bg-white/5 disabled:opacity-30 transition-colors"
            >
              ←
            </button>
            <p className="text-[11px] text-zinc-400 tabular-nums">
              {slides.length ? `${indice + 1} / ${slides.length}` : "0/0"}
            </p>
            <button
              onClick={() => setIndice((i) => Math.min(slides.length - 1, i + 1))}
              disabled={indice >= slides.length - 1}
              className="rounded-lg border border-white/10 px-2.5 py-1 text-xs text-zinc-400 hover:bg-white/5 disabled:opacity-30 transition-colors"
            >
              →
            </button>
          </div>
        </div>

        <div className={cn(
          "bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.08),transparent_40%),linear-gradient(180deg,rgba(15,15,15,0.98),rgba(5,5,5,0.98))] px-4 py-4",
          modo === "amplia" ? "min-h-[34rem]" : "min-h-[24rem]"
        )}>
          {slide ? (
            <div className="flex h-full min-h-[20rem] flex-col justify-between rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur-xl">
              <div className="space-y-4">
                <p className="text-[10px] uppercase tracking-[0.3em] text-zinc-400">Slide {slide.index}</p>
                <h3 className="text-2xl font-semibold leading-tight text-white md:text-3xl">
                  {slide.titulo || "Sin título"}
                </h3>
                {slide.cuerpo ? (
                  <p className="whitespace-pre-wrap text-base leading-relaxed text-zinc-200">{slide.cuerpo}</p>
                ) : (
                  <p className="text-sm text-zinc-400">Sin contenido textual para esta diapositiva.</p>
                )}
              </div>
              {slide.notas && (
                <div className="mt-6 rounded-xl border border-white/10 bg-black/25 p-4">
                  <p className="text-[10px] uppercase tracking-[0.3em] text-zinc-500">Notas del presentador</p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-zinc-300">{slide.notas}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="flex h-full min-h-[20rem] items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/5 p-8 text-center text-sm text-zinc-400">
              No hay diapositivas extraídas para esta presentación.
            </div>
          )}
        </div>
      </div>

      {/* Tira de miniaturas horizontal */}
      {slides.length > 0 && (
        <div>
          <p className="mb-2 text-[10px] uppercase tracking-[0.3em] text-zinc-400">Diapositivas</p>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {slides.map((slideItem, index) => {
              const activa = index === indice
              return (
                <button
                  key={slideItem.index}
                  onClick={() => setIndice(index)}
                  className={cn(
                    "w-44 shrink-0 rounded-xl border p-3 text-left transition-colors",
                    activa
                      ? "border-white/25 bg-white/10 text-white ring-1 ring-white/20"
                      : "border-white/10 bg-black/20 text-zinc-300 hover:bg-white/5",
                  )}
                >
                  <p className="text-[10px] tabular-nums text-zinc-500">#{slideItem.index}</p>
                  <p className="mt-1 line-clamp-2 text-xs font-semibold leading-snug">
                    {slideItem.titulo || "Sin título"}
                  </p>
                  {slideItem.cuerpo && (
                    <p className="mt-1 line-clamp-2 text-[10px] leading-relaxed text-zinc-400">
                      {slideItem.cuerpo}
                    </p>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function SeccionAudio({
  url,
  nombre,
  transcripcion,
  modo,
}: {
  url: string
  nombre: string
  transcripcion?: string | null
  modo: VistaPreviaModo
}) {
  return (
    <div className="flex flex-col gap-4">
      {/* Reproductor */}
      <div className="rounded-2xl border border-white/10 bg-zinc-950/95 p-5 text-white shadow-[0_20px_60px_rgba(0,0,0,0.28)]">
        <p className="text-[10px] uppercase tracking-[0.3em] text-zinc-400">Audio</p>
        <p className="mt-1.5 text-sm font-semibold text-white">{nombre}</p>
        <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur-xl">
          <audio src={url} controls className="w-full" />
        </div>
      </div>

      {/* Transcripción */}
      <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
        <p className="text-[10px] uppercase tracking-[0.3em] text-zinc-500 mb-3">Transcripción</p>
        <div className={cn(
          "overflow-auto rounded-xl border border-zinc-100 bg-zinc-50 p-4",
          modo === "amplia" ? "max-h-[40rem]" : "max-h-[28rem]"
        )}>
          {transcripcion ? (
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-700">{transcripcion}</p>
          ) : (
            <p className="text-sm text-zinc-400">No hay transcripción asociada a este audio.</p>
          )}
        </div>
      </div>
    </div>
  )
}

export function VistaPreviaArchivo({
  blob,
  mime,
  nombre,
  transcripcion,
  slides,
  modo = "compacta",
}: {
  blob: Blob
  mime: string | null
  nombre: string
  transcripcion?: string | null
  slides?: DiapositivaPrevia[]
  modo?: VistaPreviaModo
}) {
  const [texto, setTexto] = useState("")
  const [url, setUrl] = useState("")
  const tipoVista = detectarTipoVista(mime, nombre)
  const slidesValidas = useMemo(() => slides ?? [], [slides])

  useEffect(() => {
    const objectUrl = URL.createObjectURL(blob)
    setUrl(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [blob])

  useEffect(() => {
    if (tipoVista !== "text") {
      setTexto("")
      return
    }
    blob
      .text()
      .then((contenido) => setTexto(contenido.slice(0, 120_000)))
      .catch(() => setTexto("No se pudo cargar la previsualización textual."))
  }, [blob, tipoVista])

  const marcoBase = cn(
    "rounded-2xl border shadow-sm",
    modo === "amplia"
      ? "border-white/10 bg-zinc-950/95 p-4 md:p-5"
      : "border-zinc-200 bg-white p-3",
  )

  if (!url) {
    return <p className="text-sm text-zinc-500">Preparando previsualización...</p>
  }

  if (tipoVista === "pdf") {
    return (
      <div className={marcoBase}>
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <p className={cn("text-[10px] uppercase tracking-[0.3em]", modo === "amplia" ? "text-zinc-400" : "text-zinc-500")}>PDF</p>
            <p className={cn("mt-1 text-sm font-semibold", modo === "amplia" ? "text-white" : "text-zinc-900")}>{nombre}</p>
          </div>
          <p className={cn("text-xs", modo === "amplia" ? "text-zinc-400" : "text-zinc-500")}>Vista centrada</p>
        </div>
        <iframe
          src={url}
          title={nombre}
          className={cn(
            "w-full rounded-xl border",
            modo === "amplia"
              ? "h-[65vh] border-white/10 bg-white"
              : "h-[60vh] border-zinc-200 bg-white",
          )}
        />
      </div>
    )
  }

  if (tipoVista === "audio") {
    return (
      <div className={marcoBase}>
        <SeccionAudio url={url} nombre={nombre} transcripcion={transcripcion} modo={modo} />
      </div>
    )
  }

  if (tipoVista === "image") {
    return (
      <div className={marcoBase}>
        <div className={cn("flex items-center justify-center rounded-xl", modo === "amplia" ? "min-h-[50vh] bg-black/10" : "bg-zinc-50")}>
          <div
            className={cn(
              "relative overflow-hidden rounded-xl border",
              modo === "amplia"
                ? "h-[65vh] w-full border-white/10 bg-black/20"
                : "h-[60vh] w-full border-zinc-200 bg-white",
            )}
          >
            <Image
              src={url}
              alt={nombre}
              fill
              unoptimized
              sizes="100vw"
              className="object-contain p-4"
            />
          </div>
        </div>
      </div>
    )
  }

  if (tipoVista === "text") {
    return (
      <div className={marcoBase}>
        <pre
          className={cn(
            "max-h-[78vh] overflow-auto whitespace-pre-wrap break-words rounded-xl border p-4 text-sm leading-relaxed",
            modo === "amplia"
              ? "border-white/10 bg-black/25 text-zinc-100"
              : "border-zinc-200 bg-zinc-50 text-zinc-700",
          )}
        >
          {texto || "Sin contenido textual para mostrar."}
        </pre>
      </div>
    )
  }

  if (tipoVista === "pptx") {
    if (slidesValidas.length > 0) {
      return (
        <div className={marcoBase}>
          <VisorPresentacion nombre={nombre} slides={slidesValidas} modo={modo} />
        </div>
      )
    }
    return (
      <div className={cn(marcoBase, modo === "amplia" ? "text-zinc-100" : "text-zinc-600")}>
        <div className={cn("rounded-xl border p-5 text-sm", modo === "amplia" ? "border-white/10 bg-black/25" : "border-zinc-200 bg-zinc-50")}>
          <p className="font-semibold">Presentación PowerPoint</p>
          <p className={cn("mt-1", modo === "amplia" ? "text-zinc-300" : "text-zinc-500")}>
            Las diapositivas no pudieron extraerse. Descarga el archivo para verlo en PowerPoint.
          </p>
        </div>
      </div>
    )
  }

  if (tipoVista === "generic" && slidesValidas.length > 0) {
    return (
      <div className={marcoBase}>
        <VisorPresentacion nombre={nombre} slides={slidesValidas} modo={modo} />
      </div>
    )
  }

  return (
    <div className={cn(marcoBase, modo === "amplia" ? "text-zinc-100" : "text-zinc-600")}>
      <div className={cn("rounded-xl border p-4 text-sm", modo === "amplia" ? "border-white/10 bg-black/25" : "border-zinc-200 bg-zinc-50")}>
        <p className="font-medium">No hay visor nativo para este formato en web.</p>
        <p className={cn("mt-1", modo === "amplia" ? "text-zinc-300" : "text-zinc-500")}>
          Puedes abrirlo o descargarlo desde los botones superiores.
        </p>
      </div>
    </div>
  )
}
