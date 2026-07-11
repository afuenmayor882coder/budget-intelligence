import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { formatUSD, formatPct } from '@/lib/utils'

interface CategoryBreakdown {
  categoria: string
  total_usd: number
  pct_of_expenses: number
}

const COLORS = [
  '#10a37f',
  '#3b82f6',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#06b6d4',
  '#f97316',
  '#ec4899',
  '#84cc16',
]

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null
  const d = payload[0]
  return (
    <div className="bg-[var(--surface-elevated)] border border-[var(--border)] rounded-lg p-3 shadow-lg text-xs">
      <p className="text-primary font-medium mb-1">{d.name}</p>
      <p className="mono text-secondary">{formatUSD(d.value)}</p>
      <p className="text-tertiary">{formatPct(d.payload.pct_of_expenses)} of total</p>
    </div>
  )
}

export function SpendingByCategoryChart({ data }: { data: CategoryBreakdown[] }) {
  const chartData = data.map((d) => ({
    name: d.categoria,
    value: d.total_usd,
    pct_of_expenses: d.pct_of_expenses,
  }))

  return (
    <div className="flex flex-col gap-4">
      <ResponsiveContainer width="100%" height={160}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={45}
            outerRadius={72}
            paddingAngle={2}
            dataKey="value"
            strokeWidth={0}
          >
            {chartData.map((_, index) => (
              <Cell key={index} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="space-y-1.5">
        {data.slice(0, 6).map((d, i) => (
          <div key={d.categoria} className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
              <span className="text-xs text-secondary truncate">{d.categoria}</span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="text-xs mono text-primary">{formatUSD(d.total_usd)}</span>
              <span className="text-xs text-tertiary w-10 text-right">{formatPct(d.pct_of_expenses)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
