/**
 * Cliente HTTP compartido del frontend.
 * Centraliza autenticación, refresh de sesión y manejo de errores HTTP.
 */

import { obtenerApiBaseUrl } from "@/lib/api-base-url"

type JsonLike = Record<string, unknown> | unknown[] | null

/**
 * Lee el access token desde localStorage.
 * Devuelve null en entorno server-side.
 */
export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null
  }
  return localStorage.getItem("access_token")
}

function persistToken(accessToken: string): void {
  if (typeof window === "undefined") {
    return
  }
  localStorage.setItem("access_token", accessToken)
}

function clearTokenAndRedirectToLogin(): never {
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token")
    window.location.href = "/login"
  }
  throw new Error("Sesión expirada")
}

async function refreshSessionOrFail(): Promise<void> {
  const refreshResponse = await fetch(`${obtenerApiBaseUrl()}/auth/refresh`, {
    method: "POST",
    credentials: "include",
  })

  if (!refreshResponse.ok) {
    clearTokenAndRedirectToLogin()
  }

  const payload = (await refreshResponse.json()) as { access_token: string }
  persistToken(payload.access_token)
}

function createHeaders(options: RequestInit, withJsonContentType: boolean): HeadersInit {
  const token = getAccessToken()
  return {
    ...(withJsonContentType ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }
}

async function parseHttpError(response: Response): Promise<Error> {
  const fallbackMessage = `Error ${response.status}`
  const payload = await response.json().catch(() => ({ detail: "Error desconocido" } as JsonLike))
  const detail =
    typeof payload === "object" && payload && "detail" in payload
      ? String((payload as Record<string, unknown>).detail)
      : fallbackMessage
  return new Error(detail || fallbackMessage)
}

/**
 * Ejecuta una petición y reintenta una sola vez si recibe 401.
 */
async function requestWithRefresh(
  path: string,
  options: RequestInit = {},
  withJsonContentType = true,
  retried = false,
): Promise<Response> {
  const apiBaseUrl = obtenerApiBaseUrl()
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    credentials: "include",
    headers: createHeaders(options, withJsonContentType),
  })

  if (response.status === 401 && !retried) {
    await refreshSessionOrFail()
    return requestWithRefresh(path, options, withJsonContentType, true)
  }

  if (!response.ok) {
    throw await parseHttpError(response)
  }

  return response
}

/**
 * Petición JSON tipada para la API principal.
 */
export async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await requestWithRefresh(path, options, true)
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

/**
 * Petición RAW para FormData o descargas binarias.
 */
export function requestRaw(path: string, options: RequestInit = {}): Promise<Response> {
  return requestWithRefresh(path, options, false)
}

/**
 * Descarga un blob vía API autenticada y dispara descarga en navegador.
 */
export async function downloadFromApi(path: string, filename: string, options: RequestInit = {}): Promise<void> {
  const response = await requestRaw(path, options)
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

/**
 * Abre un blob en una nueva pestaña para previsualización.
 * Útil para PDF/imagenes/documentos cuando se necesita auth por cabecera.
 */
export async function openFromApi(path: string, options: RequestInit = {}): Promise<void> {
  const response = await requestRaw(path, options)
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const win = window.open(url, "_blank", "noopener,noreferrer")
  if (!win) {
    URL.revokeObjectURL(url)
    throw new Error("El navegador bloqueó la apertura de la vista previa.")
  }
  // Damos margen para que el navegador cargue el blob antes de revocar.
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
}
