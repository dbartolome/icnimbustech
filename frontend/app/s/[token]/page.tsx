"use client"

import { useEffect, useState } from "react"
import { use } from "react"
import { Download, FileX } from "lucide-react"
import { VistaPreviaArchivo, detectarTipoVista } from "@/components/ui/file-preview"
import { obtenerApiBaseUrl } from "@/lib/api-base-url"

const API_URL = obtenerApiBaseUrl()

type Estado = "cargando" | "listo" | "expirado" | "error"

export default function PaginaCompartido({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params)
  const [estado, setEstado] = useState<Estado>("cargando")
  const [blob, setBlob] = useState<Blob | null>(null)
  const [nombre, setNombre] = useState("")
  const [mime, setMime] = useState<string | null>(null)

  useEffect(() => {
    async function cargar() {
      try {
        const r = await fetch(`${API_URL}/s/${token}`)
        if (r.status === 404) { setEstado("expirado"); return }
        if (!r.ok) { setEstado("error"); return }

        const ct = r.headers.get("content-type") ?? ""
        const cd = r.headers.get("content-disposition") ?? ""
        const nombreMatch = cd.match(/filename="([^"]+)"/)
        const nombreFichero = nombreMatch?.[1] ?? `archivo_${token.slice(0, 8)}`

        setMime(ct.split(";")[0].trim())
        setNombre(nombreFichero)
        setBlob(await r.blob())
        setEstado("listo")
      } catch {
        setEstado("error")
      }
    }
    cargar()
  }, [token])

  function descargar() {
    if (!blob) return
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = nombre
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      {/* Header */}
      <header className="border-b border-white/10 px-6 py-4 flex items-center justify-between">
        <div>
          <span className="text-base font-bold tracking-tight text-sgs-rojo">SGS</span>
          <span className="text-xs text-zinc-500 ml-2">Inteligencia Comercial</span>
        </div>
        {estado === "listo" && (
          <button
            onClick={descargar}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-white/20 text-zinc-200 hover:bg-white/10 transition-colors"
          >
            <Download className="h-3.5 w-3.5" />
            Descargar
          </button>
        )}
      </header>

      <main className="flex-1 p-6 max-w-5xl w-full mx-auto">
        {estado === "cargando" && (
          <div className="flex items-center justify-center h-64 text-sm text-zinc-400">
            <span className="w-5 h-5 border-2 border-zinc-600 border-t-zinc-300 rounded-full animate-spin mr-3" />
            Cargando documento…
          </div>
        )}

        {(estado === "expirado" || estado === "error") && (
          <div className="flex flex-col items-center justify-center h-64 gap-4 text-center">
            <FileX className="h-12 w-12 text-zinc-600" />
            <div>
              <p className="text-sm font-semibold text-zinc-200">
                {estado === "expirado" ? "Enlace no encontrado o expirado" : "Error al cargar el documento"}
              </p>
              <p className="text-xs text-zinc-500 mt-1">
                {estado === "expirado"
                  ? "Este enlace ha caducado o ya no está disponible."
                  : "Inténtalo de nuevo más tarde."}
              </p>
            </div>
          </div>
        )}

        {estado === "listo" && blob && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <p className="text-xs text-zinc-500 uppercase tracking-widest">
                {detectarTipoVista(mime, nombre)}
              </p>
              <span className="text-zinc-700">·</span>
              <p className="text-sm font-medium text-zinc-200 truncate">{nombre}</p>
            </div>
            <VistaPreviaArchivo blob={blob} mime={mime} nombre={nombre} modo="amplia" />
          </div>
        )}
      </main>

      <footer className="border-t border-white/10 py-3 text-center text-[11px] text-zinc-600">
        SGS España · Inteligencia Comercial · Documento compartido
      </footer>
    </div>
  )
}
