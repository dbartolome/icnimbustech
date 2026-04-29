"use client"

import { useCallback } from "react"
import { api } from "@/lib/api"
import { useJobsStore, type JobTipo } from "@/store/use-jobs-store"

const INTERVALO_MS = 2000
const ESTADOS_FINALES = new Set(["completado", "error"])
type EstadoDocumentoJob = Awaited<ReturnType<typeof api.documentosJobs.estado>>
type RespuestaInicioJob = {
  job_id: string | null
  estado: string
  [key: string]: unknown
}

/**
 * Hook para lanzar un job de generación de documento y hacer polling automático.
 * El progreso se refleja en el JobsStore (visible en el sidebar).
 */
export function useDocumentoJob() {
  const { addJob, updateJob } = useJobsStore()

  const lanzar = useCallback(async (
    tipo: JobTipo,
    lanzarFn: () => Promise<RespuestaInicioJob>,
    onCompletado?: (estadoFinal: EstadoDocumentoJob | RespuestaInicioJob) => void,
    onError?: (error: string) => void,
  ) => {
    const respuesta = await lanzarFn()

    // El backend puede devolver job_id=null cuando ya hay resultado reciente
    if (!respuesta.job_id) {
      onCompletado?.(respuesta)
      return
    }

    const job_id = respuesta.job_id

    addJob({
      jobId: job_id,
      tipo,
      titulo: "Iniciando…",
      estado: "pendiente",
      progreso: 0,
    })

    // Polling
    const intervalo = setInterval(async () => {
      try {
        const estado = await api.documentosJobs.estado(job_id)

        updateJob(job_id, {
          titulo: estado.titulo,
          estado: estado.estado,
          progreso: estado.progreso,
          pasoActual: estado.paso_actual,
          urlDescarga: estado.url_descarga,
          resultado: estado.resultado,
        })

        if (ESTADOS_FINALES.has(estado.estado)) {
          clearInterval(intervalo)
          if (estado.estado === "completado") {
            onCompletado?.(estado)
          } else {
            onError?.(estado.error ?? "Error desconocido")
          }
        }
      } catch {
        clearInterval(intervalo)
        updateJob(job_id, { estado: "error", progreso: 0, pasoActual: "Error de conexión" })
        onError?.("Error de conexión")
      }
    }, INTERVALO_MS)
  }, [addJob, updateJob])

  return { lanzar }
}
