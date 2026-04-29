"use client"

import { useState, useRef, useEffect } from "react"
import { cn } from "@/lib/utils"
import { Topbar } from "@/components/layout/topbar"
import { api } from "@/lib/api"
import { useAppStore } from "@/store/use-app-store"

interface Mensaje {
  role: "user" | "assistant"
  content: string
  cargando?: boolean
}

const SUGERENCIAS = [
  "¿Cuáles son los productos con mejor win rate?",
  "¿Qué etapas del funnel tienen más oportunidades en riesgo?",
  "Resume el estado actual del pipeline comercial",
  "¿Qué acciones recomiendas para mejorar el win rate?",
]

function BurbujaMensaje({ mensaje }: { mensaje: Mensaje }) {
  const esUsuario = mensaje.role === "user"
  return (
    <div className={`flex ${esUsuario ? "justify-end" : "justify-start"}`}>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          esUsuario
            ? "bg-sgs-rojo text-white rounded-br-sm"
            : "bg-white border border-zinc-200 text-zinc-800 rounded-bl-sm"
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

export default function PaginaCopilot() {
  const [mensajes, setMensajes] = useState<Mensaje[]>([
    {
      role: "assistant",
      content:
        "Hola. Soy el Copilot de Inteligencia Comercial de SGS España. Tengo acceso en tiempo real al pipeline, catálogo de servicios y datos de cuentas. ¿En qué te puedo ayudar?",
    },
  ])
  const [entrada, setEntrada] = useState("")
  const [enviando, setEnviando] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const iaConfig = useAppStore((s) => s.iaConfigs.copilot)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [mensajes])

  async function enviar(texto: string) {
    if (!texto.trim() || enviando) return

    const mensajeUsuario: Mensaje = { role: "user", content: texto.trim() }
    const historialActualizado = [...mensajes, mensajeUsuario]

    setMensajes([...historialActualizado, { role: "assistant", content: "", cargando: true }])
    setEntrada("")
    setEnviando(true)

    try {
      const historialParaApi = historialActualizado.map((m) => ({
        role: m.role,
        content: m.content,
      }))

      const respuesta = await api.ia.chatStream(historialParaApi, iaConfig)

      if (!respuesta.ok) {
        const err = await respuesta.json().catch(() => ({ detail: "Error de conexión" }))
        throw new Error(err.detail ?? "Error del servidor")
      }

      const reader = respuesta.body!.getReader()
      const decoder = new TextDecoder()
      let textoAcumulado = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const lineas = decoder.decode(value).split("\n")
        for (const linea of lineas) {
          if (!linea.startsWith("data: ")) continue
          const dato = linea.slice(6)
          if (dato === "[DONE]") break
          if (dato.startsWith("[ERROR]")) {
            textoAcumulado = dato.replace("[ERROR] ", "Error: ")
            break
          }
          textoAcumulado += dato
        }

        setMensajes((prev) => {
          const copia = [...prev]
          copia[copia.length - 1] = {
            role: "assistant",
            content: textoAcumulado,
            cargando: false,
          }
          return copia
        })
      }
    } catch (err) {
      setMensajes((prev) => {
        const copia = [...prev]
        copia[copia.length - 1] = {
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : "No se pudo conectar con el copilot"}`,
          cargando: false,
        }
        return copia
      })
    } finally {
      setEnviando(false)
      textareaRef.current?.focus()
    }
  }

  function manejarTecla(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      enviar(entrada)
    }
  }

  return (
    <>
      <Topbar titulo="IC Copilot" subtitulo="Asistente de Inteligencia Comercial · Claude Sonnet" />

      <main className="flex-1 flex flex-col overflow-hidden" style={{ height: "calc(100vh - 57px)" }}>
        {/* ── Historial ── */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4 bg-zinc-50">
          {mensajes.map((m, i) => (
            <BurbujaMensaje key={i} mensaje={m} />
          ))}
          <div ref={bottomRef} />
        </div>

        {/* ── Sugerencias (solo al inicio) ── */}
        {mensajes.length <= 1 && (
          <div className="px-6 pb-3 flex flex-wrap gap-2 bg-zinc-50">
            {SUGERENCIAS.map((s) => (
              <button
                key={s}
                onClick={() => enviar(s)}
                className="text-xs px-3 py-1.5 rounded-full border border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400 hover:text-zinc-900 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* ── Input ── */}
        <div className="bg-white border-t border-zinc-200 px-6 py-4">
          <div className="flex items-end gap-3 w-full">
            <textarea
              ref={textareaRef}
              rows={1}
              value={entrada}
              onChange={(e) => setEntrada(e.target.value)}
              onKeyDown={manejarTecla}
              disabled={enviando}
              placeholder="Escribe tu pregunta… (Enter para enviar, Shift+Enter para nueva línea)"
              className="flex-1 resize-none rounded-xl border border-zinc-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-sgs-rojo focus:border-transparent disabled:opacity-50 transition-colors max-h-32"
            />
            <button
              onClick={() => enviar(entrada)}
              disabled={!entrada.trim() || enviando}
              className="px-4 py-3 rounded-xl text-sm font-medium text-white bg-sgs-rojo transition-opacity disabled:opacity-40 flex items-center gap-2"
            >
              {enviando ? (
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
              )}
              Enviar
            </button>
          </div>
          <p className="text-center text-xs text-zinc-400 mt-2">
            Powered by Claude Sonnet · Los datos son del pipeline real de SGS España
          </p>
        </div>
      </main>
    </>
  )
}
