import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { formatUSD, formatMonthYear } from '@/lib/utils'

interface MonthlyPoint {
  year: number
  month: number
  total_income_usd: number
  total_expenses_usd: number
  net_balance_usd: number
}

interface MonthlyTrendChartProps {
  data: MonthlyPoint[]
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[var(--surface-elevated)] border border-[var(--border)] rounded-lg p-3 shadow-lg text-xs space-y-1.5">
      <p className="text-secondary font-medium mb-2">{label}</p>
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

export function MonthlyTrendChart({ data }: MonthlyTrendChartProps) {
  const chartData = data.map((d) => ({
    name: formatMonthYear(d.year, d.month),
    Income: d.total_income_usd,
    Expenses: d.total_expenses_usd,
    'Net Balance': d.net_balance_usd,
  }))

  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--accent-green)" stopOpacity={0.15} />
            <stop offset="95%" stopColor="var(--accent-green)" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="expensesGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--accent-red)" stopOpacity={0.15} />
            <stop offset="95%" stopColor="var(--accent-red)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="var(--border)"
          strokeOpacity={0.5}
          vertical={false}
        />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }}
          axisLine={false}
          tickLine={false}
          dy={4}
        />
        <YAxis
          tick={{ fontSize: 11, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          width={40}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'var(--border)', strokeWidth: 1 }} />
        <Area
          type="monotone"
          dataKey="Income"
          stroke="var(--accent-green)"
          strokeWidth={1.5}
          fill="url(#incomeGrad)"
          dot={false}
          activeDot={{ r: 3, fill: 'var(--accent-green)' }}
        />
        <Area
          type="monotone"
          dataKey="Expenses"
          stroke="var(--accent-red)"
          strokeWidth={1.5}
          fill="url(#expensesGrad)"
          dot={false}
          activeDot={{ r: 3, fill: 'var(--accent-red)' }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
