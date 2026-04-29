"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useParams } from "next/navigation"
import { RoleGuard } from "@/components/role-guard"
import { Topbar } from "@/components/layout/topbar"
import { api } from "@/lib/api"
import { formatearPorcentaje } from "@/lib/utils"

type EstadisticasComercial = {
  nombre_completo: string
  win_rate: number
  oportunidades_perdidas: number
}

type ClienteBusqueda = {
  id: string
  nombre: string
}

export default function CoachingComercialPage() {
  const params = useParams<{ id: string }>()
  const usuarioId = params.id
  const [busquedaCuenta, setBusquedaCuenta] = useState("")
  const [cuentaSeleccionada, setCuentaSeleccionada] = useState<ClienteBusqueda | null>(null)

  const { data: estadisticas, isLoading: loadingEstadisticas } = useQuery<EstadisticasComercial>({
    queryKey: ["equipo-estadisticas", usuarioId],
    queryFn: () => api.equipo.estadisticas(usuarioId) as Promise<EstadisticasComercial>,
    enabled: Boolean(usuarioId),
  })

  const { data: historial = [], isLoading: loadingHistorial, refetch } = useQuery({
    queryKey: ["coaching-historial", usuarioId],
    queryFn: () => api.coaching.historial(usuarioId),
    enabled: Boolean(usuarioId),
  })

  const { data: cuentasBusqueda = [], isLoading: loadingCuentas } = useQuery<ClienteBusqueda[]>({
    queryKey: ["coaching-buscar-cuentas", busquedaCuenta],
    queryFn: async () => {
      if (busquedaCuenta.trim().length < 2) return []
      const respuesta = await api.clientes.listar({ busqueda: busquedaCuenta, pagina: 1, por_pagina: 8 })
      const datos = (respuesta as { datos?: Array<{ id: string; nombre: string }> }).datos ?? []
      return datos.map((d) => ({ id: d.id, nombre: d.nombre }))
    },
    enabled: busquedaCuenta.trim().length >= 2,
  })

  async function analizarNotas() {
    const cuentaObjetivo = cuentaSeleccionada?.id || (historial.find((h) => h.cuenta_id)?.cuenta_id as string | undefined)
    if (!cuentaObjetivo) return
    await api.coaching.analizarNotas(cuentaObjetivo)
    await refetch()
  }

  async function generarPlan() {
    await api.coaching.recomendaciones(usuarioId)
    await refetch()
  }

  return (
    <RoleGuard rolMinimo="manager">
      <Topbar titulo="Coaching Comercial" subtitulo="Análisis y plan de mejora del comercial" />

      <main className="flex-1 p-2.5 md:p-3.5 space-y-5">
        <div className="bg-white border border-zinc-200 rounded-xl p-4">
          {loadingEstadisticas ? (
            <p className="text-sm text-zinc-500">Cargando métricas...</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="rounded-lg bg-zinc-50 p-3">
                <p className="text-xs text-zinc-500">Comercial</p>
                <p className="text-sm font-semibold text-zinc-900 mt-0.5">{estadisticas?.nombre_completo ?? "N/D"}</p>
              </div>
              <div className="rounded-lg bg-zinc-50 p-3">
                <p className="text-xs text-zinc-500">Win Rate</p>
                <p className="text-sm font-semibold text-zinc-900 mt-0.5">{formatearPorcentaje(estadisticas?.win_rate ?? 0)}</p>
              </div>
              <div className="rounded-lg bg-zinc-50 p-3">
                <p className="text-xs text-zinc-500">Oportunidades perdidas</p>
                <p className="text-sm font-semibold text-zinc-900 mt-0.5">{estadisticas?.oportunidades_perdidas ?? 0}</p>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white border border-zinc-200 rounded-xl p-4 space-y-3">
          <div className="space-y-2">
            <input
              value={busquedaCuenta}
              onChange={(e) => {
                setBusquedaCuenta(e.target.value)
                setCuentaSeleccionada(null)
              }}
              placeholder="Buscar cuenta por nombre..."
              className="w-full px-3 py-1.5 text-xs border border-zinc-200 rounded-md focus:outline-none focus:ring-2 focus:ring-sgs-rojo"
            />
            {cuentaSeleccionada ? (
              <p className="text-xs text-zinc-600">
                Cuenta seleccionada: <span className="font-medium">{cuentaSeleccionada.nombre}</span>
              </p>
            ) : null}
            {loadingCuentas ? (
              <p className="text-xs text-zinc-400">Buscando cuentas...</p>
            ) : cuentasBusqueda.length > 0 && !cuentaSeleccionada ? (
              <div className="border border-zinc-200 rounded-md max-h-36 overflow-y-auto">
                {cuentasBusqueda.map((cuenta) => (
                  <button
                    key={cuenta.id}
                    onClick={() => {
                      setCuentaSeleccionada(cuenta)
                      setBusquedaCuenta(cuenta.nombre)
                    }}
                    className="w-full text-left px-3 py-2 text-xs hover:bg-zinc-50 border-b border-zinc-100 last:border-b-0"
                  >
                    {cuenta.nombre}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={analizarNotas}
              disabled={!cuentaSeleccionada && !historial.find((h) => h.cuenta_id)}
              className="px-3 py-1.5 text-xs font-medium rounded-md border border-zinc-200 text-zinc-700 hover:bg-zinc-50"
            >
              Analizar notas recientes
            </button>
            <button
              onClick={generarPlan}
              className="px-3 py-1.5 text-xs font-medium rounded-md bg-sgs-rojo text-white hover:bg-sgs-rojo/90"
            >
              Generar plan semanal
            </button>
          </div>

          {loadingHistorial ? (
            <p className="text-sm text-zinc-500">Cargando historial...</p>
          ) : historial.length === 0 ? (
            <p className="text-sm text-zinc-500">Sin sesiones de coaching todavía.</p>
          ) : (
            <div className="space-y-2">
              {historial.map((sesion) => (
                <div key={sesion.id} className="border border-zinc-100 rounded-lg p-3 bg-zinc-50">
                  <p className="text-xs font-semibold text-zinc-700 uppercase">{sesion.tipo}</p>
                  <p className="text-xs text-zinc-500 mt-0.5">{sesion.creado_en}</p>
                  <pre className="mt-2 text-xs text-zinc-700 whitespace-pre-wrap">
                    {JSON.stringify(sesion.resultado, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </RoleGuard>
  )
}
