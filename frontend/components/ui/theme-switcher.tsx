"use client"

import { Laptop, Moon, Sun } from "lucide-react"
import { cn } from "@/lib/utils"
import { useTheme, type ThemeMode } from "@/hooks/use-theme"

const OPCIONES: Array<{ modo: ThemeMode; etiqueta: string; icono: typeof Sun }> = [
  { modo: "light", etiqueta: "Claro", icono: Sun },
  { modo: "dark", etiqueta: "Oscuro", icono: Moon },
  { modo: "system", etiqueta: "Sistema", icono: Laptop },
]

export function ThemeSwitcher() {
  const { modo, cambiarTema } = useTheme()

  return (
    <div className="hidden lg:flex items-center gap-1 p-1 rounded-xl glass-panel border glass-border">
      {OPCIONES.map(({ modo: opcionModo, etiqueta, icono: Icono }) => {
        const activa = modo === opcionModo
        return (
          <button
            key={opcionModo}
            onClick={() => cambiarTema(opcionModo)}
            className={cn(
              "inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all",
              activa
                ? "bg-[var(--color-card)] text-[var(--color-texto)] shadow-sm"
                : "text-[var(--color-texto2)] hover:text-[var(--color-texto)] hover:bg-[var(--color-card-soft)]",
            )}
            title={`Tema ${etiqueta.toLowerCase()}`}
          >
            <Icono size={13} />
            {etiqueta}
          </button>
        )
      })}
    </div>
  )
}
