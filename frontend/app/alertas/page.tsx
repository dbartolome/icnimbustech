"use client"

import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Topbar } from "@/components/layout/topbar"
import { api } from "@/lib/api"
import { useAppStore } from "@/store/use-app-store"
import type { Alerta } from "@/types"

// ── Badge de nivel ──────────────────────────────────────────────────────────

function BadgeNivel({ nivel }: { nivel: Alerta["nivel"] }) {
  const estilos: Record<Alerta["nivel"], string> = {
    critico: "bg-red-50 text-red-700 border border-red-200",
    seguimiento: "bg-amber-50 text-amber-700 border border-amber-200",
    oportunidad: "bg-blue-50 text-blue-700 border border-blue-200",
  }
  const etiquetas: Record<Alerta["nivel"], string> = {
    critico: "Crítico",
    seguimiento: "Seguimiento",
    oportunidad: "Oportunidad",
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${estilos[nivel]}`}>
      {etiquetas[nivel]}
    </span>
  )
}

// ── Icono de nivel ──────────────────────────────────────────────────────────

function IconoNivel({ nivel }: { nivel: Alerta["nivel"] }) {
  if (nivel === "critico") return <span className="text-red-500 text-base">⚠</span>
  if (nivel === "seguimiento") return <span className="text-amber-500 text-base">◉</span>
  return <span className="text-blue-500 text-base">◆</span>
}

// ── Modal nueva alerta ───────────────────────────────────────────────────────

interface ModalNuevaAlertaProps {
  onClose: () => void
}

function ModalNuevaAlerta({ onClose }: ModalNuevaAlertaProps) {
  const queryClient = useQueryClient()
  const [titulo, setTitulo] = useState("")
  const [descripcion, setDescripcion] = useState("")
  const [nivel, setNivel] = useState<Alerta["nivel"]>("seguimiento")
  const [error, setError] = useState<string | null>(null)

  const crearMutation = useMutation({
    mutationFn: () => api.alertas.crear({ titulo, descripcion: descripcion || undefined, nivel }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alertas"] })
      onClose()
    },
    onError: (e: Error) => setError(e.message),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!titulo.trim()) { setError("El título es obligatorio"); return }
    crearMutation.mutate()
  }

  return (
    <div className="fixed inset-0 overlay-strong z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
        <div className="px-6 py-4 border-b border-zinc-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-900">Nueva alerta</h2>
          <button onClick={onClose} className="text-zinc-400 hover:text-zinc-600 text-lg leading-none">×</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-zinc-600 mb-1.5">Título *</label>
            <input
              className="w-full border border-zinc-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-300"
              placeholder="Ej: Cuenta en riesgo de pérdida"
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-600 mb-1.5">Descripción (opcional)</label>
            <textarea
              className="w-full border border-zinc-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-300 resize-none"
              rows={3}
              placeholder="Detalles adicionales..."
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-600 mb-1.5">Nivel</label>
            <select
              className="w-full border border-zinc-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-300 bg-white"
              value={nivel}
              onChange={(e) => setNivel(e.target.value as Alerta["nivel"])}
            >
              <option value="critico">Crítico</option>
              <option value="seguimiento">Seguimiento</option>
              <option value="oportunidad">Oportunidad</option>
            </select>
          </div>

          {error && <p className="text-xs text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-zinc-600 hover:text-zinc-900 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={crearMutation.isPending}
              className="px-4 py-2 text-sm bg-zinc-900 text-white rounded-lg hover:bg-zinc-700 transition-colors disabled:opacity-50"
            >
              {crearMutation.isPending ? "Creando…" : "Crear alerta"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Fila de alerta ───────────────────────────────────────────────────────────

interface FilaAlertaProps {
  alerta: Alerta
  puedeGestionar: boolean
  esAdmin: boolean
}

function FilaAlerta({ alerta, puedeGestionar, esAdmin }: FilaAlertaProps) {
  const queryClient = useQueryClient()
  const [confirmandoEliminar, setConfirmandoEliminar] = useState(false)

  const resolverMutation = useMutation({
    mutationFn: () => api.alertas.resolver(alerta.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alertas"] }),
  })

  const eliminarMutation = useMutation({
    mutationFn: () => api.alertas.eliminar(alerta.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alertas"] }),
  })

  const fecha = new Date(alerta.creado_en).toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  })

  return (
    <div
      className={`p-4 rounded-xl border transition-colors ${
        alerta.resuelta
          ? "bg-zinc-50 border-zinc-100 opacity-60"
          : "bg-white border-zinc-200"
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5">
          <IconoNivel nivel={alerta.nivel} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-2 flex-wrap">
              <p className={`text-sm font-semibold ${alerta.resuelta ? "text-zinc-400 line-through" : "text-zinc-900"}`}>
                {alerta.titulo}
              </p>
              <BadgeNivel nivel={alerta.nivel} />
              {alerta.resuelta && (
                <span className="text-xs text-green-600 font-medium">✓ Resuelta</span>
              )}
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {!alerta.resuelta && puedeGestionar && (
                <button
                  onClick={() => resolverMutation.mutate()}
                  disabled={resolverMutation.isPending}
                  className="text-xs px-2.5 py-1 rounded-lg bg-green-50 text-green-700 border border-green-200 hover:bg-green-100 transition-colors disabled:opacity-50"
                >
                  {resolverMutation.isPending ? "…" : "Resolver"}
                </button>
              )}
              {esAdmin && (
                confirmandoEliminar ? (
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-zinc-500">¿Eliminar?</span>
                    <button
                      onClick={() => eliminarMutation.mutate()}
                      disabled={eliminarMutation.isPending}
                      className="text-xs px-2 py-1 rounded bg-red-600 text-white hover:bg-red-700 transition-colors"
                    >
                      Sí
                    </button>
                    <button
                      onClick={() => setConfirmandoEliminar(false)}
                      className="text-xs px-2 py-1 rounded bg-zinc-100 text-zinc-600 hover:bg-zinc-200 transition-colors"
                    >
                      No
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmandoEliminar(true)}
                    className="text-xs px-2.5 py-1 rounded-lg text-zinc-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                  >
                    Eliminar
                  </button>
                )
              )}
            </div>
          </div>

          {alerta.descripcion && (
            <p className="text-sm text-zinc-600 mt-1">{alerta.descripcion}</p>
          )}

          <div className="flex items-center gap-3 mt-2">
            <span className="text-xs text-zinc-400">{fecha}</span>
            {alerta.usuario_nombre && (
              <span className="text-xs text-zinc-400">· {alerta.usuario_nombre}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Página principal ─────────────────────────────────────────────────────────

export default function PaginaAlertas() {
  const { isAdmin, isManager, usuarioActual } = useAppStore()
  const [incluirResueltas, setIncluirResueltas] = useState(false)
  const [mostrarModal, setMostrarModal] = useState(false)
  const [filtroNivel, setFiltroNivel] = useState<"todos" | Alerta["nivel"]>("todos")
  const [montado, setMontado] = useState(false)

  useEffect(() => {
    setMontado(true)
  }, [])

  // Evita hydration mismatch con estado persistido de Zustand (usuario/permisos).
  const puedeGestionar = montado
    ? isAdmin() || isManager() || (usuarioActual?.permisos.gestionar_alertas ?? false)
    : false
  const esAdmin = montado ? isAdmin() : false

  const { data: alertas = [], isLoading } = useQuery<Alerta[]>({
    queryKey: ["alertas", incluirResueltas],
    queryFn: () => api.alertas.listar(incluirResueltas) as Promise<Alerta[]>,
  })

  const alertasFiltradas =
    filtroNivel === "todos" ? alertas : alertas.filter((a) => a.nivel === filtroNivel)

  const contadores = {
    critico: alertas.filter((a) => a.nivel === "critico" && !a.resuelta).length,
    seguimiento: alertas.filter((a) => a.nivel === "seguimiento" && !a.resuelta).length,
    oportunidad: alertas.filter((a) => a.nivel === "oportunidad" && !a.resuelta).length,
  }

  return (
    <>
      <Topbar titulo="Alertas" subtitulo="Oportunidades en riesgo y avisos del sistema" />

      <main className="flex-1 p-2.5 md:p-3.5 space-y-6">
        {/* ── KPI strip ─────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 flex items-center gap-4">
            <span className="text-2xl">⚠</span>
            <div>
              <p className="text-2xl font-bold text-red-700">{contadores.critico}</p>
              <p className="text-xs text-red-600 font-medium">Críticas activas</p>
            </div>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-4 flex items-center gap-4">
            <span className="text-2xl">◉</span>
            <div>
              <p className="text-2xl font-bold text-amber-700">{contadores.seguimiento}</p>
              <p className="text-xs text-amber-600 font-medium">En seguimiento</p>
            </div>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-xl px-5 py-4 flex items-center gap-4">
            <span className="text-2xl">◆</span>
            <div>
              <p className="text-2xl font-bold text-blue-700">{contadores.oportunidad}</p>
              <p className="text-xs text-blue-600 font-medium">Oportunidades</p>
            </div>
          </div>
        </div>

        {/* ── Controles ─────────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-wrap">
            {/* Filtro por nivel */}
            {(["todos", "critico", "seguimiento", "oportunidad"] as const).map((n) => (
              <button
                key={n}
                onClick={() => setFiltroNivel(n)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                  filtroNivel === n
                    ? "bg-zinc-900 text-white border-zinc-900"
                    : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-400"
                }`}
              >
                {n === "todos" ? "Todos" : n === "critico" ? "Crítico" : n === "seguimiento" ? "Seguimiento" : "Oportunidad"}
              </button>
            ))}

            {/* Toggle resueltas */}
            <label className="flex items-center gap-2 cursor-pointer ml-2">
              <input
                type="checkbox"
                checked={incluirResueltas}
                onChange={(e) => setIncluirResueltas(e.target.checked)}
                className="rounded border-zinc-300 text-zinc-900"
              />
              <span className="text-xs text-zinc-600">Incluir resueltas</span>
            </label>
          </div>

          {puedeGestionar && (
            <button
              onClick={() => setMostrarModal(true)}
              className="text-sm px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-700 transition-colors"
            >
              + Nueva alerta
            </button>
          )}
        </div>

        {/* ── Lista de alertas ──────────────────────────────────────────── */}
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-20 rounded-xl bg-zinc-100 animate-pulse" />
            ))}
          </div>
        ) : alertasFiltradas.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-3xl mb-3">✓</p>
            <p className="text-sm font-semibold text-zinc-700">
              {filtroNivel === "todos" ? "No hay alertas activas" : `No hay alertas de tipo "${filtroNivel}"`}
            </p>
            <p className="text-xs text-zinc-400 mt-1">
              {incluirResueltas ? "Todo está en orden." : "Activa «Incluir resueltas» para ver el historial."}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {alertasFiltradas.map((alerta) => (
              <FilaAlerta
                key={alerta.id}
                alerta={alerta}
                puedeGestionar={puedeGestionar}
                esAdmin={esAdmin}
              />
            ))}
          </div>
        )}
      </main>

      {mostrarModal && <ModalNuevaAlerta onClose={() => setMostrarModal(false)} />}
    </>
  )
}
