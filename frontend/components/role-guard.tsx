"use client"

import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { useAppStore } from "@/store/use-app-store"
import type { PermisosUsuario } from "@/types"

function useStoreHydrated() {
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    // Cubre el caso en que la hidratación ya ocurrió antes de montar
    const alreadyHydrated = useAppStore.persist.hasHydrated()
    if (alreadyHydrated) {
      setHydrated(true)
      return
    }
    // Suscripción para cuando ocurra después
    const unsub = useAppStore.persist.onFinishHydration(() => setHydrated(true))
    return unsub
  }, [])

  return hydrated
}

interface RoleGuardProps {
  permiso?: keyof PermisosUsuario
  rolMinimo?: "admin" | "manager"
  redirigirA?: string
  children: React.ReactNode
}

export function RoleGuard({
  permiso,
  rolMinimo,
  redirigirA = "/overview",
  children,
}: RoleGuardProps) {
  const { can, isAdmin, isManager } = useAppStore()
  const router = useRouter()
  const hydrated = useStoreHydrated()

  const tieneAcceso = !hydrated || (() => {
    if (permiso) return can(permiso)
    if (rolMinimo === "admin") return isAdmin()
    if (rolMinimo === "manager") return isManager()
    return true
  })()

  useEffect(() => {
    if (hydrated && !tieneAcceso) router.replace(redirigirA)
  }, [hydrated, tieneAcceso, router, redirigirA])

  if (!hydrated) return null
  if (!tieneAcceso) return null
  return <>{children}</>
}
