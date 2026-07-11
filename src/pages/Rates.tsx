import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { RefreshCw, AlertCircle, CheckCircle, Clock } from 'lucide-react'
import { rates as ratesApi } from '@/lib/api'
import { formatDate, formatNumber, cn } from '@/lib/utils'
import { Card, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { SectionAnalysis } from '@/components/ui/SectionAnalysis'
import { toast } from 'sonner'

export function RatesPage() {
  const [syncing, setSyncing] = useState(false)

  const { data: latest, refetch: refetchLatest } = useQuery({
    queryKey: ['rates-latest'],
    queryFn: ratesApi.latest,
    refetchInterval: 300_000,
  })

  const { data: history = [], isLoading } = useQuery({
    queryKey: ['rates-history'],
    queryFn: () => ratesApi.list({ limit: 365 }),
  })

  const { data: gapData } = useQuery({
    queryKey: ['rates-gap'],
    queryFn: () => ratesApi.gap(12),
    staleTime: 10 * 60_000,
  })

  const { data: volatility } = useQuery({
    queryKey: ['rates-volatility'],
    queryFn: () => ratesApi.volatility(30),
    staleTime: 10 * 60_000,
  })

  const { data: syncStatus } = useQuery({
    queryKey: ['rates-sync-status'],
    queryFn: ratesApi.syncStatus,
    refetchInterval: 30_000,
  })

  const handleSync = async () => {
    setSyncing(true)
    try {
      const result = await ratesApi.sync()
      toast.success(`Sync complete — ${result.inserted ?? 0} new records`)
      refetchLatest()
    } catch (err: any) {
      toast.error(err.message ?? 'Sync failed')
    } finally {
      setSyncing(false)
    }
  }

  const chartData = (history as any[]).slice(-180).map((r: any) => ({
    date: r.fecha,
    Binance: r.tasa_binance,
    BCV: r.tasa_bcv,
  }))

  const gapChartData = (gapData?.series ?? []).slice(-12).map((d: any) => ({
    name: d.month ?? d.fecha?.slice(0, 7),
    'Gap %': d.gap_pct ?? d.dif_pct_paralelo,
  }))

  const isStale = latest?.is_stale
  const syncedAt = syncStatus?.last_sync_at ? new Date(syncStatus.last_sync_at).toLocaleString() : null

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-primary">Exchange Rates</h1>
          <p className="text-sm text-secondary mt-1">BCV official and Binance P2P parallel rate</p>
        </div>
        <div className="flex items-center gap-2">
          {isStale ? (
            <Badge variant="red" dot>Stale</Badge>
          ) : latest?.fecha ? (
            <Badge variant="green" dot>{formatDate(latest.fecha)}</Badge>
          ) : null}
          <Button
            variant="outline"
            size="sm"
            icon={<RefreshCw className={cn('w-3.5 h-3.5', syncing && 'animate-spin')} />}
            onClick={handleSync}
            loading={syncing}
          >
            Sync Now
          </Button>
        </div>
      </div>

      {/* Sync status bar */}
      {syncStatus && (
        <div className={cn(
          'flex items-center gap-3 px-4 py-2.5 rounded-xl border text-xs',
          syncStatus.status === 'ok'
            ? 'border-[var(--accent-green)] bg-[var(--accent-green-muted)] text-accent-green'
            : syncStatus.status === 'stale'
            ? 'border-[var(--accent-amber)] bg-[var(--surface)] text-accent-amber'
            : 'border-[var(--border)] bg-[var(--surface)] text-secondary'
        )}>
          {syncStatus.status === 'ok'
            ? <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
            : syncStatus.status === 'stale'
            ? <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            : <Clock className="w-3.5 h-3.5 flex-shrink-0" />
          }
          <span>
            {syncStatus.status === 'ok' && `Rate data is current · last sync ${syncedAt ?? '—'}`}
            {syncStatus.status === 'stale' && `Rate data may be stale · last sync ${syncedAt ?? 'never'}`}
            {!['ok', 'stale'].includes(syncStatus.status) && `Sync status: ${syncStatus.status}`}
          </span>
          {syncStatus.source && (
            <span className="ml-auto opacity-60">source: {syncStatus.source}</span>
          )}
        </div>
      )}

      {/* Current rate cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Card padding="md">
          <p className="text-xs text-tertiary uppercase tracking-wider mb-2">Binance P2P</p>
          <p className="mono text-2xl font-semibold text-primary">
            {latest?.tasa_binance ? formatNumber(latest.tasa_binance, 2) : '—'}
          </p>
          <p className="text-xs text-tertiary mt-1">VES / USD</p>
        </Card>
        <Card padding="md">
          <p className="text-xs text-tertiary uppercase tracking-wider mb-2">BCV Official</p>
          <p className="mono text-2xl font-semibold text-primary">
            {latest?.tasa_bcv ? formatNumber(latest.tasa_bcv, 2) : '—'}
          </p>
          <p className="text-xs text-tertiary mt-1">VES / USD</p>
        </Card>
        {latest?.dif_pct_paralelo !== undefined && (
          <Card padding="md">
            <p className="text-xs text-tertiary uppercase tracking-wider mb-2">Gap (Parallel Premium)</p>
            <p className="mono text-2xl font-semibold text-accent-amber">
              {formatNumber(Math.abs(latest.dif_pct_paralelo), 1)}%
            </p>
            <p className="text-xs text-tertiary mt-1">Binance vs BCV</p>
          </Card>
        )}
        {volatility?.annualized_volatility_pct != null && (
          <Card padding="md">
            <p className="text-xs text-tertiary uppercase tracking-wider mb-2">30-Day Volatility</p>
            <p className={cn(
              'mono text-2xl font-semibold',
              volatility.annualized_volatility_pct > 100 ? 'text-accent-red'
                : volatility.annualized_volatility_pct > 50 ? 'text-accent-amber'
                : 'text-accent-green'
            )}>
              {formatNumber(volatility.annualized_volatility_pct, 0)}%
            </p>
            <p className="text-xs text-tertiary mt-1">Annualized</p>
          </Card>
        )}
      </div>

      {/* Rate history chart */}
      <Card padding="md">
        <CardHeader>
          <CardTitle>Rate History (Last 6 Months)</CardTitle>
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-[var(--accent-green)]" />
              <span className="text-secondary">Binance</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-[var(--accent-blue)]" />
              <span className="text-secondary">BCV</span>
            </div>
          </div>
        </CardHeader>
        {isLoading ? (
          <Skeleton className="h-56 w-full" />
        ) : chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="binanceGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--accent-green)" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="var(--accent-green)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="bcvGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }}
                axisLine={false}
                tickLine={false}
                interval={Math.floor(chartData.length / 6)}
                tickFormatter={(v) => v?.slice(0, 7) ?? ''}
              />
              <YAxis
                tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }}
                axisLine={false}
                tickLine={false}
                width={50}
                tickFormatter={(v) => formatNumber(v, 0)}
              />
              <Tooltip
                contentStyle={{ background: 'var(--surface-elevated)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }}
                formatter={(v: any) => [formatNumber(Number(v), 2) + ' Bs']}
                labelFormatter={(l) => formatDate(l)}
              />
              <Area type="monotone" dataKey="Binance" stroke="var(--accent-green)" strokeWidth={1.5} fill="url(#binanceGrad)" dot={false} />
              <Area type="monotone" dataKey="BCV" stroke="var(--accent-blue)" strokeWidth={1.5} fill="url(#bcvGrad)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-56 flex items-center justify-center text-tertiary text-sm">
            Upload Historial_TCBinance.xlsx to see rate history
          </div>
        )}
      </Card>

      {/* Gap history */}
      {gapChartData.length > 0 && (
        <Card padding="md">
          <CardHeader>
            <CardTitle>Parallel Gap — Monthly (%)</CardTitle>
            <span className="text-xs text-tertiary">Binance premium over BCV</span>
          </CardHeader>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={gapChartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} interval={1} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} width={40} />
              <Tooltip
                formatter={(v: any) => [`${Number(v).toFixed(1)}%`, 'Gap']}
                contentStyle={{ background: 'var(--surface-elevated)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }}
              />
              <Bar dataKey="Gap %" fill="var(--accent-amber)" opacity={0.7} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          {gapData?.avg_gap_pct != null && (
            <SectionAnalysis
              text={`Average parallel gap over the period: ${gapData.avg_gap_pct.toFixed(1)}%. Current gap: ${gapData.current_gap_pct?.toFixed(1) ?? '—'}%.`}
              label="Gap Analysis"
              className="mt-4 pt-4 border-t border-[var(--border)]"
            />
          )}
        </Card>
      )}

      {/* Volatility detail */}
      {volatility && (
        <Card padding="md">
          <CardHeader>
            <CardTitle>Rate Volatility Metrics</CardTitle>
          </CardHeader>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Std Dev (daily)', value: volatility.std_dev_daily != null ? `${volatility.std_dev_daily.toFixed(2)}%` : '—' },
              { label: 'Std Dev (monthly)', value: volatility.std_dev_monthly != null ? `${volatility.std_dev_monthly.toFixed(2)}%` : '—' },
              { label: 'Annualized Vol', value: volatility.annualized_volatility_pct != null ? `${volatility.annualized_volatility_pct.toFixed(0)}%` : '—' },
              { label: 'Window', value: volatility.window_days != null ? `${volatility.window_days}d` : '—' },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="text-[10px] uppercase tracking-wider text-tertiary font-mono mb-1">{label}</p>
                <p className="mono text-lg font-semibold text-primary">{value}</p>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
