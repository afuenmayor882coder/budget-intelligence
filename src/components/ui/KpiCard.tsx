import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn, formatPct } from '@/lib/utils'
import { Sparkline } from './Sparkline'
import { Skeleton } from './Skeleton'

interface KpiCardProps {
  label: string
  value: string
  delta?: number
  deltaLabel?: string
  sparklineData?: number[]
  loading?: boolean
  invertDelta?: boolean
  className?: string
  sublabel?: string
}

export function KpiCard({
  label,
  value,
  delta,
  deltaLabel,
  sparklineData,
  loading,
  invertDelta = false,
  className,
  sublabel,
}: KpiCardProps) {
  if (loading) {
    return (
      <div className={cn('bg-surface border border-[var(--border)] rounded-xl p-4', className)}>
        <Skeleton className="h-3 w-24 mb-3" />
        <Skeleton className="h-8 w-32 mb-2" />
        <Skeleton className="h-3 w-16" />
      </div>
    )
  }

  const isPositive = delta !== undefined && delta > 0
  const isNegative = delta !== undefined && delta < 0
  const deltaColor = delta === undefined || delta === 0
    ? 'text-secondary'
    : invertDelta
      ? (isPositive ? 'text-accent-red' : 'text-accent-green')
      : (isPositive ? 'text-accent-green' : 'text-accent-red')

  return (
    <div className={cn('bg-surface border border-[var(--border)] rounded-xl p-4 flex flex-col gap-1', className)}>
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium text-secondary uppercase tracking-wider">{label}</p>
        {sparklineData && sparklineData.length > 1 && (
          <Sparkline data={sparklineData} color="auto" width={60} height={24} />
        )}
      </div>
      <p className="mono text-2xl font-semibold text-primary tracking-tight">{value}</p>
      <div className="flex items-center gap-1.5 mt-0.5">
        {delta !== undefined && (
          <>
            {isPositive && <TrendingUp className={cn('w-3 h-3', deltaColor)} />}
            {isNegative && <TrendingDown className={cn('w-3 h-3', deltaColor)} />}
            {delta === 0 && <Minus className="w-3 h-3 text-secondary" />}
            <span className={cn('text-xs font-medium mono', deltaColor)}>
              {formatPct(Math.abs(delta), false)}
            </span>
          </>
        )}
        {deltaLabel && (
          <span className="text-xs text-tertiary">{deltaLabel}</span>
        )}
      </div>
      {sublabel && <p className="text-xs text-tertiary mt-0.5">{sublabel}</p>}
    </div>
  )
}
