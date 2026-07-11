import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, Minus, RefreshCw } from 'lucide-react'
import { rates as ratesApi, forecasts } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Sparkline } from '@/components/ui/Sparkline'
import { useAppStore } from '@/stores/appStore'

function FxChip({
  label,
  value,
  trend,
  forecastValues,
  isLoading,
}: {
  label: string
  value: number | null | undefined
  trend: 'up' | 'down' | 'flat' | null
  forecastValues: number[]
  isLoading: boolean
}) {
  const trendColor =
    trend === 'up' ? 'text-accent-red' : trend === 'down' ? 'text-accent-green' : 'text-tertiary'

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface)] min-w-[160px]">
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-mono uppercase tracking-wider text-tertiary mb-0.5">{label}</p>
        {isLoading ? (
          <div className="h-5 w-20 bg-[var(--surface-elevated)] rounded animate-pulse" />
        ) : value != null ? (
          <p className="mono text-base font-semibold text-primary">
            Bs {value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
            <span className="text-xs text-tertiary font-normal">/USD</span>
          </p>
        ) : (
          <p className="text-sm text-tertiary">—</p>
        )}
      </div>

      {forecastValues.length > 0 && (
        <div className="w-16 h-8">
          <Sparkline
            data={forecastValues}
            color={trend === 'up' ? 'var(--accent-red)' : trend === 'down' ? 'var(--accent-green)' : 'var(--text-tertiary)'}
            height={32}
          />
        </div>
      )}

      {trend && (
        <TrendIcon className={cn('w-3.5 h-3.5 flex-shrink-0', trendColor)} />
      )}
    </div>
  )
}

export function FxForecastStrip() {
  const { setActiveTab } = useAppStore()

  const { data: latest, isLoading: rateLoading } = useQuery({
    queryKey: ['rate-latest'],
    queryFn: ratesApi.latest,
    refetchInterval: 60 * 60_000,
  })

  const { data: fxForecast, isLoading: forecastLoading } = useQuery({
    queryKey: ['fx-forecasts-strip', 7],
    queryFn: () => forecasts.fxLatest(7),
    staleTime: 30 * 60_000,
    retry: 1,
  })

  const isLoading = rateLoading

  const binanceForecast: number[] = fxForecast?.pipeline?.binance_ensemble?.forecast ?? []
  const bcvForecast: number[] = fxForecast?.pipeline?.bcv_ensemble?.forecast ?? []

  const binanceTrend =
    binanceForecast.length > 0
      ? binanceForecast[binanceForecast.length - 1] > (latest?.tasa_binance ?? 0)
        ? 'up'
        : binanceForecast[binanceForecast.length - 1] < (latest?.tasa_binance ?? 0)
        ? 'down'
        : 'flat'
      : null

  const bcvTrend =
    bcvForecast.length > 0
      ? bcvForecast[bcvForecast.length - 1] > (latest?.tasa_bcv ?? 0)
        ? 'up'
        : bcvForecast[bcvForecast.length - 1] < (latest?.tasa_bcv ?? 0)
        ? 'down'
        : 'flat'
      : null

  const spreadPct =
    latest?.tasa_binance && latest?.tasa_bcv
      ? (((latest.tasa_binance - latest.tasa_bcv) / latest.tasa_bcv) * 100).toFixed(1)
      : null

  return (
    <div
      className="flex items-center gap-3 flex-wrap cursor-pointer group"
      onClick={() => setActiveTab('macro')}
      title="View full FX analysis"
    >
      <FxChip
        label="Binance (parallel)"
        value={latest?.tasa_binance}
        trend={binanceTrend}
        forecastValues={binanceForecast}
        isLoading={isLoading}
      />
      <FxChip
        label="BCV (official)"
        value={latest?.tasa_bcv}
        trend={bcvTrend}
        forecastValues={bcvForecast}
        isLoading={isLoading}
      />

      {spreadPct && (
        <div className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--surface)]">
          <span className="text-[10px] font-mono uppercase tracking-wider text-tertiary">Spread</span>
          <span className="mono text-sm font-medium text-accent-amber">{spreadPct}%</span>
        </div>
      )}

      {!forecastLoading && binanceForecast.length === 0 && (
        <p className="text-xs text-tertiary flex items-center gap-1">
          <RefreshCw className="w-3 h-3" />
          Run forecast in Macro tab
        </p>
      )}

      <span className="text-[10px] text-tertiary hidden group-hover:inline transition-opacity">
        → Macro tab
      </span>
    </div>
  )
}
