"use client"

import NumberFlow, { type Format } from "@number-flow/react"
import { cn } from "@/lib/utils"

type AcentoColor = "rojo" | "verde" | "ambar" | "azul"

const COLORES_ACENTO: Record<AcentoColor, string> = {
  rojo:  "var(--color-sgs-rojo)",
  verde: "var(--color-sgs-verde)",
  ambar: "var(--color-sgs-ambar)",
  azul:  "var(--color-sgs-azul)",
}

interface KpiCardProps {
  etiqueta: string
  valor: string
  /** Valor numérico raw para animación con NumberFlow */
  valorRaw?: number
  /** Opciones de formato para NumberFlow */
  formato?: Format
  subtexto?: string
  acento?: AcentoColor
  className?: string
}

export function KpiCard({
  etiqueta,
  valor,
  valorRaw,
  formato,
  subtexto,
  acento = "rojo",
  className,
}: KpiCardProps) {
  return (
    <div
      className={cn(
        "glass-panel glass-border rounded-2xl p-5 relative overflow-hidden",
        className
      )}
    >
      <div
        className="absolute top-0 left-0 right-0 h-1.5 rounded-t-xl"
        style={{ backgroundColor: COLORES_ACENTO[acento] }}
      />
      <div
        className="absolute -top-12 -right-8 w-40 h-40 rounded-full blur-3xl opacity-35 pointer-events-none"
        style={{ backgroundColor: COLORES_ACENTO[acento] }}
      />

      <p className="text-xs font-medium surface-subtitle uppercase tracking-wide mt-1">
        {etiqueta}
      </p>

      {valorRaw !== undefined ? (
        <NumberFlow
          value={valorRaw}
          format={formato}
          className="text-3xl md:text-4xl font-black surface-title mt-2 tabular-nums leading-none drop-shadow-[0_1px_8px_rgba(0,0,0,0.35)]"
          animated
        />
      ) : (
        <p className="text-3xl md:text-4xl font-black surface-title mt-2 leading-none drop-shadow-[0_1px_8px_rgba(0,0,0,0.35)]">{valor}</p>
      )}

      {subtexto && (
        <p className="text-xs surface-subtitle mt-2">{subtexto}</p>
      )}
    </div>
  )
}
