"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { IaConfig, IaConfigs, ServicioIa, PermisosUsuario, UsuarioActual } from "@/types"

const PERMISOS_POR_ROL: Record<string, Partial<PermisosUsuario>> = {
  admin: {
    ver_equipo: true, ver_todos_pipeline: true, gestionar_usuarios: true,
    importar_datos: true, ver_informes_ejecutivos: true, gestionar_alertas: true,
  },
  manager: {
    ver_equipo: true, ver_todos_pipeline: true, gestionar_usuarios: false,
    importar_datos: true, ver_informes_ejecutivos: true, gestionar_alertas: false,
  },
  supervisor: {
    ver_equipo: true, ver_todos_pipeline: true, gestionar_usuarios: false,
    importar_datos: true, ver_informes_ejecutivos: true, gestionar_alertas: false,
  },
  comercial: {
    ver_equipo: false, ver_todos_pipeline: false, gestionar_usuarios: false,
    importar_datos: true, ver_informes_ejecutivos: false, gestionar_alertas: false,
  },
}

const IA_CONFIG_BASE: IaConfig = {
  proveedor: "ollama",
  ollamaUrl: process.env.NEXT_PUBLIC_OLLAMA_URL ?? "",
  ollamaModelo: process.env.NEXT_PUBLIC_OLLAMA_MODEL ?? "llama3.2:3b",
}

const IA_CONFIGS_DEFECTO: IaConfigs = {
  copilot:      { ...IA_CONFIG_BASE },
  voice:        { ...IA_CONFIG_BASE },
  informes:     { ...IA_CONFIG_BASE },
  decks:        { ...IA_CONFIG_BASE },
  cross_selling: { ...IA_CONFIG_BASE },
  importacion:  { ...IA_CONFIG_BASE },
}

interface AppStore {
  usuarioActual: UsuarioActual | null
  accessToken: string | null
  iaConfigs: IaConfigs
  sidebarAbierto: boolean
  iniciarSesion: (token: string, usuario: UsuarioActual) => void
  cerrarSesion: () => void
  setIaConfig: (servicio: ServicioIa, config: Partial<IaConfig>) => void
  toggleSidebar: () => void
  cerrarSidebar: () => void
  isAdmin: () => boolean
  isManager: () => boolean
  can: (permiso: keyof PermisosUsuario) => boolean
}

export const useAppStore = create<AppStore>()(
  persist(
    (set, get) => ({
      usuarioActual: null,
      accessToken: null,
      iaConfigs: IA_CONFIGS_DEFECTO,
      sidebarAbierto: false,
      toggleSidebar: () => set((s) => ({ sidebarAbierto: !s.sidebarAbierto })),
      cerrarSidebar: () => set({ sidebarAbierto: false }),

      iniciarSesion: (token, usuario) => {
        localStorage.setItem("access_token", token)
        document.cookie = `sgs-auth=1; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`
        set({ accessToken: token, usuarioActual: usuario })
      },

      cerrarSesion: () => {
        localStorage.removeItem("access_token")
        document.cookie = "sgs-auth=; path=/; max-age=0"
        set({ accessToken: null, usuarioActual: null })
      },

      setIaConfig: (servicio, config) =>
        set((s) => ({
          iaConfigs: {
            ...s.iaConfigs,
            [servicio]: { ...s.iaConfigs[servicio], ...config },
          },
        })),

      isAdmin: () => get().usuarioActual?.rol === "admin",

      isManager: () => {
        const rol = get().usuarioActual?.rol
        return rol === "admin" || rol === "manager" || rol === "supervisor"
      },

      can: (permiso) => {
        const u = get().usuarioActual
        if (!u) return false
        const rol = (u.rol ?? "comercial") as keyof typeof PERMISOS_POR_ROL
        return PERMISOS_POR_ROL[rol]?.[permiso] ?? false
      },
    }),
    { name: "sgs-sesion" }
  )
)
