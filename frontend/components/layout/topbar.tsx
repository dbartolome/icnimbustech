"use client"

import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, Bell, LogOut } from "lucide-react"
import { useAppStore } from "@/store/use-app-store"
import { api } from "@/lib/api"
import { HelpButton } from "@/components/ui/help-modal"
import { ThemeSwitcher } from "@/components/ui/theme-switcher"
import type { Alerta } from "@/types"

interface TopbarProps {
  titulo: string
  subtitulo?: string
}

export function Topbar({ titulo, subtitulo }: TopbarProps) {
  const { usuarioActual, cerrarSesion } = useAppStore()
  const router = useRouter()
  const { data: alertas = [] } = useQuery<Alerta[]>({
    queryKey: ["topbar-alertas"],
    queryFn: () => api.alertas.listar(false) as Promise<Alerta[]>,
    enabled: !!usuarioActual,
    refetchInterval: 30_000,
  })

  const alertasAbiertas = alertas.filter((a) => !a.resuelta)
  const totalAlertas = alertasAbiertas.length
  const hayCriticas = alertasAbiertas.some((a) => a.nivel === "critico")
  const hayNoCriticas = alertasAbiertas.some((a) => a.nivel !== "critico")

  const estiloAlertas = hayCriticas
    ? "chip-danger border border-white/15"
    : hayNoCriticas
      ? "chip-warn border border-white/15"
      : "chip-neutral border border-white/15"

  async function manejarLogout() {
    try { await api.auth.logout() } catch { /* continuar */ }
    cerrarSesion()
    router.push("/login")
  }

  return (
    <header className="relative mt-2 lg:mt-0 lg:sticky lg:top-0 z-10 mx-2 md:mx-1.5 glass-panel glass-border rounded-2xl px-2.5 py-3 md:px-3.5 md:py-3.5 flex flex-col sm:flex-row gap-2 sm:gap-3 sm:items-center sm:justify-between">
      <div>
        <h1 className="text-base md:text-lg font-semibold surface-title">{titulo}</h1>
        {subtitulo && <p className="text-xs surface-subtitle mt-0.5">{subtitulo}</p>}
      </div>

      <div className="flex w-full sm:w-auto items-center justify-end gap-2 sm:gap-3 flex-wrap">
        <ThemeSwitcher />

        <button
          onClick={() => {
            const ev = new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true })
            document.dispatchEvent(ev)
          }}
          className="hidden sm:flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border border-white/25 bg-[var(--color-card-soft-2)] surface-subtitle hover:text-[var(--color-texto)] transition-colors"
          title="Paleta de comandos"
        >
          <span>Buscar</span>
          <kbd className="inline-flex items-center gap-0.5 font-medium">⌘K</kbd>
        </button>

        <HelpButton />

        <button
          onClick={() => router.push("/alertas")}
          className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${estiloAlertas}`}
          title={totalAlertas > 0 ? `${totalAlertas} alerta(s) abierta(s)` : "Sin alertas activas"}
        >
          {hayCriticas
            ? <AlertTriangle size={12} />
            : <Bell size={12} />
          }
          <span className="hidden sm:inline">Alertas</span>
          {totalAlertas > 0 && (
            <span className="inline-flex items-center justify-center min-w-4 h-4 px-1 rounded-full chip-neutral text-[10px] font-bold">
              {totalAlertas}
            </span>
          )}
        </button>

        <span className="hidden md:inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded-full chip-success font-medium border border-white/15">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
          LIVE
        </span>

        {usuarioActual && (
          <div className="hidden md:flex items-center gap-2">
            <span className="text-xs surface-subtitle">{usuarioActual.email}</span>
            <button
              onClick={manejarLogout}
              className="flex items-center gap-1 text-xs surface-subtitle hover:text-[var(--color-texto)] transition-colors"
              title="Cerrar sesión"
            >
              <LogOut size={13} />
              Salir
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
