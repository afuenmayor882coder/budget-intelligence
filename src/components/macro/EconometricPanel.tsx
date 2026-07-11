import { useQuery, useMutation } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { RefreshCw, Download, TrendingUp } from 'lucide-react'
import { forecasts, reports } from '@/lib/api'
import type { VerdictExplanation } from '@/components/ui/VerdictCard'
import { Card, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { Badge } from '@/components/ui/Badge'
import { VerdictCard } from '@/components/ui/VerdictCard'
import { MetricTooltip } from '@/components/ui/MetricTooltip'
import { formatNumber, cn } from '@/lib/utils'
import { toast } from 'sonner'

interface ForecastPanelProps {
  horizon?: number
}

export function EconometricPanel({ horizon = 7 }: ForecastPanelProps) {
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['fx-forecasts', horizon],
    queryFn: () => forecasts.fx(horizon),
    staleTime: 30 * 60_000,
    retry: 1,
  })

  const { data: macroImpact } = useQuery({
    queryKey: ['macro-impact'],
    queryFn: forecasts.macroImpact,
    staleTime: 15 * 60_000,
  })

  const exportMd = useMutation({
    mutationFn: reports.exportMarkdown,
    onSuccess: (res) => toast.success(`Report saved: ${res.filename}`),
    onError: (err: Error) => toast.error(err.message),
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (data?.error) {
    return (
      <Card padding="md">
        <p className="text-sm text-secondary">{data.error}</p>
        <p className="text-xs text-tertiary mt-2">Upload exchange rate history via Upload tab or sync from cloud.</p>
      </Card>
    )
  }

  const pipeline = data?.pipeline || {}
  const explanations = (data?.explanations || {}) as Record<string, VerdictExplanation | VerdictExplanation[]>

  const chartData: { day: number; binance?: number; bcv?: number; binanceEns?: number; bcvEns?: number }[] = []
  const binanceEns = pipeline.binance_ensemble?.forecast as number[] | undefined
  const bcvEns = pipeline.bcv_ensemble?.forecast as number[] | undefined
  const maxLen = Math.max(binanceEns?.length || 0, bcvEns?.length || 0)

  for (let i = 0; i < maxLen; i++) {
    chartData.push({
      day: i + 1,
      binanceEns: binanceEns?.[i],
      bcvEns: bcvEns?.[i],
    })
  }

  const binanceBacktest = pipeline.binance_backtest
  const bcvBacktest = pipeline.bcv_backtest
  const bestBinance = binanceBacktest?.best_model
  const bestBcv = bcvBacktest?.best_model

  const verdictItems: { key: string; exp: VerdictExplanation; title: string }[] = []
  for (const [key, val] of Object.entries(explanations)) {
    if (Array.isArray(val)) continue
    if (val && typeof val === 'object' && 'verdict' in val) {
      verdictItems.push({
        key,
        exp: val as VerdictExplanation,
        title: key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-secondary" />
          <h2 className="text-lg font-semibold text-primary">Econometric Analysis</h2>
          <Badge variant="green">Phase 3</Badge>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            icon={<Download className="w-3.5 h-3.5" />}
            loading={exportMd.isPending}
            onClick={() => exportMd.mutate()}
          >
            Export Report
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon={<RefreshCw className={cn('w-3.5 h-3.5', isFetching && 'animate-spin')} />}
            onClick={() => refetch()}
          >
            Re-run Models
          </Button>
        </div>
      </div>

      {/* Model comparison KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {bestBinance && (
          <Card padding="md">
            <p className="text-xs text-tertiary uppercase tracking-wider mb-1">Best Binance Model</p>
            <MetricTooltip explanation={explanations.binance_metrics as VerdictExplanation || `${bestBinance} selected by lowest MAE`}>
              <p className="mono text-lg font-semibold text-primary uppercase">{bestBinance}</p>
            </MetricTooltip>
            <p className="text-xs text-tertiary mt-1">
              MAE: {formatNumber(binanceBacktest?.best_mae, 1)} VES
            </p>
          </Card>
        )}
        {bestBcv && (
          <Card padding="md">
            <p className="text-xs text-tertiary uppercase tracking-wider mb-1">Best BCV Model</p>
            <MetricTooltip explanation={explanations.bcv_metrics as VerdictExplanation || `${bestBcv} selected by lowest MAE`}>
              <p className="mono text-lg font-semibold text-primary uppercase">{bestBcv}</p>
            </MetricTooltip>
            <p className="text-xs text-tertiary mt-1">
              MAE: {formatNumber(bcvBacktest?.best_mae, 1)} VES
            </p>
          </Card>
        )}
        {pipeline.cointegration && !pipeline.cointegration.error && (
          <Card padding="md">
            <p className="text-xs text-tertiary uppercase tracking-wider mb-1">Cointegration</p>
            <p className="mono text-lg font-semibold text-primary">
              Rank {pipeline.cointegration.cointegrating_rank_95 ?? 0}
            </p>
            <p className="text-xs text-tertiary mt-1">Johansen trace test</p>
          </Card>
        )}
        {macroImpact?.risk_score != null && (
          <Card padding="md">
            <p className="text-xs text-tertiary uppercase tracking-wider mb-1">Macro Risk</p>
            <p className={cn(
              'mono text-lg font-semibold',
              macroImpact.risk_level === 'critical' || macroImpact.risk_level === 'high'
                ? 'text-accent-red'
                : macroImpact.risk_level === 'moderate'
                  ? 'text-accent-amber'
                  : 'text-accent-green',
            )}>
              {macroImpact.risk_score}%
            </p>
            <p className="text-xs text-tertiary mt-1 capitalize">{macroImpact.risk_level} exposure</p>
          </Card>
        )}
      </div>

      {/* Ensemble forecast chart */}
      {chartData.length > 0 && (
        <Card padding="md">
          <CardHeader>
            <CardTitle>{horizon}-Day Ensemble Forecast</CardTitle>
            <span className="text-xs text-tertiary">Inverse-MAE weighted</span>
          </CardHeader>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} />
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} label={{ value: 'Days ahead', position: 'insideBottom', offset: -2, fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} tickFormatter={(v) => formatNumber(v, 0)} width={55} />
              <Tooltip formatter={(v) => [formatNumber(Number(v), 2) + ' VES', '']} contentStyle={{ background: 'var(--surface-elevated)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }} />
              <Legend wrapperStyle={{ fontSize: '11px' }} />
              {binanceEns && <Line type="monotone" dataKey="binanceEns" name="Binance" stroke="var(--accent-green)" strokeWidth={1.5} dot={false} />}
              {bcvEns && <Line type="monotone" dataKey="bcvEns" name="BCV" stroke="var(--accent-blue)" strokeWidth={1.5} dot={false} />}
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* IRF chart if available */}
      {pipeline.irf?.responses && (
        <Card padding="md">
          <CardHeader>
            <CardTitle>Impulse Response — Binance Shock</CardTitle>
          </CardHeader>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart
              data={(pipeline.irf.responses.tasa_bcv || []).map((v: number, i: number) => ({ period: i, response: v }))}
              margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} />
              <XAxis dataKey="period" tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={{ background: 'var(--surface-elevated)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }} />
              <Line type="monotone" dataKey="response" name="BCV response" stroke="var(--accent-amber)" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Verdict cards */}
      {verdictItems.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-secondary">Plain-Language Analysis</h3>
          {verdictItems.slice(0, 6).map(({ key, exp, title }) => (
            <VerdictCard key={key} explanation={exp} title={title} />
          ))}
        </div>
      )}

      {/* Macro-personal elasticities */}
      {macroImpact?.elasticities && macroImpact.elasticities.length > 0 && (
        <Card padding="md">
          <CardHeader>
            <CardTitle>Category-Macro Elasticities</CardTitle>
          </CardHeader>
          <div className="space-y-2">
            {macroImpact.elasticities.map((e: { category: string; ipc_elasticity: number; interpretation: string }) => (
              <div key={e.category} className="flex items-start justify-between gap-4 py-2 border-b border-[var(--border)] last:border-0">
                <span className="text-sm text-primary">{e.category}</span>
                <MetricTooltip explanation={e.interpretation}>
                  <span className="mono text-sm text-secondary">{e.ipc_elasticity.toFixed(2)}</span>
                </MetricTooltip>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Granger causality table */}
      {pipeline.granger && pipeline.granger.length > 0 && (
        <Card padding="md">
          <CardHeader>
            <CardTitle>Granger Causality</CardTitle>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-tertiary text-xs uppercase tracking-wider">
                  <th className="pb-2 pr-4">Direction</th>
                  <th className="pb-2 pr-4">Best Lag</th>
                  <th className="pb-2 pr-4">p-value</th>
                  <th className="pb-2">Significant</th>
                </tr>
              </thead>
              <tbody>
                {pipeline.granger.slice(0, 4).map((g: { direction: string; best_lag: number; best_p_value: number; causes: boolean }, i: number) => (
                  <tr key={i} className="border-t border-[var(--border)]">
                    <td className="py-2 pr-4 text-primary">{g.direction}</td>
                    <td className="py-2 pr-4 mono text-secondary">{g.best_lag}</td>
                    <td className="py-2 pr-4 mono text-secondary">{g.best_p_value?.toFixed(3)}</td>
                    <td className="py-2">
                      <Badge variant={g.causes ? 'green' : 'default'}>{g.causes ? 'Yes' : 'No'}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
