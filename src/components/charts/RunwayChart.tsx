import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine } from 'recharts'
import { formatUSD } from '@/lib/utils'

interface ProjectionPoint {
  date: string
  balance_usd: number
}

interface RunwayChartProps {
  noIncome: ProjectionPoint[]
  withIncome: ProjectionPoint[]
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[var(--surface-elevated)] border border-[var(--border)] rounded-lg p-3 shadow-lg text-xs space-y-1.5">
      <p className="text-secondary font-medium mb-1">{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ background: p.color }} />
            <span className="text-secondary">{p.name}</span>
          </div>
          <span className="mono text-primary font-medium">{formatUSD(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

export function RunwayChart({ noIncome, withIncome }: RunwayChartProps) {
  const allDates = [...new Set([...noIncome.map((d) => d.date), ...withIncome.map((d) => d.date)])].sort()

  const noIncomeMap = Object.fromEntries(noIncome.map((d) => [d.date, d.balance_usd]))
  const withIncomeMap = Object.fromEntries(withIncome.map((d) => [d.date, d.balance_usd]))

  const chartData = allDates.map((date) => ({
    date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    'No Income': noIncomeMap[date] ?? null,
    'With Income': withIncomeMap[date] ?? null,
  }))

  const sample = chartData.filter((_, i) => i % Math.max(1, Math.floor(chartData.length / 8)) === 0)

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={sample} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="runwayGradNoIncome" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--accent-amber)" stopOpacity={0.15} />
            <stop offset="95%" stopColor="var(--accent-amber)" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="runwayGradWithIncome" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--accent-green)" stopOpacity={0.15} />
            <stop offset="95%" stopColor="var(--accent-green)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          width={36}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'var(--border)', strokeWidth: 1 }} />
        <ReferenceLine y={0} stroke="var(--accent-red)" strokeDasharray="4 2" strokeWidth={1} strokeOpacity={0.6} />
        <Area
          type="monotone"
          dataKey="No Income"
          stroke="var(--accent-amber)"
          strokeWidth={1.5}
          fill="url(#runwayGradNoIncome)"
          dot={false}
          connectNulls
        />
        <Area
          type="monotone"
          dataKey="With Income"
          stroke="var(--accent-green)"
          strokeWidth={1.5}
          fill="url(#runwayGradWithIncome)"
          dot={false}
          connectNulls
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
