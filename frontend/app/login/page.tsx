"use client"

import { useState } from "react"
import { api } from "@/lib/api"
import { useAppStore } from "@/store/use-app-store"

function normalizarRol(valor: string | null | undefined): "admin" | "manager" | "supervisor" | "comercial" {
  const rol = (valor ?? "").trim().toLowerCase()
  if (rol === "admin" || rol === "manager" || rol === "supervisor" || rol === "comercial") return rol
  return "comercial"
}

export default function PaginaLogin() {
  const [email, setEmail] = useState("")
  const [contrasena, setContrasena] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [cargando, setCargando] = useState(false)
  const { iniciarSesion } = useAppStore()
  function permisosPorRol(rol: "admin" | "manager" | "supervisor" | "comercial") {
    if (rol === "admin") {
      return {
        ver_equipo: true,
        ver_todos_pipeline: true,
        gestionar_usuarios: true,
        importar_datos: true,
        ver_informes_ejecutivos: true,
        gestionar_alertas: true,
      }
    }
    if (rol === "manager") {
      return {
        ver_equipo: true,
        ver_todos_pipeline: true,
        gestionar_usuarios: false,
        importar_datos: true,
        ver_informes_ejecutivos: true,
        gestionar_alertas: true,
      }
    }
    if (rol === "supervisor") {
      return {
        ver_equipo: true,
        ver_todos_pipeline: true,
        gestionar_usuarios: false,
        importar_datos: true,
        ver_informes_ejecutivos: true,
        gestionar_alertas: false,
      }
    }
    return {
      ver_equipo: false,
      ver_todos_pipeline: false,
      gestionar_usuarios: false,
      importar_datos: true,
      ver_informes_ejecutivos: false,
      gestionar_alertas: false,
    }
  }

  async function manejarLogin(e: React.FormEvent) {
    e.preventDefault()
    setCargando(true)
    setError(null)

    try {
      const respuesta = await api.auth.login(email, contrasena)
      // Guardar guardas de sesión antes de cualquier navegación.
      localStorage.setItem("access_token", respuesta.access_token)
      document.cookie = `sgs-auth=1; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`

      try {
        const perfil = await api.auth.perfil()
        iniciarSesion(respuesta.access_token, {
          usuario_id: perfil.usuario_id,
          email: perfil.email,
          nombre_completo: perfil.nombre_completo,
          rol: normalizarRol(perfil.rol),
          sbus_asignados: perfil.sbus_asignados,
          permisos: perfil.permisos,
        })
      } catch {
        // Fallback defensivo para no bloquear acceso si /auth/me falla puntualmente.
        iniciarSesion(respuesta.access_token, {
          usuario_id: "local-session",
          email,
          nombre_completo: email,
          rol: "comercial",
          sbus_asignados: [],
          permisos: permisosPorRol("comercial"),
        })
      }

      window.location.href = "/overview"
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión")
    } finally {
      setCargando(false)
    }
  }

  return (
    <div className="min-h-screen px-4 py-8 flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <span className="text-4xl font-black tracking-tight text-sgs-rojo">SGS</span>
          <p className="text-sm surface-subtitle mt-1">Inteligencia Comercial</p>
        </div>

        <div className="glass-panel glass-border rounded-2xl p-6 md:p-7">
          <h2 className="text-xl font-semibold surface-title mb-1">Iniciar sesión</h2>
          <p className="text-sm surface-subtitle mb-5">Accede con tu usuario corporativo</p>

          <form onSubmit={manejarLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium surface-subtitle mb-1.5">
                Correo electrónico
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="ui-input h-11 text-sm"
                placeholder="usuario@sgs.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium surface-subtitle mb-1.5">
                Contraseña
              </label>
              <input
                type="password"
                value={contrasena}
                onChange={(e) => setContrasena(e.target.value)}
                required
                className="ui-input h-11 text-sm"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <p className="text-sm surface-title bg-[rgba(192,0,26,0.14)] border border-[rgba(192,0,26,0.45)] px-3 py-2 rounded-lg">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={cargando}
              className="w-full h-11 ui-btn-primary text-sm transition-opacity disabled:opacity-60"
            >
              {cargando ? "Entrando..." : "Entrar"}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
