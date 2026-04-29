"use client"

import { useCallback, useEffect, useMemo, useState } from "react"

export type ThemeMode = "light" | "dark" | "system"

const STORAGE_KEY = "sgs-theme-mode"

function resolverTema(modo: ThemeMode): "light" | "dark" {
  if (modo !== "system") return modo
  if (typeof window === "undefined") return "dark"
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
}

export function useTheme() {
  const [modo, setModo] = useState<ThemeMode>("dark")

  useEffect(() => {
    const guardado = localStorage.getItem(STORAGE_KEY)
    if (guardado === "light" || guardado === "dark" || guardado === "system") {
      setModo(guardado)
      return
    }
    setModo("dark")
  }, [])

  useEffect(() => {
    const temaReal = resolverTema(modo)
    document.documentElement.setAttribute("data-theme", temaReal)
    localStorage.setItem(STORAGE_KEY, modo)

    if (modo !== "system") return

    const media = window.matchMedia("(prefers-color-scheme: dark)")
    const onChange = () => {
      document.documentElement.setAttribute("data-theme", media.matches ? "dark" : "light")
    }

    media.addEventListener("change", onChange)
    return () => media.removeEventListener("change", onChange)
  }, [modo])

  const temaActivo = useMemo(() => resolverTema(modo), [modo])
  const cambiarTema = useCallback((nuevo: ThemeMode) => setModo(nuevo), [])

  return { modo, temaActivo, cambiarTema }
}
