"use client"

import { useEffect, useRef, useState } from "react"
import { Check, Copy, Mail, Share2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { obtenerApiBaseUrl } from "@/lib/api-base-url"

const API_URL = obtenerApiBaseUrl()

interface BotonCompartirArtefactoProps {
  obtenerToken: () => Promise<{ token: string }>
  titulo: string
  className?: string
}

type Estado = "idle" | "cargando" | "listo"

export function BotonCompartirArtefacto({ obtenerToken, titulo, className }: BotonCompartirArtefactoProps) {
  const [estado, setEstado] = useState<Estado>("idle")
  const [url, setUrl] = useState<string | null>(null)
  const [copiado, setCopiado] = useState(false)
  const [abierto, setAbierto] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!abierto) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setAbierto(false)
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [abierto])

  async function obtenerEnlace() {
    if (estado === "cargando") return
    if (url) { setAbierto(true); return }

    setEstado("cargando")
    try {
      const { token } = await obtenerToken()
      const apiBase = API_URL.startsWith("/")
        ? `${window.location.origin}${API_URL}`
        : API_URL
      const enlace = `${apiBase}/s/${token}`
      setUrl(enlace)
      setEstado("listo")
      setAbierto(true)
    } catch {
      setEstado("idle")
    }
  }

  async function copiar() {
    if (!url) return
    await navigator.clipboard.writeText(url)
    setCopiado(true)
    setTimeout(() => setCopiado(false), 2000)
  }

  function abrirWhatsApp() {
    if (!url) return
    const texto = encodeURIComponent(`Te comparto este artefacto de SGS España:\n${titulo}\n${url}`)
    window.open(`https://wa.me/?text=${texto}`, "_blank")
  }

  function abrirEmail() {
    if (!url) return
    const asunto = encodeURIComponent(`SGS · ${titulo}`)
    const cuerpo = encodeURIComponent(`Te comparto este artefacto de Inteligencia Comercial SGS España:\n\n${titulo}\n${url}\n\nEste enlace es válido durante 7 días.`)
    window.open(`mailto:?subject=${asunto}&body=${cuerpo}`, "_blank")
  }

  return (
    <div ref={ref} className={cn("relative", className)}>
      <button
        onClick={obtenerEnlace}
        disabled={estado === "cargando"}
        title="Compartir"
        className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-white/10 transition-colors disabled:opacity-50"
      >
        {estado === "cargando" ? (
          <span className="block w-3.5 h-3.5 border-2 border-zinc-500 border-t-zinc-200 rounded-full animate-spin" />
        ) : (
          <Share2 className="w-3.5 h-3.5" />
        )}
      </button>

      {abierto && url && (
        <div className="absolute right-0 bottom-full mb-2 z-50 w-72 rounded-xl border border-white/10 bg-zinc-900 shadow-xl p-3 space-y-2">
          <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-400 font-semibold">Compartir enlace</p>

          <div className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-black/30 px-2.5 py-1.5">
            <span className="flex-1 text-[11px] text-zinc-300 truncate">{url}</span>
            <button
              onClick={copiar}
              className="shrink-0 p-1 rounded text-zinc-400 hover:text-white transition-colors"
              title="Copiar enlace"
            >
              {copiado ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            <button
              onClick={abrirWhatsApp}
              className="flex items-center justify-center gap-1.5 px-2.5 py-2 rounded-lg border border-white/10 bg-white/5 text-xs text-zinc-200 hover:bg-[#25D366]/20 hover:border-[#25D366]/40 hover:text-[#25D366] transition-colors"
            >
              <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current" aria-hidden>
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
              </svg>
              WhatsApp
            </button>
            <button
              onClick={abrirEmail}
              className="flex items-center justify-center gap-1.5 px-2.5 py-2 rounded-lg border border-white/10 bg-white/5 text-xs text-zinc-200 hover:bg-blue-500/20 hover:border-blue-400/40 hover:text-blue-300 transition-colors"
            >
              <Mail className="w-3.5 h-3.5" />
              Email
            </button>
          </div>

          <p className="text-[10px] text-zinc-500 text-center">Enlace válido 7 días · Solo lectura</p>
        </div>
      )}
    </div>
  )
}
