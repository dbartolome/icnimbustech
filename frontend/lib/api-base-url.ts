function limpiarSlashFinal(url: string): string {
  return url.endsWith("/") ? url.slice(0, -1) : url
}

export function obtenerApiBaseUrl(): string {
  const configurada = (process.env.NEXT_PUBLIC_API_URL ?? "").trim()
  if (configurada) return limpiarSlashFinal(configurada)
  return "/api"
}
