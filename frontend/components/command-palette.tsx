"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { Command } from "cmdk"
import {
  LayoutDashboard,
  GitMerge,
  TrendingUp,
  Users,
  Package,
  Building2,
  UserCircle,
  Mic,
  FileText,
  Sparkles,
  Radio,
  BarChart3,
  PresentationIcon,
  Settings,
  UserCog,
  Upload,
  Search,
  Target,
  type LucideIcon,
} from "lucide-react"
import { useAppStore } from "@/store/use-app-store"

type Rol = "admin" | "manager" | "supervisor" | "comercial"
type Grupo = "Análisis" | "Comercial" | "IC" | "Admin"
type Permiso = "ver_equipo" | "gestionar_usuarios" | "ver_informes_ejecutivos" | "importar_datos"

type NavItem = {
  href: string
  etiqueta: string
  icono: LucideIcon
  grupo: Grupo
  roles?: Rol[]
  permiso?: Permiso
  hrefPorRol?: Partial<Record<Rol, string>>
}

const NAVEGACION: NavItem[] = [
  { href: "/overview", etiqueta: "Dashboard", icono: LayoutDashboard, grupo: "Análisis" },
  { href: "/pipeline", etiqueta: "Pipeline", icono: GitMerge, grupo: "Análisis" },
  { href: "/forecast", etiqueta: "Forecast", icono: TrendingUp, grupo: "Análisis" },

  { href: "/perfil", etiqueta: "Mi Perfil", icono: UserCircle, grupo: "Comercial" },
  {
    href: "/clientes",
    etiqueta: "Cuentas",
    icono: Building2,
    grupo: "Comercial",
    roles: ["admin", "manager", "supervisor", "comercial"],
    hrefPorRol: { admin: "/clientes", manager: "/clientes", supervisor: "/clientes", comercial: "/cuentas" },
  },
  { href: "/objetivos", etiqueta: "Objetivos", icono: Target, grupo: "Comercial" },
  { href: "/productos", etiqueta: "Productos", icono: Package, grupo: "Comercial" },
  { href: "/equipo", etiqueta: "Equipo", icono: Users, grupo: "Comercial", roles: ["admin", "manager", "supervisor"] },
  { href: "/notas", etiqueta: "Notas de Voz", icono: Mic, grupo: "Comercial" },
  { href: "/documentos", etiqueta: "Documentos", icono: FileText, grupo: "Comercial" },
  { href: "/importacion", etiqueta: "Importación", icono: Upload, grupo: "Comercial", roles: ["comercial"] },

  { href: "/copilot", etiqueta: "IC Copilot", icono: Sparkles, grupo: "IC", roles: ["admin"] },
  { href: "/voice", etiqueta: "Voice Studio", icono: Radio, grupo: "IC", roles: ["admin"] },
  { href: "/informes", etiqueta: "Informes PDF", icono: BarChart3, grupo: "IC", roles: ["admin"] },
  { href: "/deck", etiqueta: "Deck Visita", icono: PresentationIcon, grupo: "IC", roles: ["admin"] },
  { href: "/configuracion", etiqueta: "Configuración IC", icono: Settings, grupo: "IC", roles: ["admin"] },

  { href: "/admin/usuarios", etiqueta: "Usuarios", icono: UserCog, grupo: "Admin", roles: ["admin"], permiso: "gestionar_usuarios" },
  {
    href: "/admin/importacion",
    etiqueta: "Importación",
    icono: Upload,
    grupo: "Admin",
    roles: ["admin", "manager", "supervisor"],
    permiso: "importar_datos",
    hrefPorRol: { admin: "/admin/importacion", manager: "/importacion", supervisor: "/importacion" },
  },
]

const GRUPOS = ["Análisis", "Comercial", "IC", "Admin"]

export function CommandPalette() {
  const [abierto, setAbierto] = useState(false)
  const router = useRouter()
  const usuarioActual = useAppStore((s) => s.usuarioActual)
  const can = useAppStore((s) => s.can)

  const rol = (usuarioActual?.rol ?? "comercial") as Rol
  const itemsVisibles = NAVEGACION.filter((item) => {
    if (item.roles && !item.roles.includes(rol)) return false
    if (item.permiso && !can(item.permiso)) return false
    return true
  }).map((item) => ({ ...item, href: item.hrefPorRol?.[rol] ?? item.href }))

  const toggle = useCallback(() => setAbierto((v) => !v), [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        toggle()
      }
    }
    document.addEventListener("keydown", handler)
    return () => document.removeEventListener("keydown", handler)
  }, [toggle])

  const navegar = (href: string) => {
    setAbierto(false)
    router.push(href)
  }

  if (!abierto) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]"
      onClick={() => setAbierto(false)}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 overlay-strong backdrop-blur-sm" />

      {/* Panel */}
      <div
        className="relative w-full max-w-lg mx-4 rounded-xl border border-zinc-200 bg-white shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <Command className="[&_[cmdk-input-wrapper]]:border-b [&_[cmdk-input-wrapper]]:border-zinc-100">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-100">
            <Search size={15} className="text-zinc-400 shrink-0" />
            <Command.Input
              placeholder="Navegar a..."
              className="flex-1 bg-transparent text-sm text-zinc-900 placeholder:text-zinc-400 outline-none"
              autoFocus
            />
            <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-zinc-200 bg-zinc-50 px-1.5 py-0.5 text-[10px] font-medium text-zinc-500">
              esc
            </kbd>
          </div>

          <Command.List className="max-h-72 overflow-y-auto py-2">
            <Command.Empty className="py-8 text-center text-sm text-zinc-400">
              Sin resultados
            </Command.Empty>

            {GRUPOS.map((grupo) => {
              const items = itemsVisibles.filter((n) => n.grupo === grupo)
              return (
                <Command.Group
                  key={grupo}
                  heading={grupo}
                  className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-zinc-400"
                >
                  {items.map((item) => {
                    const Icono = item.icono
                    return (
                      <Command.Item
                        key={item.href}
                        value={`${item.etiqueta} ${item.grupo}`}
                        onSelect={() => navegar(item.href)}
                        className="flex items-center gap-3 px-3 py-2 mx-1 rounded-lg text-sm text-zinc-700 cursor-pointer aria-selected:bg-zinc-100 aria-selected:text-zinc-900 transition-colors"
                      >
                        <Icono size={14} className="text-zinc-400 shrink-0" />
                        {item.etiqueta}
                      </Command.Item>
                    )
                  })}
                </Command.Group>
              )
            })}
          </Command.List>

          <div className="border-t border-zinc-100 px-3 py-2 flex gap-3 text-[10px] text-zinc-400">
            <span><kbd className="font-medium">↑↓</kbd> navegar</span>
            <span><kbd className="font-medium">↵</kbd> seleccionar</span>
            <span><kbd className="font-medium">esc</kbd> cerrar</span>
          </div>
        </Command>
      </div>
    </div>
  )
}
