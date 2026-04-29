"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import {
  LayoutDashboard, GitMerge, TrendingUp, Users, Package, Building2,
  UserCircle, Target, Mic, FileText, Sparkles, Radio, BarChart3,
  Presentation, Settings, UserCog, Upload, type LucideIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { JobsIndicator } from "@/components/jobs-indicator"
import { useAppStore } from "@/store/use-app-store"

interface NavItem {
  href: string
  etiqueta: string
  icono: LucideIcon
  permiso?: "ver_equipo" | "gestionar_usuarios" | "ver_informes_ejecutivos" | "importar_datos"
  roles?: Array<"admin" | "manager" | "supervisor" | "comercial">
  hrefPorRol?: Partial<Record<"admin" | "manager" | "supervisor" | "comercial", string>>
}

interface NavSeccion {
  titulo: string
  items: NavItem[]
  roles?: Array<"admin" | "manager" | "supervisor" | "comercial">
}

const SECCIONES: NavSeccion[] = [
  {
    titulo: "Análisis",
    items: [
      { href: "/overview",  etiqueta: "Dashboard",  icono: LayoutDashboard },
      { href: "/pipeline",  etiqueta: "Pipeline",   icono: GitMerge },
      { href: "/forecast",  etiqueta: "Forecast",   icono: TrendingUp },
    ],
  },
  {
    titulo: "Comercial",
    items: [
      { href: "/perfil",     etiqueta: "Mi Perfil",     icono: UserCircle },
      {
        href: "/clientes",
        etiqueta: "Cuentas",
        icono: Building2,
        roles: ["admin", "manager", "supervisor", "comercial"],
        hrefPorRol: { admin: "/clientes", manager: "/clientes", supervisor: "/clientes", comercial: "/cuentas" },
      },
      { href: "/objetivos",  etiqueta: "Objetivos",     icono: Target },
      { href: "/productos",  etiqueta: "Productos",     icono: Package },
      { href: "/equipo",     etiqueta: "Equipo",        icono: Users, roles: ["admin", "manager", "supervisor"] },
      { href: "/notas",      etiqueta: "Notas de Voz",  icono: Mic },
      { href: "/documentos", etiqueta: "Documentos",    icono: FileText },
      { href: "/importacion", etiqueta: "Importación", icono: Upload, roles: ["comercial"] },
    ],
  },
  {
    titulo: "Inteligencia Comercial",
    roles: ["admin"],
    items: [
      { href: "/copilot",       etiqueta: "IC Copilot",       icono: Sparkles },
      { href: "/voice",         etiqueta: "Voice Studio",     icono: Radio },
      { href: "/informes",      etiqueta: "Informes PDF",     icono: BarChart3 },
      { href: "/deck",          etiqueta: "Deck Visita",      icono: Presentation },
      { href: "/configuracion", etiqueta: "Configuración IC", icono: Settings },
    ],
  },
  {
    titulo: "Administración",
    roles: ["admin", "manager", "supervisor"],
    items: [
      { href: "/admin/usuarios",    etiqueta: "Usuarios",       icono: UserCog,  permiso: "gestionar_usuarios" },
      {
        href: "/admin/importacion",
        etiqueta: "Importación",
        icono: Upload,
        permiso: "importar_datos",
        hrefPorRol: { admin: "/admin/importacion", manager: "/importacion", supervisor: "/importacion" },
      },
    ],
  },
]

const ROL_BADGE: Record<string, string> = {
  admin:     "bg-sgs-rojo text-white",
  manager:   "bg-amber-100 text-amber-800",
  supervisor: "bg-emerald-100 text-emerald-800",
  comercial: "bg-zinc-100 text-zinc-600",
}
const ROL_LABEL: Record<string, string> = {
  admin: "Admin", manager: "Manager", supervisor: "Supervisor", comercial: "Comercial",
}

function normalizarRol(valor: string | null | undefined): "admin" | "manager" | "supervisor" | "comercial" {
  const r = (valor ?? "").trim().toLowerCase()
  if (r === "admin" || r === "manager" || r === "supervisor" || r === "comercial") return r
  return "comercial"
}

export function Sidebar() {
  const rutaActual = usePathname()
  const sidebarAbierto = useAppStore((s) => s.sidebarAbierto)
  const cerrarSidebar = useAppStore((s) => s.cerrarSidebar)
  const usuarioActual = useAppStore((s) => s.usuarioActual)
  const can = useAppStore((s) => s.can)
  const [montado, setMontado] = useState(false)

  useEffect(() => { setMontado(true) }, [])

  // Cerrar al navegar en mobile (en desktop no tiene efecto, CSS lo mantiene visible)
  useEffect(() => { cerrarSidebar() }, [rutaActual]) // eslint-disable-line react-hooks/exhaustive-deps

  const rol = montado ? normalizarRol(usuarioActual?.rol) : "comercial"
  const puedeVer = (permiso?: NavItem["permiso"]) =>
    !montado || !permiso || can(permiso)
  const itemVisiblePorRol = (item: NavItem) =>
    !item.roles || item.roles.includes(rol)
  const seccionVisible = (seccion: NavSeccion) =>
    !seccion.roles || seccion.roles.includes(rol)

  return (
    <>
      {/* Backdrop mobile */}
      {sidebarAbierto && (
        <div
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          onClick={cerrarSidebar}
        />
      )}

      <aside
        className={cn(
          "fixed left-0 top-0 h-screen w-56 bg-white border-r border-zinc-200 flex flex-col",
          "z-50 lg:z-20 transition-transform duration-200 lg:translate-x-0",
          sidebarAbierto ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="px-5 py-4 border-b border-zinc-200">
          <span className="text-lg font-bold tracking-tight text-sgs-rojo">SGS</span>
          <span className="text-xs text-zinc-500 block leading-none mt-0.5">Inteligencia Comercial</span>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-3">
          {SECCIONES.map((seccion) => {
            if (!seccionVisible(seccion)) return null
            const itemsVisibles = seccion.items.filter(
              (item) => puedeVer(item.permiso) && itemVisiblePorRol(item),
            )
            if (!itemsVisibles.length) return null

            return (
              <div key={seccion.titulo} className="mb-4">
                <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-widest text-zinc-400">
                  {seccion.titulo}
                </p>
                <div className="space-y-0.5">
                  {itemsVisibles.map(({ href, etiqueta, icono: Icono, hrefPorRol }) => {
                    const hrefFinal = hrefPorRol?.[rol] ?? href
                    const activo = rutaActual === hrefFinal || rutaActual.startsWith(hrefFinal + "/")
                    return (
                      <Link
                        key={`${etiqueta}-${hrefFinal}`}
                        href={hrefFinal}
                        className={cn(
                          "flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors",
                          activo
                            ? "font-medium text-white bg-sgs-rojo"
                            : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900",
                        )}
                      >
                        <Icono size={15} strokeWidth={activo ? 2.5 : 1.75} className="shrink-0" />
                        {etiqueta}
                      </Link>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </nav>

        <div className="px-3 py-3 border-t border-zinc-200 space-y-2">
          <JobsIndicator />
          {montado && usuarioActual && (
            <div className="flex items-center gap-2 px-1">
              <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full", ROL_BADGE[rol])}>
                {ROL_LABEL[rol]}
              </span>
              <span className="text-xs text-zinc-500 truncate">
                {usuarioActual.nombre_completo || usuarioActual.email}
              </span>
            </div>
          )}
          <p className="text-xs text-zinc-400 px-1">v1.1.0 · SGS España</p>
        </div>
      </aside>
    </>
  )
}
