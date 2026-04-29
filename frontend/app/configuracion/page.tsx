"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"
import { useAppStore } from "@/store/use-app-store"
import { api } from "@/lib/api"
import { Topbar } from "@/components/layout/topbar"
import { RoleGuard } from "@/components/role-guard"
import type { IaConfig, PlantillaDoc, ServicioIa } from "@/types"

// =============================================================================
// Constantes de servicios
// =============================================================================

const SERVICIOS: Array<{ id: ServicioIa; label: string; icono: string; desc: string }> = [
  { id: "copilot",       label: "IC Copilot",       icono: "✦", desc: "Chat de inteligencia comercial con contexto del pipeline" },
  { id: "voice",         label: "Voice Studio",     icono: "◎", desc: "Generación de scripts de briefing para audio" },
  { id: "informes",      label: "Informes PDF",     icono: "📊", desc: "Generación de informes ejecutivos con análisis por secciones" },
  { id: "decks",         label: "Deck de Visita",   icono: "⬡", desc: "Presentaciones comerciales en formato PPTX" },
  { id: "cross_selling", label: "Cross-Selling IC", icono: "⚡", desc: "Estudio de oportunidades y análisis de cuenta con IC" },
  { id: "importacion",   label: "Chat Importación", icono: "⇄", desc: "Chat de consultas sobre CSV importados" },
]
const OLLAMA_URL_DEFECTO = process.env.NEXT_PUBLIC_OLLAMA_URL ?? "http://76.13.9.183:32768"
const OLLAMA_MODELO_DEFECTO = process.env.NEXT_PUBLIC_OLLAMA_MODEL ?? "llama3.2:3b"
const TIPOS_PLANTILLA: PlantillaDoc["tipo"][] = ["pdf", "pptx", "briefing", "propuesta", "investigacion", "informe"]

// =============================================================================
// helpers
// =============================================================================

function fmtSize(bytes: number): string {
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`
  return `${(bytes / 1e6).toFixed(0)} MB`
}

// =============================================================================
// Panel de configuración para un servicio
// =============================================================================

function PanelServicio({
  config,
  onChange,
}: {
  config: IaConfig
  onChange: (c: Partial<IaConfig>) => void
}) {
  const [modelos, setModelos] = useState<Array<{ name: string; size: number }>>([])
  const [estadoConex, setEstadoConex] = useState<"idle" | "cargando" | "ok" | "error">("idle")
  const [msgConex, setMsgConex] = useState("")

  // Test IC
  const [testEstado, setTestEstado] = useState<"idle" | "cargando" | "ok" | "error">("idle")
  const [testRespuesta, setTestRespuesta] = useState("")
  const testRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    if (config.proveedor !== "ollama") {
      onChange({ proveedor: "ollama" })
    }
  }, [config.proveedor, onChange])

  async function conectarOllama(url: string) {
    setEstadoConex("cargando")
    setMsgConex("")
    setModelos([])
    try {
      const datos = await api.ia.obtenerModelosOllama(url.replace(/\/$/, ""))
      const lista = (datos.models ?? []).map((m: { name: string; size: number }) => ({ name: m.name, size: m.size }))
      setModelos(lista)
      setEstadoConex("ok")
      setMsgConex(`${lista.length} modelo${lista.length !== 1 ? "s" : ""} disponible${lista.length !== 1 ? "s" : ""}`)
      if (lista.length > 0 && !lista.find((m: { name: string }) => m.name === config.ollamaModelo)) {
        onChange({ ollamaModelo: lista[0].name })
      }
    } catch (e) {
      setEstadoConex("error")
      const msg = e instanceof Error ? e.message : "Error desconocido"
      setMsgConex(`No se pudo conectar a ${url} — ${msg}`)
    }
  }

  async function testearIA() {
    setTestEstado("cargando")
    setTestRespuesta("")
    try {
      const r = await api.ia.probarOllama(config.ollamaUrl, config.ollamaModelo)
      const texto = r.respuesta || "OK"
      setTestRespuesta(texto)
      testRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" })
      setTestEstado("ok")
    } catch (e) {
      setTestRespuesta(e instanceof Error ? e.message : "Error desconocido")
      setTestEstado("error")
    }
  }

  return (
    <div className="space-y-5">
      <div className="bg-zinc-50 rounded-xl p-4 space-y-4 border border-zinc-200">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold text-zinc-600 uppercase tracking-wider">Configuración Ollama</p>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">IC local</span>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-600">URL del servidor</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={config.ollamaUrl}
              onChange={(e) => onChange({ ollamaUrl: e.target.value })}
              className="flex-1 px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo/30 focus:border-sgs-rojo font-mono bg-white"
              placeholder="http://localhost:11434"
            />
            <button
              onClick={() => conectarOllama(config.ollamaUrl)}
              disabled={estadoConex === "cargando"}
              className="px-4 py-2 text-sm font-medium bg-white border border-zinc-300 hover:border-zinc-400 rounded-lg transition-colors disabled:opacity-50"
            >
              {estadoConex === "cargando" ? "Conectando…" : "Conectar"}
            </button>
          </div>
          {estadoConex !== "idle" && (
            <p className={cn("text-xs", estadoConex === "ok" ? "text-emerald-600" : estadoConex === "error" ? "text-red-600" : "text-zinc-500")}>
              {estadoConex === "ok" ? "✓ " : estadoConex === "error" ? "✗ " : ""}{msgConex}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-600">Modelo</label>
          {modelos.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {modelos.map((m) => (
                <button
                  key={m.name}
                  onClick={() => onChange({ ollamaModelo: m.name })}
                  className={cn(
                    "w-full text-left flex items-center justify-between px-3 py-2 rounded-lg border transition-colors",
                    config.ollamaModelo === m.name ? "border-sgs-rojo bg-red-50" : "border-zinc-200 bg-white hover:border-zinc-300",
                  )}
                >
                  <span className="text-sm font-mono text-zinc-800">{m.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-zinc-400">{fmtSize(m.size)}</span>
                    {config.ollamaModelo === m.name && <span className="text-xs font-bold text-sgs-rojo">✓</span>}
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <input
              type="text"
              value={config.ollamaModelo}
              onChange={(e) => onChange({ ollamaModelo: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo/30 focus:border-sgs-rojo font-mono bg-white"
              placeholder="qwen2.5:14b, llama3.2, mistral, deepseek-r1…"
            />
          )}
          {modelos.length === 0 && estadoConex === "idle" && (
            <p className="text-xs text-zinc-400 italic">Haz clic en &quot;Conectar&quot; para ver modelos instalados en Ollama</p>
          )}
          <p className="text-[11px] text-zinc-500">
            Puedes escribir manualmente cualquier modelo compatible.
          </p>
        </div>
      </div>

      {/* Botón test */}
      <div className="pt-1">
        <button
          onClick={testearIA}
          disabled={testEstado === "cargando"}
          className="px-4 py-2 text-sm font-semibold bg-zinc-800 text-white hover:bg-zinc-700 rounded-lg transition-colors disabled:opacity-50"
        >
          {testEstado === "cargando" ? "Probando…" : "⚡ Probar conexión"}
        </button>
      </div>

      {/* Resultado test */}
      {testEstado !== "idle" && (
        <div className={cn(
          "rounded-xl border p-4 space-y-2",
          testEstado === "error" ? "border-red-200 bg-red-50" : "border-zinc-200 bg-white",
        )}>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              Test · Ollama / {config.ollamaModelo}
            </span>
            {testEstado === "cargando" && (
              <span className="w-3 h-3 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin" />
            )}
            {testEstado === "ok" && <span className="text-xs text-emerald-600 font-semibold">✓ OK</span>}
            {testEstado === "error" && <span className="text-xs text-red-600 font-semibold">✗ Error</span>}
          </div>
          <p className="text-xs text-zinc-400 italic border-b border-zinc-100 pb-2">
            &quot;¿Cuál es el win rate global del pipeline de SGS España?&quot;
          </p>
          <p
            ref={testRef}
            className={cn("text-sm leading-relaxed whitespace-pre-wrap", testEstado === "error" ? "text-red-700" : "text-zinc-800")}
          >
            {testRespuesta || (testEstado === "cargando" && (
              <span className="inline-flex gap-1 items-center text-zinc-400">
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce" style={{ animationDelay: "300ms" }} />
              </span>
            ))}
          </p>
        </div>
      )}

    </div>
  )
}

function PanelPlantillasIa() {
  const [tipoFiltro, setTipoFiltro] = useState<PlantillaDoc["tipo"]>("pdf")
  const [plantillas, setPlantillas] = useState<PlantillaDoc[]>([])
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState("")
  const [seleccionadaId, setSeleccionadaId] = useState<string | null>(null)
  const [nombre, setNombre] = useState("")
  const [activa, setActiva] = useState(true)
  const [contenidoTexto, setContenidoTexto] = useState("{}")
  const [guardando, setGuardando] = useState(false)

  const cargar = useCallback(async () => {
    setCargando(true)
    setError("")
    try {
      const datos = await api.plantillas.listar(tipoFiltro, false)
      setPlantillas(datos)
      if (datos.length > 0) {
        const primera = datos[0]
        setSeleccionadaId(primera.id)
        setNombre(primera.nombre)
        setActiva(primera.activa)
        setContenidoTexto(JSON.stringify(primera.contenido ?? {}, null, 2))
      } else {
        setSeleccionadaId(null)
        setNombre("")
        setActiva(true)
        setContenidoTexto("{}")
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudieron cargar plantillas")
    } finally {
      setCargando(false)
    }
  }, [tipoFiltro])

  useEffect(() => {
    void cargar()
  }, [cargar])

  function cargarEditorDesdeSeleccion(id: string) {
    const p = plantillas.find((item) => item.id === id)
    if (!p) return
    setSeleccionadaId(p.id)
    setNombre(p.nombre)
    setActiva(p.activa)
    setContenidoTexto(JSON.stringify(p.contenido ?? {}, null, 2))
  }

  async function guardarSeleccionada() {
    if (!seleccionadaId) return
    setGuardando(true)
    setError("")
    try {
      const contenido = JSON.parse(contenidoTexto)
      const actualizada = await api.plantillas.actualizar(seleccionadaId, { nombre, activa, contenido })
      setPlantillas((prev) => prev.map((p) => (p.id === actualizada.id ? actualizada : p)))
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar la plantilla")
    } finally {
      setGuardando(false)
    }
  }

  async function crearNueva() {
    setGuardando(true)
    setError("")
    try {
      const contenido = JSON.parse(contenidoTexto || "{}")
      const nueva = await api.plantillas.crear({
        nombre: nombre.trim() || `Plantilla ${tipoFiltro.toUpperCase()}`,
        tipo: tipoFiltro,
        contenido,
      })
      setPlantillas((prev) => [nueva, ...prev])
      setSeleccionadaId(nueva.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo crear la plantilla")
    } finally {
      setGuardando(false)
    }
  }

  async function eliminarSeleccionada() {
    if (!seleccionadaId) return
    setGuardando(true)
    setError("")
    try {
      await api.plantillas.eliminar(seleccionadaId)
      const restante = plantillas.filter((p) => p.id !== seleccionadaId)
      setPlantillas(restante)
      if (restante.length > 0) {
        cargarEditorDesdeSeleccion(restante[0].id)
      } else {
        setSeleccionadaId(null)
        setNombre("")
        setActiva(true)
        setContenidoTexto("{}")
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo eliminar la plantilla")
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-zinc-200 p-4 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-zinc-800">Plantillas IC</h3>
          <p className="text-xs text-zinc-500">Administra plantillas para informes, presentaciones y audios.</p>
        </div>
        <button
          onClick={() => void cargar()}
          className="px-2.5 py-1 rounded-md text-xs font-semibold border border-zinc-300 hover:border-zinc-400"
        >
          Recargar
        </button>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {TIPOS_PLANTILLA.map((tipo) => (
          <button
            key={tipo}
            onClick={() => setTipoFiltro(tipo)}
            className={cn(
              "px-2 py-1 text-[11px] font-semibold rounded-md border transition-colors uppercase",
              tipoFiltro === tipo ? "border-sgs-rojo bg-red-50 text-sgs-rojo" : "border-zinc-200 text-zinc-600 hover:border-zinc-300",
            )}
          >
            {tipo}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="border border-zinc-200 rounded-lg p-2 max-h-64 overflow-auto space-y-1">
          {cargando ? (
            <p className="text-xs text-zinc-500 p-2">Cargando plantillas…</p>
          ) : plantillas.length === 0 ? (
            <p className="text-xs text-zinc-500 p-2">No hay plantillas para este tipo.</p>
          ) : (
            plantillas.map((p) => (
              <button
                key={p.id}
                onClick={() => cargarEditorDesdeSeleccion(p.id)}
                className={cn(
                  "w-full text-left rounded-md border px-2 py-1.5 transition-colors",
                  seleccionadaId === p.id ? "border-sgs-rojo bg-red-50" : "border-zinc-200 hover:border-zinc-300",
                )}
              >
                <p className="text-xs font-semibold text-zinc-800 truncate">{p.nombre}</p>
                <p className="text-[10px] text-zinc-500">{p.activa ? "Activa" : "Inactiva"} · {new Date(p.actualizado_en).toLocaleDateString("es-ES")}</p>
              </button>
            ))
          )}
        </div>

        <div className="space-y-2">
          <input
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            placeholder="Nombre de plantilla"
            className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo/30 focus:border-sgs-rojo"
          />
          <label className="flex items-center gap-2 text-xs text-zinc-700">
            <input
              type="checkbox"
              checked={activa}
              onChange={(e) => setActiva(e.target.checked)}
            />
            Plantilla activa
          </label>
          <textarea
            value={contenidoTexto}
            onChange={(e) => setContenidoTexto(e.target.value)}
            className="w-full h-40 px-3 py-2 text-xs font-mono border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo/30 focus:border-sgs-rojo"
            placeholder='{"prompt_base":"..."}'
          />
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => void crearNueva()}
              disabled={guardando}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-zinc-800 text-white hover:bg-zinc-700 disabled:opacity-50"
            >
              Crear nueva
            </button>
            <button
              onClick={() => void guardarSeleccionada()}
              disabled={guardando || !seleccionadaId}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-sgs-rojo text-white hover:bg-red-700 disabled:opacity-50"
            >
              Guardar cambios
            </button>
            <button
              onClick={() => void eliminarSeleccionada()}
              disabled={guardando || !seleccionadaId}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-red-200 text-red-700 hover:bg-red-50 disabled:opacity-50"
            >
              Eliminar
            </button>
          </div>
          {error && <p className="text-xs text-red-600">{error}</p>}
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Página
// =============================================================================

export default function PaginaConfiguracion() {
  const { iaConfigs, setIaConfig } = useAppStore()
  const [tabActiva, setTabActiva] = useState<ServicioIa>("copilot")
  const [guardados, setGuardados] = useState<Partial<Record<ServicioIa, boolean>>>({})
  const [research, setResearch] = useState<{
    proveedorActivo: string
    modeloActivo: string
    ollamaUrlActiva: string
    proveedores: Record<string, { configurado: boolean; deep_research_soportado: boolean; modelo_activo?: string; api_key_runtime?: boolean }>
  } | null>(null)
  const [researchBorrador, setResearchBorrador] = useState("")
  const [researchModeloBorrador, setResearchModeloBorrador] = useState("")
  const [researchOllamaUrlBorrador, setResearchOllamaUrlBorrador] = useState("")
  const [researchApiKeyBorrador, setResearchApiKeyBorrador] = useState("")
  const [researchEstado, setResearchEstado] = useState<"idle" | "cargando" | "ok" | "error">("idle")
  const [researchMsg, setResearchMsg] = useState("")
  const [researchTestEstado, setResearchTestEstado] = useState<"idle" | "cargando" | "ok" | "error">("idle")
  const [researchTestMsg, setResearchTestMsg] = useState("")
  const [researchModelos, setResearchModelos] = useState<Array<{ name: string; size: number }>>([])
  const [researchConexEstado, setResearchConexEstado] = useState<"idle" | "cargando" | "ok" | "error">("idle")
  const [researchConexMsg, setResearchConexMsg] = useState("")

  // Borrador local — se guarda al hacer clic en "Guardar"
  const [borradores, setBorradores] = useState<Record<ServicioIa, IaConfig>>({ ...iaConfigs })

  const cargarResearch = useCallback(async () => {
    setResearchEstado("cargando")
    setResearchMsg("")
    try {
      const datos = await api.ia.obtenerConfigResearch()
      setResearch({
        proveedorActivo: datos.proveedor_activo,
        modeloActivo: datos.modelo_activo,
        ollamaUrlActiva: datos.ollama_url_activa,
        proveedores: datos.proveedores,
      })
      setResearchBorrador(datos.proveedor_activo)
      setResearchModeloBorrador(datos.modelo_activo)
      setResearchOllamaUrlBorrador(datos.ollama_url_activa)
      setResearchApiKeyBorrador("")
      setResearchEstado("idle")
    } catch (e) {
      setResearchEstado("error")
      setResearchMsg(e instanceof Error ? e.message : "No se pudo cargar configuración Research")
    }
  }, [])

  const cargarOperacional = useCallback(async () => {
    try {
      const datos = await api.ia.obtenerConfigOperacional()
      const mapeado: Record<ServicioIa, IaConfig> = {
        copilot: {
          proveedor: "ollama",
          ollamaUrl: datos.configs.copilot?.ollama_url ?? OLLAMA_URL_DEFECTO,
          ollamaModelo: datos.configs.copilot?.ollama_modelo ?? OLLAMA_MODELO_DEFECTO,
        },
        voice: {
          proveedor: "ollama",
          ollamaUrl: datos.configs.voice?.ollama_url ?? OLLAMA_URL_DEFECTO,
          ollamaModelo: datos.configs.voice?.ollama_modelo ?? OLLAMA_MODELO_DEFECTO,
        },
        informes: {
          proveedor: "ollama",
          ollamaUrl: datos.configs.informes?.ollama_url ?? OLLAMA_URL_DEFECTO,
          ollamaModelo: datos.configs.informes?.ollama_modelo ?? OLLAMA_MODELO_DEFECTO,
        },
        decks: {
          proveedor: "ollama",
          ollamaUrl: datos.configs.decks?.ollama_url ?? OLLAMA_URL_DEFECTO,
          ollamaModelo: datos.configs.decks?.ollama_modelo ?? OLLAMA_MODELO_DEFECTO,
        },
        cross_selling: {
          proveedor: "ollama",
          ollamaUrl: datos.configs.cross_selling?.ollama_url ?? OLLAMA_URL_DEFECTO,
          ollamaModelo: datos.configs.cross_selling?.ollama_modelo ?? OLLAMA_MODELO_DEFECTO,
        },
        importacion: {
          proveedor: "ollama",
          ollamaUrl: datos.configs.importacion?.ollama_url ?? OLLAMA_URL_DEFECTO,
          ollamaModelo: datos.configs.importacion?.ollama_modelo ?? OLLAMA_MODELO_DEFECTO,
        },
      }
      for (const servicio of ["copilot", "voice", "informes", "decks", "cross_selling", "importacion"] as const) {
        setIaConfig(servicio, mapeado[servicio])
      }
      setBorradores(mapeado)
    } catch {
      // Si no hay config persistida todavía, seguimos con la del store local.
    }
  }, [setIaConfig])

  useEffect(() => {
    void cargarResearch()
    void cargarOperacional()
  }, [cargarOperacional, cargarResearch])

  function actualizarBorrador(servicio: ServicioIa, cambios: Partial<IaConfig>) {
    setBorradores((b) => ({ ...b, [servicio]: { ...b[servicio], ...cambios } }))
  }

  async function guardar(servicio: ServicioIa) {
    const nuevoEstado: Record<ServicioIa, IaConfig> = {
      ...borradores,
      [servicio]: { ...borradores[servicio], proveedor: "ollama" },
    }
    try {
      await api.ia.actualizarConfigOperacional({
        copilot: {
          proveedor: "ollama",
          ollama_url: nuevoEstado.copilot.ollamaUrl,
          ollama_modelo: nuevoEstado.copilot.ollamaModelo,
        },
        voice: {
          proveedor: "ollama",
          ollama_url: nuevoEstado.voice.ollamaUrl,
          ollama_modelo: nuevoEstado.voice.ollamaModelo,
        },
        informes: {
          proveedor: "ollama",
          ollama_url: nuevoEstado.informes.ollamaUrl,
          ollama_modelo: nuevoEstado.informes.ollamaModelo,
        },
        decks: {
          proveedor: "ollama",
          ollama_url: nuevoEstado.decks.ollamaUrl,
          ollama_modelo: nuevoEstado.decks.ollamaModelo,
        },
        cross_selling: {
          proveedor: "ollama",
          ollama_url: nuevoEstado.cross_selling.ollamaUrl,
          ollama_modelo: nuevoEstado.cross_selling.ollamaModelo,
        },
        importacion: {
          proveedor: "ollama",
          ollama_url: nuevoEstado.importacion.ollamaUrl,
          ollama_modelo: nuevoEstado.importacion.ollamaModelo,
        },
      })
      setIaConfig(servicio, nuevoEstado[servicio])
      setGuardados((g) => ({ ...g, [servicio]: true }))
      setTimeout(() => setGuardados((g) => ({ ...g, [servicio]: false })), 2500)
    } catch {
      setGuardados((g) => ({ ...g, [servicio]: false }))
    }
  }

  async function guardarResearch() {
    setResearchEstado("cargando")
    setResearchMsg("")
    try {
      const res = await api.ia.actualizarConfigResearch({
        proveedor: researchBorrador,
        modelo: researchModeloBorrador,
        api_key: researchApiKeyBorrador || undefined,
        ollama_url: researchBorrador === "ollama" ? researchOllamaUrlBorrador : undefined,
      })
      setResearch((prev) =>
        prev
          ? {
              ...prev,
              proveedorActivo: res.proveedor_activo,
              modeloActivo: res.modelo_activo,
              ollamaUrlActiva: researchBorrador === "ollama" ? researchOllamaUrlBorrador : prev.ollamaUrlActiva,
            }
          : prev
      )
      setResearchApiKeyBorrador("")
      setResearchEstado("ok")
      setResearchMsg(`Deep Research activo: ${res.proveedor_activo} · ${res.modelo_activo}`)
      setTimeout(() => setResearchEstado("idle"), 2000)
    } catch (e) {
      setResearchEstado("error")
      setResearchMsg(e instanceof Error ? e.message : "No se pudo guardar configuración Research")
    }
  }

  async function probarResearch() {
    setResearchTestEstado("cargando")
    setResearchTestMsg("")
    try {
      const r = await api.ia.probarResearch({
        proveedor: researchBorrador,
        modelo: researchModeloBorrador,
        api_key: researchApiKeyBorrador || undefined,
        ollama_url: researchBorrador === "ollama" ? researchOllamaUrlBorrador : undefined,
      })
      setResearchTestEstado("ok")
      setResearchTestMsg(r.respuesta || "OK")
    } catch (e) {
      setResearchTestEstado("error")
      setResearchTestMsg(e instanceof Error ? e.message : "Error desconocido")
    }
  }

  async function conectarResearchOllama() {
    setResearchConexEstado("cargando")
    setResearchConexMsg("")
    setResearchModelos([])
    try {
      const datos = await api.ia.obtenerModelosOllama(researchOllamaUrlBorrador.replace(/\/$/, ""))
      const lista = (datos.models ?? []).map((m: { name: string; size: number }) => ({ name: m.name, size: m.size }))
      setResearchModelos(lista)
      setResearchConexEstado("ok")
      setResearchConexMsg(`${lista.length} modelo${lista.length !== 1 ? "s" : ""} disponible${lista.length !== 1 ? "s" : ""}`)
      if (lista.length > 0 && !lista.find((m: { name: string }) => m.name === researchModeloBorrador)) {
        setResearchModeloBorrador(lista[0].name)
      }
    } catch (e) {
      setResearchConexEstado("error")
      const msg = e instanceof Error ? e.message : "Error desconocido"
      setResearchConexMsg(`No se pudo conectar a ${researchOllamaUrlBorrador} — ${msg}`)
    }
  }

  const config = borradores[tabActiva]
  const guardado = guardados[tabActiva]
  const hayCambios = JSON.stringify(borradores[tabActiva]) !== JSON.stringify(iaConfigs[tabActiva])
  const usaOllamaResearch = researchBorrador === "ollama"
  const researchSinCambios = Boolean(
    research &&
    researchBorrador.trim() === research.proveedorActivo.trim() &&
    researchModeloBorrador.trim() === research.modeloActivo.trim() &&
    (!usaOllamaResearch || researchOllamaUrlBorrador.trim() === research.ollamaUrlActiva.trim()) &&
    !researchApiKeyBorrador.trim()
  )

  const servicioActivo = SERVICIOS.find((s) => s.id === tabActiva)!

  return (
    <RoleGuard rolMinimo="admin">
      <>
      <Topbar
        titulo="Configuración IC"
        subtitulo="Ajustes de modelos y proveedores de IC por servicio"
      />
      <main className="flex-1 p-2.5 md:p-3.5 w-full space-y-5">

      {/* Cabecera */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Configuración IC</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Configura el motor de Inteligencia Comercial de forma independiente para cada servicio.
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        <div className="xl:col-span-4 space-y-6">
          {/* Deep Research */}
          <div className="bg-white rounded-xl border border-zinc-200 p-5 space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-zinc-800">Deep Research (Investigación)</h2>
              <p className="text-xs text-zinc-500 mt-0.5">
                Selecciona el proveedor externo para investigación web (cuentas, mercado, señales).
              </p>
            </div>

            {research ? (
              <div className="space-y-3">
                <div className="grid grid-cols-1 gap-2">
                  {Object.entries(research.proveedores).map(([nombre, meta]) => {
                    const activo = researchBorrador === nombre
                    const deshabilitado = !meta.deep_research_soportado
                    return (
                      <button
                        key={nombre}
                        onClick={() => {
                          if (deshabilitado) return
                          setResearchBorrador(nombre)
                          setResearchModeloBorrador(meta.modelo_activo || "")
                        }}
                        disabled={deshabilitado}
                        className={cn(
                          "text-left p-3 rounded-lg border transition-colors",
                          activo ? "border-sgs-rojo bg-red-50" : "border-zinc-200 bg-white",
                          deshabilitado ? "opacity-50 cursor-not-allowed" : "hover:border-zinc-300",
                        )}
                      >
                        <p className="text-sm font-semibold text-zinc-800 capitalize">{nombre}</p>
                        <p className="text-[11px] text-zinc-500 mt-0.5 font-mono">
                          {meta.modelo_activo || "modelo no configurado"}
                        </p>
                        <p className="text-[11px] text-zinc-500 mt-1">
                          {meta.deep_research_soportado ? "Deep Research soportado" : "No soportado"}
                        </p>
                        {nombre !== "ollama" ? (
                          <p className={cn("text-[11px] mt-0.5", meta.configurado ? "text-emerald-600" : "text-amber-600")}>
                            {meta.configurado ? "API key configurada" : "Falta API key"}
                          </p>
                        ) : (
                          <p className="text-[11px] mt-0.5 text-emerald-600">
                            Conexión por URL (sin API key)
                          </p>
                        )}
                      </button>
                    )
                  })}
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={guardarResearch}
                    disabled={researchEstado === "cargando" || researchSinCambios}
                    className={cn(
                      "px-4 py-2 rounded-lg text-sm font-semibold transition-colors",
                      researchEstado === "cargando"
                        ? "bg-zinc-300 text-zinc-700"
                        : "bg-zinc-800 text-white hover:bg-zinc-700 disabled:opacity-50",
                    )}
                  >
                    {researchEstado === "cargando" ? "Guardando…" : "Guardar Deep Research"}
                  </button>
                  <p className="text-xs text-zinc-500">
                    Activo: <span className="font-semibold capitalize">{research.proveedorActivo}</span> · <span className="font-mono">{research.modeloActivo}</span>
                  </p>
                  <button
                    onClick={() => void probarResearch()}
                    disabled={researchTestEstado === "cargando"}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-zinc-300 hover:border-zinc-400 disabled:opacity-50"
                  >
                    {researchTestEstado === "cargando" ? "Probando…" : "Probar conexión"}
                  </button>
                </div>

                <div className="grid grid-cols-1 gap-3">
                  {usaOllamaResearch && (
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-zinc-600">URL Ollama para Deep Research</label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={researchOllamaUrlBorrador}
                          onChange={(e) => setResearchOllamaUrlBorrador(e.target.value)}
                          className="flex-1 px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo/30 focus:border-sgs-rojo font-mono bg-white"
                          placeholder="http://localhost:11434"
                        />
                        <button
                          onClick={() => void conectarResearchOllama()}
                          disabled={researchConexEstado === "cargando"}
                          className="px-4 py-2 text-sm font-medium bg-white border border-zinc-300 hover:border-zinc-400 rounded-lg transition-colors disabled:opacity-50"
                        >
                          {researchConexEstado === "cargando" ? "Conectando…" : "Conectar"}
                        </button>
                      </div>
                      {researchConexEstado !== "idle" && (
                        <p className={cn("text-xs", researchConexEstado === "ok" ? "text-emerald-600" : researchConexEstado === "error" ? "text-red-600" : "text-zinc-500")}>
                          {researchConexEstado === "ok" ? "✓ " : researchConexEstado === "error" ? "✗ " : ""}{researchConexMsg}
                        </p>
                      )}
                      <p className="text-[11px] text-zinc-500">
                        Esta URL solo afecta al motor Deep Research cuando el proveedor es Ollama.
                      </p>
                    </div>
                  )}

                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-600">Modelo Deep Research</label>
                    {usaOllamaResearch && researchModelos.length > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {researchModelos.map((m) => (
                          <button
                            key={m.name}
                            onClick={() => setResearchModeloBorrador(m.name)}
                            className={cn(
                              "w-full text-left flex items-center justify-between px-3 py-2 rounded-lg border transition-colors",
                              researchModeloBorrador === m.name ? "border-sgs-rojo bg-red-50" : "border-zinc-200 bg-white hover:border-zinc-300",
                            )}
                          >
                            <span className="text-sm font-mono text-zinc-800">{m.name}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-zinc-400">{fmtSize(m.size)}</span>
                              {researchModeloBorrador === m.name && <span className="text-xs font-bold text-sgs-rojo">✓</span>}
                            </div>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <input
                        type="text"
                        value={researchModeloBorrador}
                        onChange={(e) => setResearchModeloBorrador(e.target.value)}
                        className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo/30 focus:border-sgs-rojo font-mono bg-white"
                        placeholder="claude-sonnet-4-20250514 · gpt-4.1 · gemini-2.5-pro"
                      />
                    )}
                  </div>

                  {!usaOllamaResearch ? (
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-zinc-600">API key del proveedor seleccionado (opcional)</label>
                      <input
                        type="password"
                        value={researchApiKeyBorrador}
                        onChange={(e) => setResearchApiKeyBorrador(e.target.value)}
                        className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sgs-rojo/30 focus:border-sgs-rojo font-mono bg-white"
                        placeholder="Pega aquí la key para guardarla en runtime del backend"
                      />
                      <p className="text-[11px] text-zinc-500">
                        La key se envía solo al backend. No se muestra ni se devuelve después de guardar.
                      </p>
                    </div>
                  ) : (
                    <p className="text-[11px] text-zinc-500">
                      Con proveedor Ollama no se necesita API key.
                    </p>
                  )}
                </div>

                {researchMsg && (
                  <p className={cn("text-xs", researchEstado === "error" ? "text-red-600" : "text-emerald-600")}>
                    {researchMsg}
                  </p>
                )}
                {researchTestEstado !== "idle" && (
                  <p className={cn("text-xs", researchTestEstado === "error" ? "text-red-600" : "text-emerald-600")}>
                    Test Research: {researchTestMsg}
                  </p>
                )}
              </div>
            ) : researchEstado === "error" ? (
              <div className="space-y-3">
                <p className="text-xs text-red-600">
                  Error al cargar configuración Research: {researchMsg || "Error desconocido"}
                </p>
                <button
                  onClick={() => void cargarResearch()}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-zinc-800 text-white hover:bg-zinc-700"
                >
                  Reintentar
                </button>
              </div>
            ) : (
              <p className="text-xs text-zinc-500">
                {researchEstado === "cargando" ? "Cargando configuración Research…" : "Inicializando…"}
              </p>
            )}
          </div>

          {/* Resumen global */}
          <div className="bg-white rounded-xl border border-zinc-200 p-4">
            <p className="text-xs font-semibold text-zinc-600 uppercase tracking-wider mb-3">Resumen de configuración</p>
            <div className="grid grid-cols-1 gap-2">
              {SERVICIOS.map((s) => {
                const c = iaConfigs[s.id]
                return (
                  <div key={s.id} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-50">
                    <span className="text-sm">{s.icono}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-zinc-700 truncate">{s.label}</p>
                      <p className="text-[10px] text-zinc-500 font-mono truncate">
                        {`Ollama · ${c.ollamaModelo}`}
                      </p>
                    </div>
                    <span className="w-2 h-2 rounded-full shrink-0 bg-emerald-400" />
                  </div>
                )
              })}
            </div>
          </div>

          <PanelPlantillasIa />
        </div>

        <div className="xl:col-span-8">
          {/* Tabs de servicios */}
          <div className="bg-white rounded-xl border border-zinc-200 overflow-hidden">

        {/* Barra de tabs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 border-b border-zinc-200">
          {SERVICIOS.map((s) => {
            const config = iaConfigs[s.id]
            const enBorrador = JSON.stringify(borradores[s.id]) !== JSON.stringify(config)
            return (
              <button
                key={s.id}
                onClick={() => setTabActiva(s.id)}
                className={cn(
                  "flex items-center justify-center gap-2 px-3 py-3 text-sm font-medium transition-colors border-b-2 -mb-px",
                  tabActiva === s.id
                    ? "border-sgs-rojo text-sgs-rojo bg-red-50/40"
                    : "border-transparent text-zinc-500 hover:text-zinc-800 hover:bg-zinc-50",
                )}
              >
                <span>{s.icono}</span>
                <span className="text-left leading-tight">
                  <span className="block">{s.label}</span>
                  <span className="block text-[10px] font-mono text-zinc-500">
                    {config.ollamaModelo}
                  </span>
                </span>
                {enBorrador && (
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" title="Cambios sin guardar" />
                )}
              </button>
            )
          })}
        </div>

        {/* Contenido del tab activo */}
        <div className="p-5">
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-zinc-800">{servicioActivo.label}</h2>
            <p className="text-xs text-zinc-500 mt-0.5">{servicioActivo.desc}</p>
          </div>

          <PanelServicio
            key={tabActiva}
            config={config}
            onChange={(cambios) => actualizarBorrador(tabActiva, cambios)}
          />

          {/* Guardar */}
          <div className="flex items-center gap-3 mt-5 pt-4 border-t border-zinc-100">
            <button
              onClick={() => void guardar(tabActiva)}
              disabled={!hayCambios && !guardado}
              className={cn(
                "px-5 py-2 rounded-lg text-sm font-semibold transition-all",
                guardado
                  ? "bg-emerald-500 text-white"
                  : hayCambios
                  ? "bg-sgs-rojo text-white hover:bg-red-700"
                  : "bg-zinc-100 text-zinc-400 cursor-not-allowed",
              )}
            >
              {guardado ? "✓ Guardado" : `Guardar ${servicioActivo.label}`}
            </button>
            {hayCambios && !guardado && (
              <p className="text-xs text-zinc-500">Cambios sin guardar en este servicio</p>
            )}
          </div>
        </div>
      </div>
        </div>
      </div>
      </main>
      </>
    </RoleGuard>
  )
}
