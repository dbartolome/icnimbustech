"use client"

import { useState, useEffect, Suspense } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { useSearchParams } from "next/navigation"
import { cn } from "@/lib/utils"
import { Topbar } from "@/components/layout/topbar"
import { useJobsStore } from "@/store/use-jobs-store"
import { useAppStore } from "@/store/use-app-store"
import { obtenerApiBaseUrl } from "@/lib/api-base-url"

const API = obtenerApiBaseUrl()

// ── Tipos con const objects (TypeScript skill) ─────────────────────────────

const TIPO_DECK = {
  PRIMERA_VISITA: "primera_visita",
  SEGUIMIENTO_OFERTA: "seguimiento_oferta",
  UPSELLING: "upselling",
  PROPUESTA_TECNICA: "propuesta_tecnica",
} as const

type TipoDeck = (typeof TIPO_DECK)[keyof typeof TIPO_DECK]

const ESTADO_JOB = {
  PENDIENTE: "pendiente",
  GENERANDO_CONTENIDO: "generando_contenido",
  CONSTRUYENDO_SLIDES: "construyendo_slides",
  COMPLETADO: "completado",
  ERROR: "error",
} as const

type EstadoJob = (typeof ESTADO_JOB)[keyof typeof ESTADO_JOB]

// ── Interfaces ─────────────────────────────────────────────────────────────

interface JobStatus {
  job_id: string
  estado: EstadoJob
  progreso: number
  mensaje: string
  archivo: string | null
}

interface OpcionTipo {
  value: TipoDeck
  label: string
  descripcion: string
  icono: string
}

// ── Datos estáticos ────────────────────────────────────────────────────────

const TIPOS_DECK: OpcionTipo[] = [
  {
    value: TIPO_DECK.PRIMERA_VISITA,
    label: "Primera visita",
    descripcion: "Presentación completa de SGS, propuesta de valor y proceso de certificación.",
    icono: "◈",
  },
  {
    value: TIPO_DECK.SEGUIMIENTO_OFERTA,
    label: "Seguimiento de oferta",
    descripcion: "Recordatorio de la propuesta, respuesta a objeciones y cierre.",
    icono: "◉",
  },
  {
    value: TIPO_DECK.UPSELLING,
    label: "Upselling / Cross-selling",
    descripcion: "Nueva norma para cliente existente con condiciones especiales.",
    icono: "◆",
  },
  {
    value: TIPO_DECK.PROPUESTA_TECNICA,
    label: "Propuesta técnica",
    descripcion: "Detalle de la norma, proceso de auditoría, plazos e inversión.",
    icono: "◬",
  },
]

const NORMAS_SUGERIDAS = [
  "ISO 9001:2015",
  "ISO 14001:2015",
  "ISO 45001:2018",
  "ISO 27001:2022",
  "ISO 50001:2018",
  "ISO 22000:2018",
  "IATF 16949:2016",
  "EN 9100:2018",
]

const SECTORES = [
  "Industria manufacturera",
  "Alimentación y bebidas",
  "Automoción",
  "Construcción",
  "Energía",
  "Farmacéutico",
  "Logística y transporte",
  "Servicios",
  "Tecnología",
  "Otro",
]

// ── Helpers ────────────────────────────────────────────────────────────────

function getHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}` }
}

// ── Subcomponentes ─────────────────────────────────────────────────────────

const COLOR_BARRA: Record<EstadoJob, string> = {
  pendiente: "bg-zinc-400",
  generando_contenido: "bg-blue-500",
  construyendo_slides: "bg-amber-500",
  completado: "bg-green-500",
  error: "bg-red-500",
}

interface BarraProgresoProps {
  progreso: number
  estado: EstadoJob
}

function BarraProgreso({ progreso, estado }: BarraProgresoProps) {
  return (
    <div className="h-2 bg-zinc-100 rounded-full overflow-hidden">
      <div
        className={cn("h-full rounded-full transition-all duration-700", COLOR_BARRA[estado])}
        style={{ width: `${progreso}%` }}
      />
    </div>
  )
}

// ── Página principal ───────────────────────────────────────────────────────

function PaginaDeckInterna() {
  const searchParams = useSearchParams()
  const { addJob, updateJob } = useJobsStore()
  const iaConfig = useAppStore((s) => s.iaConfigs.decks)

  const [tipo, setTipo] = useState<TipoDeck>(TIPO_DECK.PRIMERA_VISITA)
  const [empresa, setEmpresa] = useState("")
  const [sector, setSector] = useState("")
  const [norma, setNorma] = useState("")
  const [objetivo, setObjetivo] = useState("")
  const [notas, setNotas] = useState("")
  const [numSlides, setNumSlides] = useState(10)
  const [jobId, setJobId] = useState<string | null>(null)

  // Pre-rellenar desde URL params (flujo Mis Cuentas → Deck)
  useEffect(() => {
    const empresaParam = searchParams.get("empresa")
    const sectorParam = searchParams.get("sector")
    if (empresaParam) setEmpresa(empresaParam)
    if (sectorParam) setSector(sectorParam)
  }, [searchParams])

  const { mutate: iniciarGeneracion, isPending } = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API}/decks/generar`, {
        method: "POST",
        headers: { ...getHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({
          empresa,
          sector,
          norma,
          tipo,
          objetivo_visita: objetivo,
          notas_adicionales: notas,
          num_slides: numSlides,
          proveedor: iaConfig.proveedor,
          ollama_url: iaConfig.ollamaUrl,
          ollama_modelo: iaConfig.ollamaModelo,
        }),
      })
      if (!res.ok) throw new Error("Error al iniciar la generación")
      return res.json()
    },
    onSuccess: (data) => {
      setJobId(data.job_id)
      addJob({
        jobId: data.job_id,
        tipo: "deck",
        titulo: `Deck · ${empresa}`,
        estado: "pendiente",
        progreso: 0,
      })
    },
  })

  const { data: jobStatus } = useQuery<JobStatus>({
    queryKey: ["deck-status", jobId],
    queryFn: async () => {
      const res = await fetch(`${API}/decks/status/${jobId}`, { headers: getHeaders() })
      if (!res.ok) throw new Error("Error consultando estado")
      return res.json()
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      const estado = query.state.data?.estado
      if (!estado || estado === ESTADO_JOB.COMPLETADO || estado === ESTADO_JOB.ERROR) return false
      return 2000
    },
    select: (data) => {
      if (jobId) updateJob(jobId, { estado: data.estado, progreso: data.progreso })
      return data
    },
  })

  function descargar() {
    fetch(`${API}/decks/download/${jobId}`, { headers: getHeaders() })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `deck_${empresa.replace(/\s+/g, "_")}.pptx`
        a.click()
        URL.revokeObjectURL(url)
      })
  }

  const generando = jobStatus && jobStatus.estado !== ESTADO_JOB.COMPLETADO && jobStatus.estado !== ESTADO_JOB.ERROR
  const completado = jobStatus?.estado === ESTADO_JOB.COMPLETADO
  const error = jobStatus?.estado === ESTADO_JOB.ERROR

  return (
    <>
      <Topbar titulo="Deck de Visita" subtitulo="Genera presentaciones PowerPoint con IC para tus visitas comerciales" />

      <main className="flex-1 p-2.5 md:p-3.5">
        <div className="w-full space-y-6">

          {/* ── Estado del job activo ── */}
          {jobId && jobStatus && (
            <div className="bg-white rounded-xl border border-zinc-200 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-zinc-800">
                  {completado ? "✅ Presentación lista" : error ? "❌ Error en la generación" : "⚙️ Generando presentación..."}
                </h2>
                {(completado || error) && (
                  <button
                    onClick={() => setJobId(null)}
                    className="text-xs text-zinc-500 hover:text-zinc-800 underline"
                  >
                    Nueva presentación
                  </button>
                )}
              </div>

              <BarraProgreso progreso={jobStatus.progreso} estado={jobStatus.estado} />

              <p className="text-sm text-zinc-600">{jobStatus.mensaje}</p>

              {generando && (
                <div className="flex items-center gap-2 text-xs text-zinc-400">
                  <span className="animate-spin">◌</span>
                  <span>Esto puede tardar 20–40 segundos...</span>
                </div>
              )}

              {completado && (
                <button
                  onClick={descargar}
                  className="w-full py-3 rounded-lg text-sm font-semibold text-white bg-sgs-rojo transition-colors"
                >
                  ⬇ Descargar presentación .pptx
                </button>
              )}

              {error && (
                <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">
                  {jobStatus.mensaje}
                </p>
              )}
            </div>
          )}

          {/* ── Formulario ── */}
          {!jobId && (
            <>
              {/* Selector de tipo */}
              <div className="bg-white rounded-xl border border-zinc-200 p-5">
                <h2 className="text-sm font-semibold text-zinc-800 mb-4">Tipo de presentación</h2>
                <div className="grid grid-cols-2 gap-3">
                  {TIPOS_DECK.map((t) => (
                    <button
                      key={t.value}
                      onClick={() => setTipo(t.value)}
                      className={cn(
                        "text-left p-4 rounded-lg border transition-all",
                        tipo === t.value ? "border-sgs-rojo bg-red-50" : "border-zinc-200 hover:border-zinc-300"
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-lg">{t.icono}</span>
                        <span className={cn(
                          "text-sm font-semibold",
                          tipo === t.value ? "text-sgs-rojo" : "text-zinc-800"
                        )}>
                          {t.label}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-500 leading-relaxed">{t.descripcion}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Datos de la visita */}
              <div className="bg-white rounded-xl border border-zinc-200 p-5">
                <h2 className="text-sm font-semibold text-zinc-800 mb-4">Datos de la visita</h2>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-zinc-600 mb-1.5">
                        Empresa cliente *
                      </label>
                      <input
                        type="text"
                        value={empresa}
                        onChange={(e) => setEmpresa(e.target.value)}
                        placeholder="Ej: Aceros Bilbao S.A."
                        className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-zinc-600 mb-1.5">
                        Sector *
                      </label>
                      <select
                        value={sector}
                        onChange={(e) => setSector(e.target.value)}
                        className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
                      >
                        <option value="">Seleccionar sector...</option>
                        {SECTORES.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-zinc-600 mb-1.5">
                      Norma / Certificación *
                    </label>
                    <input
                      type="text"
                      value={norma}
                      onChange={(e) => setNorma(e.target.value)}
                      placeholder="Ej: ISO 9001:2015"
                      className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
                    />
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {NORMAS_SUGERIDAS.map((n) => (
                        <button
                          key={n}
                          onClick={() => setNorma(n)}
                          className={cn(
                            "text-xs px-2 py-1 rounded-md border transition-colors",
                            norma === n
                              ? "border-sgs-rojo bg-red-50 text-sgs-rojo"
                              : "border-zinc-200 text-zinc-500 hover:border-zinc-300"
                          )}
                        >
                          {n}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-zinc-600 mb-1.5">
                      Objetivo de la visita *
                    </label>
                    <textarea
                      value={objetivo}
                      onChange={(e) => setObjetivo(e.target.value)}
                      placeholder="Ej: Presentar SGS y explorar necesidades de certificación ISO 9001 para su planta de producción en Bilbao. El contacto es el Director de Calidad."
                      rows={3}
                      className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent resize-none"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-zinc-600 mb-1.5">
                        Notas adicionales
                      </label>
                      <textarea
                        value={notas}
                        onChange={(e) => setNotas(e.target.value)}
                        placeholder="Contexto extra, objeciones conocidas, histórico con el cliente..."
                        rows={3}
                        className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent resize-none"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-zinc-600 mb-1.5">
                        Número de slides: <span className="font-semibold text-zinc-800">{numSlides}</span>
                      </label>
                      <input
                        type="range"
                        min={6}
                        max={15}
                        value={numSlides}
                        onChange={(e) => setNumSlides(Number(e.target.value))}
                        className="w-full mt-2"
                      />
                      <div className="flex justify-between text-xs text-zinc-400 mt-1">
                        <span>6 (conciso)</span>
                        <span>15 (completo)</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <button
                onClick={() => iniciarGeneracion()}
                disabled={isPending || !empresa.trim() || !sector || !norma.trim() || !objetivo.trim()}
                className="w-full py-3.5 rounded-xl text-sm font-semibold text-white bg-sgs-rojo transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isPending ? "Iniciando..." : "✦  Generar presentación con IC"}
              </button>
            </>
          )}
        </div>
      </main>
    </>
  )
}

export default function PaginaDeck() {
  return (
    <Suspense>
      <PaginaDeckInterna />
    </Suspense>
  )
}
