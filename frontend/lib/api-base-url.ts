function limpiarSlashFinal(url: string): string {
  return url.endsWith("/") ? url.slice(0, -1) : url
}

function esHostLocal(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "0.0.0.0"
}

function corregirApiUrlLocal(configurada: string): string {
  if (typeof window === "undefined") {
    return configurada
  }

  try {
    const parsed = new URL(configurada)
    if (!esHostLocal(parsed.hostname)) {
      return configurada
    }
    const protocolo = window.location.protocol
    const hostReal = window.location.hostname
    const puerto = parsed.port || "8033"
    return `${protocolo}//${hostReal}:${puerto}`
  } catch {
    return configurada
  }
}

export function obtenerApiBaseUrl(): string {
  const configurada = (process.env.NEXT_PUBLIC_API_URL ?? "").trim()
  if (configurada) return limpiarSlashFinal(corregirApiUrlLocal(configurada))
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8033`
  }
  return "/api"
}
