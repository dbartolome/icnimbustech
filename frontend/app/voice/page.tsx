"use client"

import { useState, useRef, useEffect } from "react"
import { cn } from "@/lib/utils"
import { Topbar } from "@/components/layout/topbar"
import { api } from "@/lib/api"
import { useAppStore } from "@/store/use-app-store"

// ── Tipos con const objects (TypeScript skill) ─────────────────────────────

const FOCO = {
  GENERAL: "general",
  PRODUCTOS: "productos",
  EQUIPO: "equipo",
  PIPELINE: "pipeline",
} as const

type Foco = (typeof FOCO)[keyof typeof FOCO]

const ESTADO = {
  IDLE: "idle",
  GENERANDO: "generando",
  LISTO: "listo",
  REPRODUCIENDO: "reproduciendo",
  PAUSADO: "pausado",
} as const

type Estado = (typeof ESTADO)[keyof typeof ESTADO]

// ── Datos de focos ─────────────────────────────────────────────────────────

interface DatosFoco {
  id: Foco
  label: string
  descripcion: string
}

const FOCOS: DatosFoco[] = [
  { id: FOCO.GENERAL, label: "Resumen general", descripcion: "Vista completa del pipeline y KPIs clave" },
  { id: FOCO.PRODUCTOS, label: "Análisis de productos", descripcion: "Win rate y volumen por norma/producto" },
  { id: FOCO.EQUIPO, label: "Rendimiento del equipo", descripcion: "Rankings y oportunidades de mejora" },
  { id: FOCO.PIPELINE, label: "Estado del funnel", descripcion: "Etapas, riesgos y oportunidades activas" },
]

// ── Waveform animado ───────────────────────────────────────────────────────

function Waveform({ activo }: { activo: boolean }) {
  return (
    <div className="flex items-center justify-center gap-0.5 h-12">
      {Array.from({ length: 24 }).map((_, i) => (
        <div
          key={i}
          className={cn("w-1 rounded-full transition-all", activo ? "bg-sgs-rojo" : "bg-gray-300")}
          style={{
            height: activo ? `${20 + Math.sin(i * 0.8) * 16}px` : "6px",
            animation: activo ? "wave 1.2s ease-in-out infinite" : "none",
            animationDelay: `${i * 0.05}s`,
          }}
        />
      ))}
      <style>{`
        @keyframes wave {
          0%, 100% { transform: scaleY(1); }
          50% { transform: scaleY(1.8); }
        }
      `}</style>
    </div>
  )
}

function IconPlay() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5v14l11-7z" />
    </svg>
  )
}
function IconPause() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
    </svg>
  )
}
function IconStop() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M6 6h12v12H6z" />
    </svg>
  )
}

export default function PaginaVoice() {
  const iaConfig = useAppStore((s) => s.iaConfigs.voice)
  const [focoSeleccionado, setFocoSeleccionado] = useState<Foco>(FOCO.GENERAL)
  const [estado, setEstado] = useState<Estado>(ESTADO.IDLE)
  const [script, setScript] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [progreso, setProgreso] = useState(0)
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)

  useEffect(() => {
    return () => { window.speechSynthesis?.cancel() }
  }, [])

  async function generarScript() {
    setEstado(ESTADO.GENERANDO)
    setError(null)
    setScript(null)
    setProgreso(0)
    window.speechSynthesis?.cancel()

    try {
      const datos = await api.voice.briefing(focoSeleccionado, iaConfig)
      setScript(datos.script)
      setEstado(ESTADO.LISTO)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al generar el briefing")
      setEstado(ESTADO.IDLE)
    }
  }

  function reproducir() {
    if (!script || !window.speechSynthesis) return

    window.speechSynthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(script)
    utterance.lang = "es-ES"
    utterance.rate = 0.95
    utterance.pitch = 1
    utterance.volume = 1

    const voces = window.speechSynthesis.getVoices()
    const vozES = voces.find(
      (v) => v.lang.startsWith("es") && (v.name.includes("Google") || v.name.includes("Microsoft"))
    )
    if (vozES) utterance.voice = vozES

    utterance.onstart = () => setEstado(ESTADO.REPRODUCIENDO)
    utterance.onend = () => { setEstado(ESTADO.LISTO); setProgreso(0) }
    utterance.onerror = () => setEstado(ESTADO.LISTO)

    const palabrasTotales = script.split(" ").length
    let palabrasLeidas = 0
    utterance.onboundary = (e) => {
      if (e.name === "word") {
        palabrasLeidas++
        setProgreso(Math.round((palabrasLeidas / palabrasTotales) * 100))
      }
    }

    utteranceRef.current = utterance
    window.speechSynthesis.speak(utterance)
  }

  function pausar() {
    window.speechSynthesis?.pause()
    setEstado(ESTADO.PAUSADO)
  }

  function reanudar() {
    window.speechSynthesis?.resume()
    setEstado(ESTADO.REPRODUCIENDO)
  }

  function detener() {
    window.speechSynthesis?.cancel()
    setEstado(ESTADO.LISTO)
    setProgreso(0)
  }

  const palabras = script ? script.split(" ").length : 0
  const minutos = Math.round(palabras / 140)

  return (
    <>
      <Topbar titulo="Voice Studio" subtitulo="Briefings de voz generados con IC" />

      <main className="flex-1 p-2.5 md:p-3.5 space-y-6 w-full">
        {/* ── Selector de foco ── */}
        <div className="bg-white rounded-xl border border-zinc-200 p-5">
          <h2 className="text-sm font-semibold text-zinc-800 mb-4">Tipo de briefing</h2>
          <div className="grid grid-cols-2 gap-3">
            {FOCOS.map((f) => (
              <button
                key={f.id}
                onClick={() => { setFocoSeleccionado(f.id); setScript(null); setEstado(ESTADO.IDLE) }}
                className={cn(
                  "text-left px-4 py-3 rounded-lg border transition-all",
                  focoSeleccionado === f.id
                    ? "border-sgs-rojo bg-red-50"
                    : "border-zinc-200 hover:border-zinc-300"
                )}
              >
                <p className={cn(
                  "text-sm font-medium",
                  focoSeleccionado === f.id ? "text-sgs-rojo" : "text-zinc-800"
                )}>
                  {f.label}
                </p>
                <p className="text-xs text-zinc-400 mt-0.5">{f.descripcion}</p>
              </button>
            ))}
          </div>

          <button
            onClick={generarScript}
            disabled={estado === ESTADO.GENERANDO || estado === ESTADO.REPRODUCIENDO}
            className="mt-4 w-full py-2.5 rounded-lg text-sm font-medium text-white bg-sgs-rojo transition-opacity disabled:opacity-50"
          >
            {estado === ESTADO.GENERANDO ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Generando briefing…
              </span>
            ) : (
              "Generar briefing"
            )}
          </button>

          {error && (
            <p className="mt-3 text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
          )}
        </div>

        {/* ── Reproductor ── */}
        {script && (
          <div className="bg-white rounded-xl border border-zinc-200 p-5 space-y-5">
            <Waveform activo={estado === ESTADO.REPRODUCIENDO} />

            {progreso > 0 && (
              <div className="h-1 bg-zinc-100 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all bg-sgs-rojo"
                  style={{ width: `${progreso}%` }}
                />
              </div>
            )}

            <div className="flex items-center justify-center gap-3">
              {estado === ESTADO.LISTO && (
                <button
                  onClick={reproducir}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white bg-sgs-rojo"
                >
                  <IconPlay /> Reproducir
                </button>
              )}
              {estado === ESTADO.REPRODUCIENDO && (
                <>
                  <button
                    onClick={pausar}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium border border-zinc-300 text-zinc-700 hover:bg-zinc-50"
                  >
                    <IconPause /> Pausar
                  </button>
                  <button
                    onClick={detener}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium border border-zinc-300 text-zinc-700 hover:bg-zinc-50"
                  >
                    <IconStop /> Detener
                  </button>
                </>
              )}
              {estado === ESTADO.PAUSADO && (
                <>
                  <button
                    onClick={reanudar}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white bg-sgs-rojo"
                  >
                    <IconPlay /> Reanudar
                  </button>
                  <button
                    onClick={detener}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium border border-zinc-300 text-zinc-700 hover:bg-zinc-50"
                  >
                    <IconStop /> Detener
                  </button>
                </>
              )}
            </div>

            <p className="text-center text-xs text-zinc-400">
              {palabras} palabras · ~{minutos} min · Web Speech API · es-ES
            </p>
          </div>
        )}

        {/* ── Script generado ── */}
        {script && (
          <div className="bg-white rounded-xl border border-zinc-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-zinc-800">Script del briefing</h2>
              <button
                onClick={() => navigator.clipboard?.writeText(script)}
                className="text-xs text-zinc-400 hover:text-zinc-700 transition-colors"
              >
                Copiar texto
              </button>
            </div>
            <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-wrap">{script}</p>
          </div>
        )}
      </main>
    </>
  )
}
