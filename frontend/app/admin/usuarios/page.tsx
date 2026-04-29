"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import { Topbar } from "@/components/layout/topbar"
import { RoleGuard } from "@/components/role-guard"
import type { UsuarioRead } from "@/types"

// =============================================================================
// Const types
// =============================================================================

const ROL_COLOR: Record<string, string> = {
  admin:     "text-red-700 bg-red-50",
  manager:   "text-amber-700 bg-amber-50",
  supervisor: "text-emerald-700 bg-emerald-50",
  comercial: "text-zinc-600 bg-zinc-100",
}

const ROL_LABEL: Record<string, string> = {
  admin:     "Admin",
  manager:   "Manager",
  supervisor: "Supervisor",
  comercial: "Comercial",
}

// =============================================================================
// Modal de crear / editar usuario
// =============================================================================

interface ModalUsuarioProps {
  usuario?: UsuarioRead
  onCerrar: () => void
  onGuardado: () => void
}

function ModalUsuario({ usuario, onCerrar, onGuardado }: ModalUsuarioProps) {
  const esEdicion = !!usuario
  const [email, setEmail] = useState(usuario?.email ?? "")
  const [nombre, setNombre] = useState(usuario?.nombre_completo ?? "")
  const [contrasena, setContrasena] = useState("")
  const [rol, setRol] = useState<"admin" | "manager" | "supervisor" | "comercial">(usuario?.rol ?? "comercial")
  const [nombreCsv, setNombreCsv] = useState(usuario?.nombre_csv ?? "")
  const [motivo, setMotivo] = useState("")
  const [error, setError] = useState("")

  const mutacion = useMutation({
    mutationFn: () => {
      if (esEdicion) {
        return api.usuarios.actualizar(usuario!.id, {
          nombre_completo: nombre,
          rol,
          nombre_csv: nombreCsv || undefined,
          activo: true,
          motivo_cambio_rol: motivo || undefined,
        })
      }
      return api.usuarios.crear({
        email,
        nombre_completo: nombre,
        contrasena,
        rol,
        nombre_csv: nombreCsv || undefined,
      })
    },
    onSuccess: () => {
      onGuardado()
      onCerrar()
    },
    onError: (e: Error) => setError(e.message),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overlay-strong">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-900">
            {esEdicion ? "Editar usuario" : "Nuevo usuario"}
          </h2>
          <button onClick={onCerrar} className="text-zinc-400 hover:text-zinc-700">✕</button>
        </div>

        <div className="space-y-3">
          {!esEdicion && (
            <div>
              <label className="block text-xs font-medium text-zinc-600 mb-1">Email *</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1">Nombre completo *</label>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
            />
          </div>

          {!esEdicion && (
            <div>
              <label className="block text-xs font-medium text-zinc-600 mb-1">Contraseña *</label>
              <input
                type="password"
                value={contrasena}
                onChange={(e) => setContrasena(e.target.value)}
                className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1">Rol *</label>
            <select
              value={rol}
              onChange={(e) => setRol(e.target.value as typeof rol)}
              className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
            >
              <option value="comercial">Comercial</option>
              <option value="supervisor">Supervisor</option>
              <option value="manager">Manager</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1">
              Nombre en CSV <span className="text-zinc-400 font-normal">(Opportunity Owner de Salesforce)</span>
            </label>
            <input
              type="text"
              value={nombreCsv}
              onChange={(e) => setNombreCsv(e.target.value)}
              placeholder="Ej: García López, María"
              className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
            />
          </div>

          {esEdicion && rol !== usuario?.rol && (
            <div>
              <label className="block text-xs font-medium text-zinc-600 mb-1">
                Motivo del cambio de rol
              </label>
              <input
                type="text"
                value={motivo}
                onChange={(e) => setMotivo(e.target.value)}
                placeholder="Ej: Promoción a manager del equipo Norte"
                className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
              />
            </div>
          )}
        </div>

        {error && (
          <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
        )}

        <div className="flex gap-2 pt-2">
          <button
            onClick={onCerrar}
            className="flex-1 py-2 text-sm border border-zinc-200 rounded-lg text-zinc-600 hover:bg-zinc-50"
          >
            Cancelar
          </button>
          <button
            onClick={() => mutacion.mutate()}
            disabled={mutacion.isPending || !nombre.trim() || (!esEdicion && (!email.trim() || !contrasena.trim()))}
            className="flex-1 py-2 text-sm font-medium text-white bg-sgs-rojo rounded-lg disabled:opacity-40"
          >
            {mutacion.isPending ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Fila de usuario
// =============================================================================

function FilaUsuario({
  usuario,
  onEditar,
  onEliminar,
}: {
  usuario: UsuarioRead
  onEditar: () => void
  onEliminar: () => void
}) {
  return (
    <tr className="border-b border-zinc-100 hover:bg-zinc-50 transition-colors">
      <td className="px-4 py-3">
        <div>
          <p className="text-sm font-medium text-zinc-900">{usuario.nombre_completo}</p>
          <p className="text-xs text-zinc-500">{usuario.email}</p>
        </div>
      </td>
      <td className="px-4 py-3">
        <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full", ROL_COLOR[usuario.rol])}>
          {ROL_LABEL[usuario.rol]}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-zinc-500">
        {usuario.nombre_csv ?? <span className="text-zinc-300">—</span>}
      </td>
      <td className="px-4 py-3 text-xs text-zinc-500">
        {usuario.sbus_asignados.length > 0
          ? usuario.sbus_asignados.join(", ")
          : <span className="text-zinc-300">—</span>}
      </td>
      <td className="px-4 py-3">
        <span className={cn(
          "text-[10px] font-medium px-2 py-0.5 rounded-full",
          usuario.activo ? "text-emerald-700 bg-emerald-50" : "text-zinc-500 bg-zinc-100"
        )}>
          {usuario.activo ? "Activo" : "Inactivo"}
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2 justify-end">
          <button
            onClick={onEditar}
            className="text-xs text-zinc-600 border border-zinc-200 px-2 py-1 rounded-lg hover:bg-zinc-50"
          >
            Editar
          </button>
          <button
            onClick={onEliminar}
            className="text-xs text-red-500 hover:text-red-700"
            title="Eliminar"
          >
            ✕
          </button>
        </div>
      </td>
    </tr>
  )
}

// =============================================================================
// Página principal
// =============================================================================

function ContenidoAdminUsuarios() {
  const [busqueda, setBusqueda] = useState("")
  const [modalAbierto, setModalAbierto] = useState(false)
  const [usuarioEditando, setUsuarioEditando] = useState<UsuarioRead | undefined>()
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery<{ total: number; datos: UsuarioRead[] }>({
    queryKey: ["usuarios-admin", busqueda],
    queryFn: () =>
      api.usuarios.listar({ busqueda: busqueda || undefined }) as Promise<{
        total: number
        datos: UsuarioRead[]
      }>,
  })

  const mutEliminar = useMutation({
    mutationFn: (id: string) => api.usuarios.eliminar(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["usuarios-admin"] }),
  })

  function abrirCrear() {
    setUsuarioEditando(undefined)
    setModalAbierto(true)
  }

  function abrirEditar(usuario: UsuarioRead) {
    setUsuarioEditando(usuario)
    setModalAbierto(true)
  }

  return (
    <>
      <Topbar
        titulo="Gestión de usuarios"
        subtitulo={data ? `${data.total} usuarios registrados` : "Administración de accesos y roles"}
      />
      <div className="flex-1 flex flex-col">
      {/* Header */}
      <header className="px-6 py-5 border-b border-zinc-200 bg-white">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-zinc-900">Operaciones de usuarios</h2>
            <p className="text-sm text-zinc-500 mt-0.5">
              Crear, editar rol y auditar activación.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative w-56">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 text-sm">◎</span>
              <input
                type="text"
                placeholder="Buscar usuario…"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                className="w-full pl-8 pr-3 py-2 text-sm border border-zinc-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
              />
            </div>
            <button
              onClick={abrirCrear}
              className="px-4 py-2 text-sm font-medium text-white bg-sgs-rojo rounded-lg hover:opacity-90 transition-opacity"
            >
              + Nuevo usuario
            </button>
          </div>
        </div>
      </header>

      {/* Tabla */}
      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="h-8 w-8 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
          </div>
        ) : !data?.datos.length ? (
          <div className="flex flex-col items-center justify-center h-64 gap-2">
            <span className="text-3xl text-zinc-300">◯</span>
            <p className="text-sm text-zinc-500">
              {busqueda ? "Sin resultados para tu búsqueda." : "No hay usuarios registrados."}
            </p>
          </div>
        ) : (
          <table className="w-full text-left">
            <thead className="sticky top-0 bg-zinc-50 border-b border-zinc-200 z-10">
              <tr>
                <th className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Usuario</th>
                <th className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Rol</th>
                <th className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Nombre CSV</th>
                <th className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">SBUs</th>
                <th className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Estado</th>
                <th className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white">
              {data.datos.map((usuario) => (
                <FilaUsuario
                  key={usuario.id}
                  usuario={usuario}
                  onEditar={() => abrirEditar(usuario)}
                  onEliminar={() => {
                    toast.warning(`¿Eliminar a ${usuario.nombre_completo}?`, {
                      action: {
                        label: "Eliminar",
                        onClick: () => mutEliminar.mutate(usuario.id),
                      },
                      cancel: { label: "Cancelar", onClick: () => {} },
                      duration: 8000,
                    })
                  }}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal */}
      {modalAbierto && (
        <ModalUsuario
          usuario={usuarioEditando}
          onCerrar={() => setModalAbierto(false)}
          onGuardado={() => queryClient.invalidateQueries({ queryKey: ["usuarios-admin"] })}
        />
      )}
      </div>
    </>
  )
}

export default function AdminUsuariosPage() {
  return (
    <RoleGuard permiso="gestionar_usuarios">
      <ContenidoAdminUsuarios />
    </RoleGuard>
  )
}
