"use client"

import { Suspense, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSearchParams, useRouter } from "next/navigation"
import Image from "next/image"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import { formatearEuros, formatearPorcentaje } from "@/lib/utils"
import { Topbar } from "@/components/layout/topbar"
import { useAppStore } from "@/store/use-app-store"
import type {
  PerfilRead,
  PerfilStats,
  NotificacionesConfig,
} from "@/types"

// ── Const types ───────────────────────────────────────────────────────────────

const TAB = {
  DATOS: "datos",
  CONFIG: "config",
} as const

type Tab = (typeof TAB)[keyof typeof TAB]

const SBU_OPCIONES = [
  "Certification",
  "Technical Consulting",
  "ESG Solutions",
  "Training",
  "Responsible Business Services",
  "Second Party",
]

const VOCES_TTS = ["es-ES", "es-MX", "es-AR", "es-US"]

// ── PerfilHero ────────────────────────────────────────────────────────────────

interface PerfilHeroProps {
  perfil: PerfilRead
  stats: PerfilStats | undefined
}

function PerfilHero({ perfil, stats }: PerfilHeroProps) {
  const iniciales = perfil.nombre_completo
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase()

  const colorRol: Record<string, string> = {
    admin: "bg-red-100 text-red-700",
    manager: "bg-blue-100 text-blue-700",
    comercial: "bg-green-100 text-green-700",
  }

  return (
    <div className="bg-white rounded-xl border border-zinc-200 p-6 flex items-center gap-6">
      {/* Avatar con iniciales */}
      <div className="relative w-16 h-16 rounded-full bg-sgs-rojo flex items-center justify-center text-white text-xl font-bold shrink-0 overflow-hidden">
        {perfil.avatar_url ? (
          <Image
            src={perfil.avatar_url}
            alt={perfil.nombre_completo}
            fill
            unoptimized
            sizes="64px"
            className="w-full h-full rounded-full object-cover"
          />
        ) : (
          iniciales
        )}
      </div>

      {/* Datos */}
      <div className="flex-1 min-w-0">
        <h1 className="text-lg font-bold text-zinc-900 truncate">{perfil.nombre_completo}</h1>
        <p className="text-sm text-zinc-500">{perfil.email}</p>
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", colorRol[perfil.rol] ?? "bg-zinc-100 text-zinc-600")}>
            {perfil.rol}
          </span>
          {perfil.sbu_principal && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium">
              {perfil.sbu_principal}
            </span>
          )}
          {perfil.zona && (
            <span className="text-xs text-zinc-400">📍 {perfil.zona}</span>
          )}
        </div>
      </div>

      {/* KPIs rápidos */}
      {stats && (
        <div className="hidden md:flex gap-6">
          <div className="text-right">
            <p className="text-xs text-zinc-400">Pipeline activo</p>
            <p className="text-sm font-bold text-zinc-900">{formatearEuros(stats.pipeline_activo)}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-zinc-400">Win Rate</p>
            <p className={cn("text-sm font-bold", Number(stats.win_rate) >= 70 ? "text-green-600" : "text-amber-600")}>
              {formatearPorcentaje(stats.win_rate)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-zinc-400">Abiertas</p>
            <p className="text-sm font-bold text-zinc-900">{stats.oportunidades_abiertas}</p>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Tab: Datos personales ─────────────────────────────────────────────────────

interface TabDatosProps {
  perfil: PerfilRead
}

function TabDatos({ perfil }: TabDatosProps) {
  const qc = useQueryClient()
  const [nombre, setNombre] = useState(perfil.nombre_completo)
  const [telefono, setTelefono] = useState(perfil.telefono ?? "")
  const [zona, setZona] = useState(perfil.zona ?? "")
  const [sbu, setSbu] = useState(perfil.sbu_principal ?? "")
  const [avatarUrl, setAvatarUrl] = useState(perfil.avatar_url ?? "")
  const [guardado, setGuardado] = useState(false)

  const { mutate: guardar, isPending } = useMutation({
    mutationFn: () =>
      api.perfil.actualizar({
        nombre_completo: nombre || undefined,
        telefono: telefono || undefined,
        zona: zona || undefined,
        sbu_principal: sbu || undefined,
        avatar_url: avatarUrl || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["perfil"] })
      setGuardado(true)
      setTimeout(() => setGuardado(false), 3000)
    },
  })

  return (
    <div className="bg-white rounded-xl border border-zinc-200 p-6 space-y-5">
      <h2 className="text-sm font-semibold text-zinc-800">Datos personales</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-zinc-600 mb-1.5">Email</label>
          <input
            type="text"
            value={perfil.email}
            disabled
            className="w-full text-sm border border-zinc-200 bg-zinc-50 text-zinc-500 rounded-lg px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-zinc-600 mb-1.5">Rol</label>
          <input
            type="text"
            value={perfil.rol}
            disabled
            className="w-full text-sm border border-zinc-200 bg-zinc-50 text-zinc-500 rounded-lg px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-zinc-600 mb-1.5">Nombre completo</label>
          <input
            type="text"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-zinc-600 mb-1.5">Teléfono</label>
          <input
            type="tel"
            value={telefono}
            onChange={(e) => setTelefono(e.target.value)}
            placeholder="+34 600 000 000"
            className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-zinc-600 mb-1.5">Zona</label>
          <input
            type="text"
            value={zona}
            onChange={(e) => setZona(e.target.value)}
            placeholder="Ej: Madrid Norte, Cataluña Sur..."
            className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-zinc-600 mb-1.5">SBU principal</label>
          <select
            value={sbu}
            onChange={(e) => setSbu(e.target.value)}
            className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
          >
            <option value="">Sin asignar</option>
            {SBU_OPCIONES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="md:col-span-2">
          <label className="block text-xs font-medium text-zinc-600 mb-1.5">URL de avatar</label>
          <input
            type="url"
            value={avatarUrl}
            onChange={(e) => setAvatarUrl(e.target.value)}
            placeholder="https://..."
            className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => guardar()}
          disabled={isPending}
          className="px-5 py-2 rounded-lg text-sm font-medium text-white bg-sgs-rojo disabled:opacity-50 transition-opacity"
        >
          {isPending ? "Guardando..." : "Guardar cambios"}
        </button>
        {guardado && (
          <span className="text-xs text-green-600 font-medium">✓ Guardado correctamente</span>
        )}
      </div>
    </div>
  )
}

// ── Tab: Configuración ────────────────────────────────────────────────────────

function TabConfig() {
  const qc = useQueryClient()
  const [guardado, setGuardado] = useState(false)

  const { data: config, isLoading } = useQuery<NotificacionesConfig>({
    queryKey: ["perfil-notificaciones"],
    queryFn: () => api.perfil.obtenerNotificaciones() as Promise<NotificacionesConfig>,
  })

  const [form, setForm] = useState<Partial<NotificacionesConfig>>({})

  const valor = (campo: keyof NotificacionesConfig) =>
    campo in form ? form[campo] : config?.[campo]

  const { mutate: guardar, isPending } = useMutation({
    mutationFn: () => api.perfil.actualizarNotificaciones(form as Record<string, unknown>),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["perfil-notificaciones"] })
      setGuardado(true)
      setTimeout(() => setGuardado(false), 3000)
    },
  })

  if (isLoading) return <div className="h-48 bg-zinc-100 rounded-xl animate-pulse" />

  return (
    <div className="bg-white rounded-xl border border-zinc-200 p-6 space-y-6">
      <h2 className="text-sm font-semibold text-zinc-800">Configuración de IC y alertas</h2>

      {/* Alertas */}
      <div className="space-y-3">
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">Alertas</p>
        {(
          [
            { campo: "alertas_pipeline", label: "Alertas de pipeline" },
            { campo: "briefing_diario", label: "Briefing diario automático" },
            { campo: "alerta_win_rate", label: "Alerta de Win Rate bajo" },
          ] as const
        ).map(({ campo, label }) => (
          <label key={campo} className="flex items-center justify-between cursor-pointer">
            <span className="text-sm text-zinc-700">{label}</span>
            <button
              role="switch"
              aria-checked={!!valor(campo)}
              onClick={() => setForm((f) => ({ ...f, [campo]: !valor(campo) }))}
              className={cn(
                "relative inline-flex h-5 w-9 rounded-full transition-colors",
                valor(campo) ? "bg-sgs-rojo" : "bg-zinc-200"
              )}
            >
              <span
                className={cn(
                  "inline-block h-4 w-4 rounded-full bg-white shadow transition-transform mt-0.5",
                  valor(campo) ? "translate-x-4" : "translate-x-0.5"
                )}
              />
            </button>
          </label>
        ))}
      </div>

      {/* Preferencias IC */}
      <div className="space-y-3">
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">Preferencias IC</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1.5">Hora del briefing</label>
            <input
              type="time"
              value={(valor("hora_briefing") as string) ?? "08:00"}
              onChange={(e) => setForm((f) => ({ ...f, hora_briefing: e.target.value }))}
              className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1.5">Duración podcast (min)</label>
            <input
              type="number"
              min={1}
              max={30}
              value={(valor("duracion_podcast_min") as number) ?? 5}
              onChange={(e) => setForm((f) => ({ ...f, duracion_podcast_min: Number(e.target.value) }))}
              className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1.5">Voz TTS</label>
            <select
              value={(valor("voz_tts") as string) ?? "es-ES"}
              onChange={(e) => setForm((f) => ({ ...f, voz_tts: e.target.value }))}
              className="w-full text-sm border border-zinc-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent"
            >
              {VOCES_TTS.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1.5">
              Umbral alerta WR: <span className="font-bold text-zinc-800">{(valor("umbral_win_rate") as number) ?? 60}%</span>
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={(valor("umbral_win_rate") as number) ?? 60}
              onChange={(e) => setForm((f) => ({ ...f, umbral_win_rate: Number(e.target.value) }))}
              className="w-full mt-2"
            />
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => guardar()}
          disabled={isPending || Object.keys(form).length === 0}
          className="px-5 py-2 rounded-lg text-sm font-medium text-white bg-sgs-rojo disabled:opacity-50 transition-opacity"
        >
          {isPending ? "Guardando..." : "Guardar configuración"}
        </button>
        {guardado && (
          <span className="text-xs text-green-600 font-medium">✓ Guardado correctamente</span>
        )}
      </div>
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

const TABS: Array<{ id: Tab; label: string }> = [
  { id: TAB.DATOS, label: "Datos personales" },
  { id: TAB.CONFIG, label: "Configuración" },
]

function PaginaPerfilInterna() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const queryClient = useQueryClient()
  const usuarioActual = useAppStore((s) => s.usuarioActual)
  const [exportandoCsvPerfil, setExportandoCsvPerfil] = useState(false)
  const [reseteando, setReseteando] = useState(false)
  const tabQuery = searchParams.get("tab") as Tab | null
  const tabActual = tabQuery && TABS.some((t) => t.id === tabQuery) ? tabQuery : TAB.DATOS

  const { data: perfil, isLoading: cargandoPerfil, isError: perfilConError } = useQuery<PerfilRead>({
    queryKey: ["perfil"],
    queryFn: () => api.perfil.obtener() as Promise<PerfilRead>,
  })

  const perfilFallback: PerfilRead | null = usuarioActual
    ? {
        usuario_id: usuarioActual.usuario_id,
        email: usuarioActual.email,
        nombre_completo: usuarioActual.nombre_completo,
        rol: usuarioActual.rol,
        telefono: null,
        zona: null,
        sbu_principal: null,
        avatar_url: null,
        manager_id: null,
      }
    : null

  const perfilMostrado = perfil ?? perfilFallback

  const { data: stats } = useQuery<PerfilStats>({
    queryKey: ["perfil-stats"],
    queryFn: () => api.perfil.stats() as Promise<PerfilStats>,
    enabled: !!perfilMostrado,
  })

  function cambiarTab(tab: Tab) {
    router.push(`/perfil?tab=${tab}`, { scroll: false })
  }

  const exportarCsvPerfil = async () => {
    try {
      setExportandoCsvPerfil(true)
      await api.perfil.exportarCsv()
    } finally {
      setExportandoCsvPerfil(false)
    }
  }

  const resetearCuenta = async () => {
    if (!confirm("¿Seguro que quieres resetear tu cuenta? Se eliminarán todas tus oportunidades, seguimientos y documentos. Esta acción no se puede deshacer.")) return
    try {
      setReseteando(true)
      await api.perfil.resetearCuenta()
      queryClient.invalidateQueries()
    } finally {
      setReseteando(false)
    }
  }

  return (
    <>
      <Topbar titulo="Mi Perfil" subtitulo="Datos personales y configuración" />

      <main className="flex-1 p-2.5 md:p-3.5 space-y-5 w-full">
        {/* ── Hero ── */}
        {cargandoPerfil ? (
          <div className="h-28 bg-zinc-100 rounded-xl animate-pulse" />
        ) : perfilMostrado ? (
          <PerfilHero perfil={perfilMostrado} stats={stats} />
        ) : null}

        {perfilConError && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
            No se pudo cargar el perfil completo. Se muestran los datos base de tu sesión.
          </div>
        )}

        {/* ── Tabs ── */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-zinc-200 gap-2">
          <div className="flex gap-1 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => cambiarTab(t.id)}
              className={cn(
                "px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px",
                tabActual === t.id
                  ? "border-sgs-rojo text-sgs-rojo"
                  : "border-transparent text-zinc-500 hover:text-zinc-800"
              )}
            >
              {t.label}
            </button>
          ))}
          </div>
          <div className="flex items-center gap-2 mb-2">
            <button
              onClick={exportarCsvPerfil}
              disabled={exportandoCsvPerfil}
              className="w-full sm:w-auto px-4 py-2 rounded-lg text-xs font-semibold border border-zinc-300 text-zinc-700 bg-white hover:bg-zinc-50 disabled:opacity-50 transition-colors"
            >
              {exportandoCsvPerfil ? "Exportando CSV..." : "Exportar datos CSV"}
            </button>
            <button
              onClick={resetearCuenta}
              disabled={reseteando}
              className="w-full sm:w-auto px-4 py-2 rounded-lg text-xs font-semibold border border-red-300 text-red-600 bg-white hover:bg-red-50 disabled:opacity-50 transition-colors"
            >
              {reseteando ? "Reseteando..." : "Resetear mi cuenta"}
            </button>
          </div>
        </div>

        {/* ── Contenido de tab ── */}
        {tabActual === TAB.DATOS && perfilMostrado && <TabDatos perfil={perfilMostrado} />}
        {tabActual === TAB.CONFIG && <TabConfig />}
      </main>
    </>
  )
}

export default function PaginaPerfil() {
  return (
    <Suspense fallback={<div className="flex-1 p-6 text-sm text-zinc-500">Cargando perfil...</div>}>
      <PaginaPerfilInterna />
    </Suspense>
  )
}
