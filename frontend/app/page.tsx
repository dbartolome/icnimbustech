"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAppStore } from "@/store/use-app-store"

export default function PaginaInicio() {
  const router = useRouter()
  const usuarioActual = useAppStore((s) => s.usuarioActual)

  useEffect(() => {
    if (!usuarioActual) {
      // La store aún no se ha hidratado o no hay sesión —
      // el middleware ya debería haber redirigido a /login
      return
    }

    router.replace("/overview")
  }, [usuarioActual, router])

  // Spinner mínimo mientras hidrata la store
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-5 h-5 rounded-full border-2 border-zinc-300 border-t-sgs-rojo animate-spin" />
    </div>
  )
}
