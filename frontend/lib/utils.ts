import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Formatea importes monetarios en euros con locale español
export function formatearEuros(valor: number): string {
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(valor)
}

// Formatea porcentajes
export function formatearPorcentaje(valor: number): string {
  return `${Number(valor).toFixed(1)}%`
}

// Color semafórico para win rate
export function colorWinRate(winRate: number): string {
  if (winRate >= 90) return "text-green-700"
  if (winRate >= 70) return "text-yellow-700"
  return "text-red-700"
}

// Etiqueta legible de etapa del pipeline
export const ETIQUETAS_ETAPA: Record<string, string> = {
  estimation_sent:       "Estimación enviada",
  technically_approved:  "Aprobado técnicamente",
  in_progress:           "En progreso",
  discover:              "Discover",
  contract_offer_sent:   "Contrato enviado",
  propose:               "Propuesta",
  estimation_accepted:   "Estimación aceptada",
  negotiate:             "Negociación",
  closed_won:            "Cerrado ganado",
  closed_lost:           "Cerrado perdido",
  closed_withdrawn:      "Retirado",
}
