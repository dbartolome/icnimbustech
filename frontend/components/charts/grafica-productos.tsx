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
  ReferenceLine,
} from "recharts"
import type { ProductoAnalisis } from "@/types"

interface Props {
  datos: ProductoAnalisis[]
}

function TooltipPersonalizado({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ value: number }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  const wr = payload[0].value
  return (
    <div className="bg-white border border-zinc-200 rounded-lg shadow-md p-3 text-xs">
      <p className="font-semibold text-zinc-800 mb-1">{label}</p>
      <p style={{ color: wr >= 80 ? "var(--color-sgs-verde)" : wr >= 60 ? "var(--color-sgs-ambar)" : "var(--color-sgs-rojo)" }}>
        Win Rate: {wr.toFixed(1)}%
      </p>
    </div>
  )
}

function colorBarra(wr: number): string {
  if (wr >= 80) return "var(--color-sgs-verde)"
  if (wr >= 60) return "var(--color-sgs-ambar)"
  return "var(--color-sgs-rojo)"
}

export function GraficaProductos({ datos }: Props) {
  const chartData = datos
    .filter((p) => p.total_oportunidades > 0)
    .map((p) => ({
      nombre: p.nombre.length > 20 ? p.nombre.slice(0, 18) + "…" : p.nombre,
      win_rate: Number(p.win_rate),
    }))

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis
          dataKey="nombre"
          tick={{ fontSize: 10, fill: "#71717a" }}
          axisLine={false}
          tickLine={false}
          angle={-35}
          textAnchor="end"
          interval={0}
        />
        <YAxis
          domain={[0, 100]}
          tickFormatter={(v: number) => `${v}%`}
          tick={{ fontSize: 10, fill: "#71717a" }}
          axisLine={false}
          tickLine={false}
          width={38}
        />
        <Tooltip content={<TooltipPersonalizado />} cursor={{ fill: "#f4f4f5" }} />
        <ReferenceLine y={80} stroke="#e2e8f0" strokeDasharray="4 4" label={{ value: "80%", position: "right", fontSize: 9, fill: "#94a3b8" }} />
        <Bar dataKey="win_rate" name="Win Rate" radius={[4, 4, 0, 0]} maxBarSize={44}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={colorBarra(entry.win_rate)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
