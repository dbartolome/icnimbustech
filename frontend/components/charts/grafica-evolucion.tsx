"use client"

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import type { PuntoEvolucion } from "@/types"

const fmt = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0 })

interface TooltipProps {
  active?: boolean
  payload?: Array<{ name: string; value: number; color: string }>
  label?: string
}

function TooltipEvolucion({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-zinc-200 rounded-xl shadow-lg p-3 text-xs min-w-[140px]">
      <p className="font-semibold text-zinc-700 mb-2">{label}</p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-zinc-500">
            <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
            {p.name}
          </span>
          <span className="font-semibold text-zinc-800">{fmt.format(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

interface GraficaEvolucionProps {
  datos: PuntoEvolucion[]
}

export function GraficaEvolucion({ datos }: GraficaEvolucionProps) {
  const datosConFormato = datos.map((d) => ({
    ...d,
    mes: d.mes.slice(5),
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={datosConFormato} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="gradCreadas" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#E4E4E7" stopOpacity={0.6} />
            <stop offset="95%" stopColor="#E4E4E7" stopOpacity={0.05} />
          </linearGradient>
          <linearGradient id="gradGanadas" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--color-sgs-verde)" stopOpacity={0.35} />
            <stop offset="95%" stopColor="var(--color-sgs-verde)" stopOpacity={0.02} />
          </linearGradient>
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="#F4F4F5" vertical={false} />
        <XAxis
          dataKey="mes"
          tick={{ fontSize: 11, fill: "#71717A" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "#71717A" }}
          axisLine={false}
          tickLine={false}
          width={40}
          tickFormatter={(v: number) =>
            new Intl.NumberFormat("es-ES", { notation: "compact", maximumFractionDigits: 0 }).format(v)
          }
        />
        <Tooltip content={<TooltipEvolucion />} cursor={{ stroke: "#E4E4E7", strokeWidth: 1 }} />

        <Area
          type="monotone"
          dataKey="total_creadas"
          name="Creadas"
          stroke="#A1A1AA"
          strokeWidth={1.5}
          fill="url(#gradCreadas)"
          dot={false}
          activeDot={{ r: 4, fill: "#A1A1AA" }}
        />
        <Area
          type="monotone"
          dataKey="ganadas"
          name="Ganadas"
          stroke="var(--color-sgs-verde)"
          strokeWidth={2}
          fill="url(#gradGanadas)"
          dot={false}
          activeDot={{ r: 4, fill: "var(--color-sgs-verde)" }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
