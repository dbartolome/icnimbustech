"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts"
import type { ComercialRanking } from "@/types"

const fmtEUR = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 })
const fmtCompact = new Intl.NumberFormat("es-ES", { notation: "compact", maximumFractionDigits: 1 })

interface Props {
  datos: ComercialRanking[]
  comercialSeleccionado: string | null
}

interface TooltipProps {
  active?: boolean
  payload?: Array<{ name: string; value: number; dataKey: string }>
  label?: string
}

function TooltipPersonalizado({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-zinc-200 rounded-xl shadow-lg p-3 text-xs min-w-[160px]">
      <p className="font-semibold text-zinc-700 mb-2">{label}</p>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-4">
          <span className="text-zinc-500">{p.name}</span>
          <span className="font-semibold text-zinc-800">{fmtEUR.format(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

export function GraficaPipelineEquipo({ datos, comercialSeleccionado }: Props) {
  const chartData = datos.map((c) => ({
    id: c.propietario_id,
    nombre: c.nombre_completo.split(" ")[0],
    importe_ganado: Number(c.importe_ganado),
    pipeline_abierto: Number(c.pipeline_abierto),
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }} barCategoryGap="28%">
        <defs>
          <linearGradient id="gradGanado" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-sgs-rojo)" stopOpacity={1} />
            <stop offset="100%" stopColor="var(--color-sgs-rojo)" stopOpacity={0.6} />
          </linearGradient>
          <linearGradient id="gradAzul" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-sgs-azul)" stopOpacity={1} />
            <stop offset="100%" stopColor="var(--color-sgs-azul)" stopOpacity={0.6} />
          </linearGradient>
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis
          dataKey="nombre"
          tick={{ fontSize: 11, fill: "#71717a" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => fmtCompact.format(v)}
          tick={{ fontSize: 10, fill: "#71717a" }}
          axisLine={false}
          tickLine={false}
          width={52}
        />
        <Tooltip content={<TooltipPersonalizado />} cursor={{ fill: "#f4f4f5", radius: 4 }} />

        <Bar dataKey="importe_ganado" name="Ganado" radius={[4, 4, 0, 0]} maxBarSize={32}>
          {chartData.map((entry) => (
            <Cell
              key={entry.id}
              fill={entry.id === comercialSeleccionado ? "url(#gradGanado)" : "url(#gradAzul)"}
              opacity={comercialSeleccionado && entry.id !== comercialSeleccionado ? 0.3 : 1}
            />
          ))}
        </Bar>
        <Bar dataKey="pipeline_abierto" name="Pipeline abierto" radius={[4, 4, 0, 0]} maxBarSize={32} fill="#E4E4E7">
          {chartData.map((entry) => (
            <Cell
              key={entry.id}
              fill="#E4E4E7"
              opacity={comercialSeleccionado && entry.id !== comercialSeleccionado ? 0.2 : 0.8}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
