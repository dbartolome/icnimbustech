"use client"

import { create } from "zustand"

export type JobTipo = "informe" | "deck" | "pdf" | "pptx" | "briefing" | "estudio_ia" | "investigacion"

export interface Job {
  jobId: string
  tipo: JobTipo
  titulo: string
  estado: string
  progreso: number
  pasoActual?: string
  urlDescarga?: string
  resultado?: unknown
}

interface JobsStore {
  jobs: Record<string, Job>
  addJob: (job: Job) => void
  updateJob: (jobId: string, update: Partial<Omit<Job, "jobId">>) => void
  removeJob: (jobId: string) => void
}

export const useJobsStore = create<JobsStore>()((set) => ({
  jobs: {},

  addJob: (job) =>
    set((s) => ({ jobs: { ...s.jobs, [job.jobId]: job } })),

  updateJob: (jobId, update) =>
    set((s) => {
      const existing = s.jobs[jobId]
      if (!existing) return s
      return { jobs: { ...s.jobs, [jobId]: { ...existing, ...update } } }
    }),

  removeJob: (jobId) =>
    set((s) => {
      const { [jobId]: eliminado, ...rest } = s.jobs
      void eliminado
      return { jobs: rest }
    }),
}))
