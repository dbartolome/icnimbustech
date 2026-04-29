"use client"

import { useState } from "react"
import type React from "react"
import { useRouter } from "next/navigation"
import { Settings, X, BarChart3, PresentationIcon, FileText, Mic, Sparkles, Search } from "lucide-react"
import { cn } from "@/lib/utils"
import { useJobsStore, type Job } from "@/store/use-jobs-store"

const ESTADO_COLOR: Record<string, string> = {
  completado: "text-emerald-700",
  error: "text-red-600",
  generando: "text-blue-600",
  analizando: "text-violet-600",
  investigando: "text-blue-600",
  generando_contenido: "text-blue-600",
  construyendo_slides: "text-amber-600",
  pendiente: "text-zinc-500",
}

const TIPO_ICONO: Record<string, React.ReactNode> = {
  informe: <BarChart3 size={14} className="shrink-0" />,
  deck: <PresentationIcon size={14} className="shrink-0" />,
  pdf: <FileText size={14} className="shrink-0" />,
  pptx: <PresentationIcon size={14} className="shrink-0" />,
  briefing: <Mic size={14} className="shrink-0" />,
  estudio_ia: <Sparkles size={14} className="shrink-0" />,
  investigacion: <Search size={14} className="shrink-0" />,
}

function FilaJob({ job, onEliminar }: { job: Job; onEliminar: () => void }) {
  const router = useRouter()
  const activo = job.estado !== "completado" && job.estado !== "error"

  function irAlModulo() {
    router.push(job.tipo === "informe" ? "/informes" : "/deck")
  }

  return (
    <div className="px-3 py-2.5 hover:bg-zinc-50 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <button onClick={irAlModulo} className="flex items-center gap-1.5 min-w-0 text-left">
          <span className="text-zinc-400">{TIPO_ICONO[job.tipo]}</span>
          <span className="text-xs font-medium text-zinc-800 truncate">{job.titulo}</span>
        </button>
        <button
          onClick={onEliminar}
          className="text-zinc-300 hover:text-zinc-600 shrink-0"
        >
          <X size={12} />
        </button>
      </div>

      <div className="mt-1.5 flex items-center gap-2">
        <div className="flex-1 h-1 bg-zinc-100 rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              job.estado === "completado"
                ? "bg-emerald-500"
                : job.estado === "error"
                ? "bg-red-500"
                : "bg-sgs-rojo",
            )}
            style={{ width: `${job.progreso}%` }}
          />
        </div>
        <span className={cn("text-[10px] font-medium shrink-0", ESTADO_COLOR[job.estado] ?? "text-zinc-500")}>
          {job.progreso}%
        </span>
      </div>

      {(activo || job.estado === "error") && job.pasoActual && (
        <div className="flex items-center gap-1 mt-1">
          {activo ? (
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse shrink-0" />
          ) : (
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
          )}
          <span className={cn("text-[10px] truncate", activo ? "text-zinc-400" : "text-red-500")}>
            {job.pasoActual}
          </span>
        </div>
      )}
    </div>
  )
}

export function JobsIndicator() {
  const { jobs, removeJob } = useJobsStore()
  const [abierto, setAbierto] = useState(false)

  const lista = Object.values(jobs)
  const activos = lista.filter((j) => j.estado !== "completado" && j.estado !== "error")
  const hayJobs = lista.length > 0

  if (!hayJobs) return null

  return (
    <div className="relative">
      {/* Botón trigger */}
      <button
        onClick={() => setAbierto(!abierto)}
        className={cn(
          "w-full flex items-center gap-2 px-3 py-2 rounded-md text-xs transition-colors",
          activos.length > 0
            ? "bg-blue-50 text-blue-700 hover:bg-blue-100"
            : "bg-zinc-50 text-zinc-600 hover:bg-zinc-100",
        )}
      >
        <span className="relative shrink-0">
          <Settings size={14} className={activos.length > 0 ? "animate-spin" : ""} style={{ animationDuration: "3s" }} />
          {activos.length > 0 && (
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-sgs-rojo rounded-full animate-ping" />
          )}
        </span>
        <span className="truncate">
          {activos.length > 0
            ? `${activos.length} generación${activos.length > 1 ? "es" : ""} activa${activos.length > 1 ? "s" : ""}`
            : `${lista.length} job${lista.length > 1 ? "s" : ""} completado${lista.length > 1 ? "s" : ""}`}
        </span>
      </button>

      {/* Panel desplegable — hacia arriba */}
      {abierto && (
        <div className="absolute bottom-full left-0 right-0 mb-1 bg-white border border-zinc-200 rounded-xl shadow-lg overflow-hidden z-50">
          <div className="px-3 py-2 border-b border-zinc-100 flex items-center justify-between">
            <p className="text-xs font-semibold text-zinc-700">Generaciones</p>
            <button onClick={() => setAbierto(false)} className="text-zinc-400 hover:text-zinc-700">
              <X size={13} />
            </button>
          </div>
          <div className="max-h-60 overflow-y-auto divide-y divide-zinc-50">
            {lista.map((job) => (
              <FilaJob key={job.jobId} job={job} onEliminar={() => removeJob(job.jobId)} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
