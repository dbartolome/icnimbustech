"use client"

import { Fragment, useCallback, useRef, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Trash2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import { Topbar } from "@/components/layout/topbar"
import type { ImportacionEstado } from "@/types"

interface MensajeCsv {
  role: "user" | "assistant"
  content: string
  cargando?: boolean
}

interface ImportacionPreview {
  id: string
  nombre_archivo: string
  creado_en: string
  columnas: string[]
  filas: Record<string, string>[]
}

// ─── helpers ─────────────────────────────────────────────────────────────────

function fmt(n: number | null): string {
  if (n === null || n === undefined) return "—"
  return n.toLocaleString("es-ES")
}

function fmtFecha(iso: string): string {
  return new Date(iso).toLocaleString("es-ES", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  })
}

function BadgeEstado({ estado }: { estado: ImportacionEstado["estado"] }) {
  const cls = {
    procesando: "bg-amber-100 text-amber-800",
    completado:  "bg-emerald-100 text-emerald-800",
    error:       "bg-red-100 text-red-700",
  }[estado]
  const label = { procesando: "Procesando…", completado: "Completado", error: "Error" }[estado]
  return (
    <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full", cls)}>
      {label}
    </span>
  )
}

// ─── BarraProgreso ────────────────────────────────────────────────────────────

function BarraProgreso({ resultado }: { resultado: ImportacionEstado }) {
  const total = resultado.total_filas ?? 0
  const ok = (resultado.filas_creadas ?? 0) + (resultado.filas_actualizadas ?? 0)
  const err = resultado.filas_error ?? 0
  const pct = total > 0 ? Math.round((ok / total) * 100) : 0

  return (
    <div className="mt-4 space-y-3">
      <div className="h-2 bg-zinc-100 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            resultado.estado === "error" ? "bg-red-500" :
            err > 0 ? "bg-amber-500" : "bg-emerald-500"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
        {[
          { label: "Total", value: fmt(resultado.total_filas), cls: "text-zinc-700" },
          { label: "Creadas", value: fmt(resultado.filas_creadas), cls: "text-emerald-600" },
          { label: "Actualizadas", value: fmt(resultado.filas_actualizadas), cls: "text-blue-600" },
          { label: "Errores", value: fmt(resultado.filas_error), cls: err > 0 ? "text-red-600" : "text-zinc-400" },
        ].map(({ label, value, cls }) => (
          <div key={label} className="bg-zinc-50 rounded-lg p-3">
            <p className={cn("text-xl font-bold", cls)}>{value}</p>
            <p className="text-xs text-zinc-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {resultado.errores && resultado.errores.length > 0 && (
        <details className="mt-2">
          <summary className="cursor-pointer text-sm text-red-600 font-medium select-none">
            Ver {resultado.errores.length} errores
          </summary>
          <div className="mt-2 max-h-48 overflow-y-auto rounded-lg border border-red-100 bg-red-50 p-3 space-y-1">
            {resultado.errores.map((e, i) => (
              <p key={i} className="text-xs text-red-700 font-mono">
                <span className="font-bold">Fila {e.fila}:</span> {e.error}
              </p>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}

// ─── ZonaUpload ───────────────────────────────────────────────────────────────

function ZonaUpload({
  onArchivo,
  cargando,
}: {
  onArchivo: (f: File) => void
  cargando: boolean
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [arrastrandoSobre, setArrastrandoSobre] = useState(false)

  const manejarArchivo = useCallback(
    (f: File) => {
      if (!f.name.toLowerCase().endsWith(".csv")) {
        toast.error("Solo se aceptan archivos .csv")
        return
      }
      onArchivo(f)
    },
    [onArchivo],
  )

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setArrastrandoSobre(true) }}
      onDragLeave={() => setArrastrandoSobre(false)}
      onDrop={(e) => {
        e.preventDefault()
        setArrastrandoSobre(false)
        const f = e.dataTransfer.files[0]
        if (f) manejarArchivo(f)
      }}
      onClick={() => !cargando && inputRef.current?.click()}
      className={cn(
        "border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors",
        arrastrandoSobre
          ? "border-sgs-rojo bg-red-50"
          : "border-zinc-300 hover:border-zinc-400 hover:bg-zinc-50",
        cargando && "pointer-events-none opacity-60",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) manejarArchivo(f) }}
      />
      <p className="text-4xl mb-3">📂</p>
      <p className="font-semibold text-zinc-700">
        {cargando ? "Procesando…" : "Arrastra un CSV aquí o haz clic para seleccionar"}
      </p>
      <p className="text-sm text-zinc-500 mt-1">Formato Salesforce · máx. 10 MB</p>
    </div>
  )
}

// ─── HistorialFila ────────────────────────────────────────────────────────────

function HistorialRow({
  item,
  onEliminar,
  contextoActivo,
  contextoCargando,
  onToggleContexto,
}: {
  item: ImportacionEstado
  onEliminar: (id: string) => void
  contextoActivo: boolean
  contextoCargando: boolean
  onToggleContexto: (id: string) => void
}) {
  const [confirmando, setConfirmando] = useState(false)
  const [eliminando, setEliminando] = useState(false)

  async function handleEliminar() {
    if (!confirmando) { setConfirmando(true); return }
    setEliminando(true)
    try {
      await onEliminar(item.id)
    } finally {
      setEliminando(false)
      setConfirmando(false)
    }
  }

  const err = item.filas_error ?? 0

  return (
    <tr className="hover:bg-zinc-50 transition-colors group">
      <td className="px-4 py-3 max-w-[220px]">
        <p className="text-xs font-medium text-zinc-800 truncate" title={item.nombre_archivo}>
          {item.nombre_archivo}
        </p>
        {item.usuario && <p className="text-[11px] text-zinc-400 truncate">{item.usuario}</p>}
      </td>
      <td className="px-3 py-2 text-[11px] text-zinc-500 whitespace-nowrap">{fmtFecha(item.creado_en)}</td>
      <td className="px-3 py-2">
        <span className={cn(
          "text-[10px] font-medium px-1.5 py-0.5 rounded-full",
          item.modo === "upsert"  ? "bg-blue-50 text-blue-700"
          : item.modo === "reset" ? "bg-amber-100 text-amber-800"
          :                         "bg-zinc-100 text-zinc-600"
        )}>
          {item.modo}
        </span>
      </td>
      <td className="px-3 py-2"><BadgeEstado estado={item.estado} /></td>
      <td className="px-3 py-2 text-[11px] text-right text-zinc-600 tabular-nums">{fmt(item.total_filas)}</td>
      <td className="px-3 py-2 text-[11px] text-right text-emerald-600 tabular-nums">{fmt(item.filas_creadas)}</td>
      <td className="px-3 py-2 text-[11px] text-right text-blue-600 tabular-nums">{fmt(item.filas_actualizadas)}</td>
      <td className="px-3 py-2 text-[11px] text-right tabular-nums">
        <span className={err > 0 ? "text-red-600 font-medium" : "text-zinc-400"}>{fmt(item.filas_error)}</span>
      </td>
      <td className="px-3 py-2 text-right">
        <div className="flex items-center justify-end gap-1.5">
          <button
            type="button"
            onClick={() => onToggleContexto(item.id)}
            className={cn(
              "text-[10px] px-2 py-0.5 rounded border shrink-0",
              contextoActivo
                ? "bg-emerald-100 text-emerald-700 border-emerald-300"
                : "bg-white text-zinc-500 border-zinc-200 hover:border-zinc-400",
              contextoCargando && "animate-pulse",
            )}
            title={contextoActivo ? "Ocultar CSV y desactivar contexto IA" : "Desplegar CSV y activar contexto IA"}
          >
            {contextoCargando ? "Cargando IA…" : contextoActivo ? "IA ON" : "Ver CSV"}
          </button>
          <button
            onClick={handleEliminar}
            disabled={eliminando}
            title={confirmando ? "Confirmar — clic de nuevo para borrar" : "Eliminar registro"}
            className={cn(
              "opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-md",
              confirmando
                ? "text-red-600 bg-red-50 opacity-100"
                : "text-zinc-400 hover:text-red-500 hover:bg-red-50",
              eliminando && "opacity-50 cursor-wait",
            )}
          >
            <Trash2 size={13} />
          </button>
        </div>
      </td>
    </tr>
  )
}

function BurbujaChat({ mensaje }: { mensaje: MensajeCsv }) {
  const esUsuario = mensaje.role === "user"
  return (
    <div className={cn("flex", esUsuario ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[92%] rounded-xl px-3 py-2 text-sm leading-relaxed",
          esUsuario
            ? "bg-sgs-rojo text-white rounded-br-sm"
            : "bg-zinc-800 border border-zinc-700 text-zinc-100 rounded-bl-sm"
        )}
      >
        {mensaje.cargando ? (
          <span className="inline-flex gap-1 items-center">
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce" style={{ animationDelay: "300ms" }} />
          </span>
        ) : (
          <p className="whitespace-pre-wrap">{mensaje.content}</p>
        )}
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PaginaImportacion() {
  const [modo, setModo] = useState<"upsert" | "append" | "reset">("reset")
  const [cargando, setCargando] = useState(false)
  const [resultado, setResultado] = useState<ImportacionEstado | null>(null)
  const [mensajesCsv, setMensajesCsv] = useState<MensajeCsv[]>([
    {
      role: "assistant",
      content: "Chat CSV listo. Selecciona un archivo con 'Ver CSV' y pregúntame por su contenido.",
    },
  ])
  const [preguntaCsv, setPreguntaCsv] = useState("")
  const [enviandoCsv, setEnviandoCsv] = useState(false)
  const [importacionContextoId, setImportacionContextoId] = useState<string | null>(null)
  const [filtroPreview, setFiltroPreview] = useState("")
  const [paginaPreview, setPaginaPreview] = useState(1)
  const [porPaginaPreview, setPorPaginaPreview] = useState(25)
  const [ordenColumnaPreview, setOrdenColumnaPreview] = useState<string | null>(null)
  const [ordenDireccionPreview, setOrdenDireccionPreview] = useState<"asc" | "desc">("asc")
  const bottomCsvRef = useRef<HTMLDivElement>(null)

  const qc = useQueryClient()

  const { data: historial = [], isLoading: cargandoHistorial } = useQuery({
    queryKey: ["importacion-historial"],
    queryFn: () => api.importacion.historial(),
    staleTime: 10_000,
  })

  const { data: previewSeleccionada, isLoading: cargandoPreview } = useQuery<ImportacionPreview>({
    queryKey: ["importacion-preview", importacionContextoId],
    queryFn: () => api.importacion.preview(importacionContextoId as string),
    enabled: Boolean(importacionContextoId),
    staleTime: 10_000,
  })

  const filasPreviewFiltradas = (() => {
    if (!previewSeleccionada) return []
    const q = filtroPreview.trim().toLowerCase()
    if (!q) return previewSeleccionada.filas
    return previewSeleccionada.filas.filter((fila) =>
      previewSeleccionada.columnas.some((col) => String(fila[col] ?? "").toLowerCase().includes(q)),
    )
  })()

  const filasPreviewOrdenadas = (() => {
    if (!ordenColumnaPreview) return filasPreviewFiltradas
    const col = ordenColumnaPreview
    const dir = ordenDireccionPreview
    return [...filasPreviewFiltradas].sort((a, b) => {
      const av = String(a[col] ?? "").toLowerCase()
      const bv = String(b[col] ?? "").toLowerCase()
      const cmp = av.localeCompare(bv, "es", { numeric: true, sensitivity: "base" })
      return dir === "asc" ? cmp : -cmp
    })
  })()

  const totalPaginasPreview = Math.max(1, Math.ceil(filasPreviewOrdenadas.length / porPaginaPreview))
  const paginaPreviewAjustada = Math.min(paginaPreview, totalPaginasPreview)
  const inicioPreview = (paginaPreviewAjustada - 1) * porPaginaPreview
  const filasPreviewPaginadas = filasPreviewOrdenadas.slice(inicioPreview, inicioPreview + porPaginaPreview)

  function alternarOrdenColumna(columna: string) {
    if (ordenColumnaPreview !== columna) {
      setOrdenColumnaPreview(columna)
      setOrdenDireccionPreview("asc")
      setPaginaPreview(1)
      return
    }
    setOrdenDireccionPreview((d) => (d === "asc" ? "desc" : "asc"))
    setPaginaPreview(1)
  }

  function exportarPreviewCsv() {
    if (!previewSeleccionada || filasPreviewFiltradas.length === 0) return
    const cols = previewSeleccionada.columnas
    const escapeCsv = (v: string) => `"${String(v ?? "").replace(/"/g, '""')}"`
    const header = cols.map(escapeCsv).join(",")
    const body = filasPreviewFiltradas
      .map((fila) => cols.map((c) => escapeCsv(String(fila[c] ?? ""))).join(","))
      .join("\n")
    const csv = `${header}\n${body}`
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    const base = previewSeleccionada.nombre_archivo.replace(/\.csv$/i, "")
    a.href = url
    a.download = `${base}_preview_filtrado.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const subirArchivo = async (archivo: File) => {
    setCargando(true)
    setResultado(null)
    try {
      const res = await api.importacion.subir(archivo, modo)
      setResultado(res)
      setImportacionContextoId(res.id)
      qc.invalidateQueries({ queryKey: ["pipeline-lista"] })
      qc.invalidateQueries({ queryKey: ["pipeline-funnel"] })
      qc.invalidateQueries({ queryKey: ["dashboard-kpis"] })
      qc.invalidateQueries({ queryKey: ["dashboard-evolucion"] })
      qc.invalidateQueries({ queryKey: ["dashboard-sbu"] })
      qc.invalidateQueries({ queryKey: ["importacion-historial"] })
      setMensajesCsv((prev) => ([
        ...prev,
        {
          role: "assistant",
          content: `Importación terminada (${res.estado}). Ya puedes consultarme sobre ${res.nombre_archivo}.`,
        },
      ]))
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al importar"
      setResultado({
        id: "",
        nombre_archivo: archivo.name,
        modo,
        estado: "error",
        total_filas: null,
        filas_procesadas: null,
        filas_creadas: null,
        filas_actualizadas: null,
        filas_error: null,
        errores: [{ fila: 0, error: msg }],
        creado_en: new Date().toISOString(),
        usuario: null,
      })
    } finally {
      setCargando(false)
    }
  }

  async function enviarConsultaCsv(textoPlano: string) {
    const texto = textoPlano.trim()
    if (!texto || enviandoCsv) return

    const nuevoUsuario: MensajeCsv = { role: "user", content: texto }
    const historialChat = [...mensajesCsv, nuevoUsuario]
    setMensajesCsv([...historialChat, { role: "assistant", content: "", cargando: true }])
    setPreguntaCsv("")
    setEnviandoCsv(true)

    const timeoutId = setTimeout(() => {
      setMensajesCsv((prev) => {
        const last = prev[prev.length - 1]
        if (last?.cargando) {
          const copia = [...prev]
          copia[copia.length - 1] = {
            role: "assistant",
            content: "La IA tarda más de lo esperado. Revisa que Ollama esté activo en el servidor.",
            cargando: false,
          }
          return copia
        }
        return prev
      })
      setEnviandoCsv(false)
    }, 55_000)

    try {
      const { respuesta } = await api.importacion.chat(texto, importacionContextoId ?? undefined)
      clearTimeout(timeoutId)
      setMensajesCsv((prev) => {
        const copia = [...prev]
        copia[copia.length - 1] = {
          role: "assistant",
          content: respuesta,
          cargando: false,
        }
        return copia
      })
    } catch (err) {
      clearTimeout(timeoutId)
      setMensajesCsv((prev) => {
        const copia = [...prev]
        copia[copia.length - 1] = {
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : "No se pudo consultar el chat CSV"}`,
          cargando: false,
        }
        return copia
      })
    } finally {
      setEnviandoCsv(false)
      setTimeout(() => bottomCsvRef.current?.scrollIntoView({ behavior: "smooth" }), 0)
    }
  }

  const onEliminar = async (id: string) => {
    await api.importacion.eliminar(id)
    qc.invalidateQueries({ queryKey: ["importacion-historial"] })
    toast.success("Registro eliminado")
  }

  return (
    <>
      <Topbar
        titulo="Importación CSV"
        subtitulo="Carga oportunidades desde Salesforce con control de errores, trazabilidad y chat de consulta"
      />
      <main className="flex-1 p-2.5 md:p-3.5 w-full space-y-4">

        {/* Upload + Chat en grid */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">

          {/* Panel upload */}
          <div className="ui-panel p-5 space-y-4 xl:col-span-1">
            <div>
              <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">Modo de carga</p>
              <div className="flex gap-2">
                {(["reset", "upsert", "append"] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setModo(m)}
                    className={cn(
                      "flex-1 py-2 px-3 rounded-lg border text-xs font-medium transition-colors",
                      modo === m
                        ? "bg-sgs-rojo text-white border-sgs-rojo"
                        : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-400",
                    )}
                  >
                    {m === "reset" ? "Reset" : m === "upsert" ? "Upsert" : "Append"}
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-zinc-400 mt-2">
                {modo === "reset"
                  ? "Elimina oportunidades previas y carga el CSV desde cero."
                  : modo === "upsert"
                  ? "Actualiza existentes (mismo ID) e inserta nuevas."
                  : "Solo inserta filas cuyo ID no existe aún."}
              </p>
            </div>

            <ZonaUpload onArchivo={subirArchivo} cargando={cargando} />

            {cargando && (
              <div className="flex items-center gap-2 text-sm text-zinc-500 animate-pulse">
                <span className="w-4 h-4 border-2 border-sgs-rojo border-t-transparent rounded-full animate-spin inline-block" />
                Procesando filas…
              </div>
            )}

            {resultado && <BarraProgreso resultado={resultado} />}
          </div>

          {/* Panel chat */}
          <div className="ui-panel overflow-hidden flex flex-col xl:col-span-2">
            <div className="px-5 py-3 border-b border-zinc-100">
              <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Chat de consultas</p>
              <p className="text-[11px] text-zinc-500 mt-1">
                {importacionContextoId
                  ? `Contexto activo: ${previewSeleccionada?.nombre_archivo ?? "CSV seleccionado"}`
                  : "Pulsa un CSV del historial para usarlo como contexto en el chat."}
              </p>
              {importacionContextoId && (
                <button
                  type="button"
                  onClick={() => setImportacionContextoId(null)}
                  className="mt-2 text-[11px] px-2 py-1 rounded-md border border-zinc-200 text-zinc-500 hover:border-zinc-400"
                >
                  Quitar contexto fijo
                </button>
              )}
            </div>

            <div className="flex-1 max-h-[420px] overflow-y-auto p-4 space-y-3 bg-zinc-900/95">
              {mensajesCsv.map((m, i) => (
                <BurbujaChat key={i} mensaje={m} />
              ))}
              <div ref={bottomCsvRef} />
            </div>

            <div className="p-3 border-t border-zinc-100 space-y-2">
              {previewSeleccionada && (
                <p className="text-[11px] text-zinc-500">
                  Columnas detectadas: {previewSeleccionada.columnas.slice(0, 8).join(", ")}
                  {previewSeleccionada.columnas.length > 8 ? "…" : ""}
                </p>
              )}
              <div className="flex items-end gap-2">
                <textarea
                  rows={1}
                  value={preguntaCsv}
                  onChange={(e) => setPreguntaCsv(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault()
                      enviarConsultaCsv(preguntaCsv)
                    }
                  }}
                  disabled={enviandoCsv}
                  placeholder="Pregunta sobre el contenido del CSV seleccionado…"
                  className="flex-1 resize-none rounded-lg border border-zinc-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent disabled:opacity-50 transition-colors max-h-28"
                />
                <button
                  type="button"
                  onClick={() => enviarConsultaCsv(preguntaCsv)}
                  disabled={!preguntaCsv.trim() || enviandoCsv}
                  className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-sgs-rojo transition-opacity disabled:opacity-40 inline-flex items-center gap-2 shrink-0"
                >
                  {enviandoCsv
                    ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    : "Enviar"}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Tabla historial */}
        <div className="ui-panel overflow-hidden">
          <div className="px-5 py-3 border-b border-zinc-100 flex items-center justify-between">
            <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Historial de importaciones</p>
            {historial.length > 0 && (
              <span className="text-[11px] text-zinc-400">{historial.length} registros</span>
            )}
          </div>

          {cargandoHistorial ? (
            <p className="text-sm text-zinc-400 p-5">Cargando…</p>
          ) : historial.length === 0 ? (
            <p className="text-sm text-zinc-400 p-5">Sin importaciones previas.</p>
          ) : (
            <div className="overflow-x-hidden">
              <table className="w-full table-fixed text-sm">
                <thead className="bg-zinc-50 border-b border-zinc-100">
                  <tr>
                    <th className="px-3 py-2 text-left text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">Archivo</th>
                    <th className="px-3 py-2 text-left text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">Fecha</th>
                    <th className="px-3 py-2 text-left text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">Modo</th>
                    <th className="px-3 py-2 text-left text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">Estado</th>
                    <th className="px-3 py-2 text-right text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">Total</th>
                    <th className="px-3 py-2 text-right text-[10px] font-semibold text-emerald-600 uppercase tracking-wide">Creadas</th>
                    <th className="px-3 py-2 text-right text-[10px] font-semibold text-blue-500 uppercase tracking-wide">Actualizadas</th>
                    <th className="px-3 py-2 text-right text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">Errores</th>
                    <th className="px-3 py-2 w-28 text-right text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-50">
                  {historial.map((item) => (
                    <Fragment key={item.id}>
                      <HistorialRow
                        item={item}
                        onEliminar={onEliminar}
                        contextoActivo={importacionContextoId === item.id}
                        contextoCargando={importacionContextoId === item.id && cargandoPreview}
                        onToggleContexto={(id) => {
                          setImportacionContextoId((prev) => (prev === id ? null : id))
                          setPaginaPreview(1)
                          setFiltroPreview("")
                        }}
                      />
                      {importacionContextoId === item.id && (
                        <tr>
                          <td colSpan={9} className="p-0">
                            {cargandoPreview ? (
                              <p className="text-sm text-zinc-400 p-4">Cargando datos…</p>
                            ) : !previewSeleccionada || previewSeleccionada.filas.length === 0 ? (
                              <p className="text-sm text-zinc-400 p-4">
                                Esta importación no tiene filas de preview guardadas.
                              </p>
                            ) : (
                              <div className="border-t border-zinc-100">
                                <div className="p-3 border-b border-zinc-100 bg-white">
                                  <input
                                    type="text"
                                    value={filtroPreview}
                                    onChange={(e) => {
                                      setFiltroPreview(e.target.value)
                                      setPaginaPreview(1)
                                    }}
                                    placeholder="Filtrar filas por texto…"
                                    className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
                                  />
                                  <div className="mt-2 flex items-center justify-between gap-2">
                                    <p className="text-[11px] text-zinc-500">
                                      Mostrando {filasPreviewOrdenadas.length} de {previewSeleccionada.filas.length} filas.
                                    </p>
                                    <p className="text-[10px] text-zinc-400">Tabla informativa (solo lectura)</p>
                                    <div className="flex items-center gap-2">
                                      <select
                                        value={String(porPaginaPreview)}
                                        onChange={(e) => {
                                          setPorPaginaPreview(Number(e.target.value))
                                          setPaginaPreview(1)
                                        }}
                                        className="text-[11px] px-2 py-1 rounded-md border border-zinc-200 bg-white text-zinc-600"
                                      >
                                        {[25, 50, 100].map((n) => (
                                          <option key={n} value={n}>{n} / pág</option>
                                        ))}
                                      </select>
                                      <button
                                        type="button"
                                        onClick={exportarPreviewCsv}
                                        disabled={filasPreviewFiltradas.length === 0}
                                        className="text-[11px] px-2.5 py-1 rounded-md border border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400 disabled:opacity-50"
                                      >
                                        Exportar filtrado CSV
                                      </button>
                                    </div>
                                  </div>
                                </div>
                                <div className="overflow-x-auto overflow-y-auto max-h-[320px]">
                                  <table className="min-w-full text-xs">
                                    <thead className="bg-zinc-50 sticky top-0 z-10">
                                      <tr>
                                        {previewSeleccionada.columnas.map((col) => (
                                          <th key={col} className="px-3 py-2 text-left font-semibold text-zinc-600 whitespace-nowrap">
                                            <button
                                              type="button"
                                              onClick={() => alternarOrdenColumna(col)}
                                              className="inline-flex items-center gap-1 hover:text-zinc-900"
                                              title="Ordenar por columna"
                                            >
                                              {col}
                                              {ordenColumnaPreview === col && (
                                                <span className="text-[10px]">{ordenDireccionPreview === "asc" ? "▲" : "▼"}</span>
                                              )}
                                            </button>
                                          </th>
                                        ))}
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-zinc-100">
                                      {filasPreviewPaginadas.map((fila, idx) => (
                                        <tr key={idx} className="hover:bg-zinc-50">
                                          {previewSeleccionada.columnas.map((col) => (
                                            <td key={`${idx}-${col}`} className="px-3 py-2 text-zinc-700 whitespace-nowrap">
                                              {fila[col] ?? ""}
                                            </td>
                                          ))}
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                                <div className="p-3 border-t border-zinc-100 bg-white flex items-center justify-between">
                                  <p className="text-[11px] text-zinc-500">
                                    Página {paginaPreviewAjustada} de {totalPaginasPreview}
                                  </p>
                                  <div className="flex items-center gap-1.5">
                                    <button
                                      type="button"
                                      onClick={() => setPaginaPreview((p) => Math.max(1, p - 1))}
                                      disabled={paginaPreviewAjustada <= 1}
                                      className="text-[11px] px-2.5 py-1 rounded-md border border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400 disabled:opacity-50"
                                    >
                                      Anterior
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => setPaginaPreview((p) => Math.min(totalPaginasPreview, p + 1))}
                                      disabled={paginaPreviewAjustada >= totalPaginasPreview}
                                      className="text-[11px] px-2.5 py-1 rounded-md border border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400 disabled:opacity-50"
                                    >
                                      Siguiente
                                    </button>
                                  </div>
                                </div>
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          </div>

      </main>
    </>
  )
}
