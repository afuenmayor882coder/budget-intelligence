import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, Clock, Zap, RefreshCw, Target } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { analysis, transactions, rates as ratesApi } from '@/lib/api'
import { formatUSD, formatPct, cn } from '@/lib/utils'
import { useAppStore } from '@/stores/appStore'
import { KpiCard } from '@/components/ui/KpiCard'
import { Card, CardHeader, CardTitle } from '@/components/ui/Card'
import { MonoValue } from '@/components/ui/MonoValue'
import { NumberCounter } from '@/components/ui/NumberCounter'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { ExecutiveSummary } from '@/components/ui/ExecutiveSummary'
import { AlertCard } from '@/components/ui/AlertCard'
import { SectionAnalysis } from '@/components/ui/SectionAnalysis'
import { MonthlyTrendChart } from '@/components/charts/MonthlyTrend'
import { SpendingByCategoryChart } from '@/components/charts/SpendingByCategory'
import { RunwayChart } from '@/components/charts/RunwayChart'
import { FxForecastStrip } from '@/components/ui/FxForecastStrip'
import { MacroChipStrip } from '@/components/ui/MacroChipStrip'
import { RecommendationsPreview } from '@/components/ui/RecommendationsPreview'

export function Dashboard() {
  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ['kpis'],
    queryFn: analysis.kpis,
    refetchInterval: 60_000,
  })

  const { data: runway, isLoading: runwayLoading } = useQuery({
    queryKey: ['runway'],
    queryFn: () => analysis.runway(),
  })

  const { data: monthlySeries, isLoading: seriesLoading } = useQuery({
    queryKey: ['monthly-series'],
    queryFn: transactions.monthlySeries,
  })

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['summary'],
    queryFn: () => transactions.summary(),
  })

  const { data: narrative, isLoading: narrativeLoading, refetch: refetchNarrative } = useQuery({
    queryKey: ['narrative'],
    queryFn: analysis.narrative,
    staleTime: 5 * 60_000,
  })

  const { data: latestRate } = useQuery({
    queryKey: ['rate-latest'],
    queryFn: ratesApi.latest,
    refetchInterval: 60 * 60_000,
  })

  const { data: purchasingPower } = useQuery({
    queryKey: ['purchasing-power'],
    queryFn: analysis.purchasingPower,
    staleTime: 10 * 60_000,
  })

  const hasData = kpis || monthlySeries?.length > 0

  if (!hasData && !kpisLoading) {
    return <EmptyState />
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      {/* Alert cards — critical/warning insights surface at the top */}
      <AnimatePresence>
        {narrative?.alerts?.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-2"
          >
            {narrative.alerts.slice(0, 3).map((alert: any) => (
              <AlertCard
                key={alert.insight_id}
                severity={alert.severity}
                subject={alert.subject}
                text={alert.text}
                insightId={alert.insight_id}
                onDismiss={(id) => analysis.dismissInsight(id)}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Hero row */}
      <div className="flex items-start justify-between gap-6">
        <div className="space-y-1">
          <p className="text-xs font-medium text-tertiary uppercase tracking-widest">Current Balance</p>
          {kpisLoading ? (
            <Skeleton className="h-14 w-56" />
          ) : (
            <div className="flex items-end gap-3">
              <NumberCounter
                value={kpis?.current_balance_usd ?? 0}
                duration={700}
                formatter={(v) => formatUSD(v)}
                className="text-5xl font-semibold tracking-tight text-primary"
              />
              {kpis?.balance_change_pct !== undefined && (
                <div className={cn(
                  'flex items-center gap-1 mb-2',
                  kpis.balance_change_pct >= 0 ? 'text-accent-green' : 'text-accent-red'
                )}>
                  {kpis.balance_change_pct >= 0
                    ? <TrendingUp className="w-4 h-4" />
                    : <TrendingDown className="w-4 h-4" />}
                  <span className="text-sm mono font-medium">
                    {formatPct(Math.abs(kpis.balance_change_pct), false)} vs last month
                  </span>
                </div>
              )}
            </div>
          )}
          <p className="text-xs text-tertiary">Combined across all accounts</p>
        </div>
        <div className="flex items-center gap-2">
          {latestRate?.is_stale ? (
            <Badge variant="amber" dot>STALE</Badge>
          ) : latestRate?.tasa_binance ? (
            <Badge variant="green" dot>LIVE</Badge>
          ) : null}
          {latestRate?.tasa_binance && (
            <span className="text-xs mono text-secondary">
              Bs {latestRate.tasa_binance.toFixed(0)}/USD
            </span>
          )}
        </div>
      </div>

      {/* FX Forecast Strip */}
      <FxForecastStrip />

      {/* Executive Summary — narrative hero */}
      {(narrativeLoading || narrative?.executive_summary) && (
        <Card padding="md">
          <ExecutiveSummary
            text={narrative?.executive_summary ?? ''}
            loading={narrativeLoading}
            onRefresh={() => refetchNarrative()}
          />
        </Card>
      )}

      {/* KPI grid */}
      <motion.div
        className="grid grid-cols-2 lg:grid-cols-4 gap-3"
        initial="hidden"
        animate="visible"
        variants={{ visible: { transition: { staggerChildren: 0.06 } } }}
      >
        {[
          { label: 'Runway', value: kpis ? `${kpis.runway_days ?? '—'} days` : '—', sublabel: 'Days to zero (no income)' },
          { label: 'Monthly Burn', value: kpis ? formatUSD(kpis.monthly_burn_usd ?? 0) : '—', delta: kpis?.burn_change_pct, deltaLabel: 'vs last month', invertDelta: true },
          { label: 'Savings Rate', value: kpis ? formatPct(kpis.savings_rate ?? 0) : '—', delta: kpis?.savings_rate_change, deltaLabel: 'vs last month' },
          { label: 'Real Income', value: kpis ? formatUSD(kpis.real_income_usd ?? 0) : '—', delta: kpis?.real_income_change_pct, deltaLabel: 'vs last month' },
        ].map((card) => (
          <motion.div
            key={card.label}
            variants={{ hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] } } }}
          >
            <KpiCard {...card} loading={kpisLoading} />
          </motion.div>
        ))}
      </motion.div>

      {/* Macro indicator strip */}
      <MacroChipStrip />

      {/* Primary chart + Category breakdown */}
      <div className="grid lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2" padding="md">
          <CardHeader>
            <CardTitle>Income vs Expenses</CardTitle>
            <div className="flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-[var(--accent-green)]" />
                <span className="text-secondary">Income</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-[var(--accent-red)]" />
                <span className="text-secondary">Expenses</span>
              </div>
            </div>
          </CardHeader>
          {seriesLoading ? (
            <Skeleton className="h-60 w-full" />
          ) : monthlySeries?.length > 0 ? (
            <MonthlyTrendChart data={monthlySeries} />
          ) : (
            <div className="h-60 flex items-center justify-center text-tertiary text-sm">
              No data yet — upload your CSV to get started
            </div>
          )}
          {narrative?.sections?.spending && (
            <SectionAnalysis
              text={narrative.sections.spending}
              className="mt-4 pt-4 border-t border-[var(--border)]"
            />
          )}
        </Card>

        <Card padding="md">
          <CardHeader>
            <CardTitle>Spending by Category</CardTitle>
            {summary && (
              <span className="text-xs mono text-secondary">{formatUSD(summary.total_expenses_usd ?? 0)}</span>
            )}
          </CardHeader>
          {summaryLoading ? (
            <Skeleton className="h-60 w-full" />
          ) : summary?.category_breakdown?.length > 0 ? (
            <SpendingByCategoryChart data={summary.category_breakdown} />
          ) : (
            <div className="h-60 flex items-center justify-center text-tertiary text-sm text-center px-4">
              No transactions yet
            </div>
          )}
        </Card>
      </div>

      {/* Cashflow Runway */}
      <Card padding="md">
        <CardHeader>
          <div>
            <CardTitle>Cashflow Runway</CardTitle>
            <p className="text-xs text-tertiary mt-0.5">Projected balance over time</p>
          </div>
          <div className="flex items-center gap-3">
            {runway && (
              <>
                <div className="text-right">
                  <p className="text-[10px] text-tertiary uppercase tracking-wider">No Income</p>
                  <p className="mono text-sm font-medium text-accent-amber">{runway.days_no_income} days</p>
                </div>
                <div className="w-px h-8 bg-[var(--border)]" />
                <div className="text-right">
                  <p className="text-[10px] text-tertiary uppercase tracking-wider">With Income</p>
                  <p className={cn('mono text-sm font-medium', runway.days_with_income < 0 ? 'text-accent-green' : 'text-accent-blue')}>
                    {runway.days_with_income < 0 ? 'Surplus' : `${runway.days_with_income} days`}
                  </p>
                </div>
              </>
            )}
          </div>
        </CardHeader>
        {runwayLoading ? (
          <Skeleton className="h-48 w-full" />
        ) : runway?.projection_no_income?.length > 0 ? (
          <RunwayChart
            noIncome={runway.projection_no_income}
            withIncome={runway.projection_with_income}
          />
        ) : (
          <div className="h-48 flex items-center justify-center text-tertiary text-sm">
            <div className="text-center">
              <Clock className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p>Add income sources and upload transactions to see runway</p>
            </div>
          </div>
        )}
      </Card>

      {/* Purchasing Power strip */}
      {purchasingPower && (
        <Card padding="md">
          <CardHeader>
            <div>
              <CardTitle>Purchasing Power</CardTitle>
              <p className="text-xs text-tertiary mt-0.5">Three depreciation lenses</p>
            </div>
          </CardHeader>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <PurchasingPowerLens
              label="Personal Inflation"
              value={purchasingPower.lens_spending?.total_depreciation_pct}
              description={purchasingPower.lens_spending?.description}
              suffix="%"
              invert
            />
            <PurchasingPowerLens
              label="Cesta Basica Coverage"
              value={purchasingPower.lens_cesta_basica?.baskets_covered}
              description="Income ÷ Cesta Basica basket"
              suffix="× baskets"
              good={v => v >= 2}
            />
            <PurchasingPowerLens
              label="FX Subscription Impact"
              value={purchasingPower.lens_subscriptions?.fx_depreciation_6m_pct}
              description="FX cost increase on USD subs (6m)"
              suffix="%"
              invert
            />
          </div>
          {narrative?.sections?.spending && (
            <SectionAnalysis
              text={`Real income projections: ${
                purchasingPower.projections?.avg_monthly_inflation_pct != null
                  ? `At ${purchasingPower.projections.avg_monthly_inflation_pct.toFixed(1)}% avg monthly inflation, your real income in 12 months would be ${purchasingPower.projections.real_income_12m_usd != null ? formatUSD(purchasingPower.projections.real_income_12m_usd) : 'N/A'}.`
                  : 'Upload IPC data to see projections.'
              }`}
              className="mt-4 pt-4 border-t border-[var(--border)]"
              label="Projection"
            />
          )}
        </Card>
      )}

      {/* Smart Recommendations */}
      <RecommendationsPreview />

      {/* This Month at a Glance + Top Categories */}
      {summary?.category_breakdown?.length > 0 && (
        <div className="grid lg:grid-cols-2 gap-4">
          <Card padding="md">
            <CardHeader>
              <CardTitle>This Month at a Glance</CardTitle>
            </CardHeader>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-secondary">Total Income</span>
                <MonoValue value={formatUSD(summary.total_income_usd ?? 0)} size="sm" color="green" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-secondary">Total Expenses</span>
                <MonoValue value={formatUSD(summary.total_expenses_usd ?? 0)} size="sm" color="red" />
              </div>
              <div className="h-px bg-[var(--border)]" />
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">Net</span>
                <MonoValue
                  value={formatUSD(summary.net_balance_usd ?? 0)}
                  size="sm"
                  color={(summary.net_balance_usd ?? 0) >= 0 ? 'green' : 'red'}
                />
              </div>
              {summary.savings_rate !== undefined && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-secondary">Savings Rate</span>
                  <MonoValue value={formatPct(summary.savings_rate)} size="sm" />
                </div>
              )}
            </div>
          </Card>

          <Card padding="md">
            <CardHeader>
              <CardTitle>Top Spending Categories</CardTitle>
            </CardHeader>
            <div className="space-y-2">
              {summary.category_breakdown?.slice(0, 5).map((cat: any, i: number) => (
                <div key={cat.categoria} className="flex items-center gap-3">
                  <span className="text-xs mono text-tertiary w-4">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-secondary truncate">{cat.categoria}</span>
                      <span className="text-xs mono text-primary ml-2">{formatUSD(cat.total_usd)}</span>
                    </div>
                    <div className="h-1 bg-[var(--surface-elevated)] rounded-full">
                      <div
                        className="h-full bg-[var(--accent-green)] rounded-full transition-all duration-500"
                        style={{ width: `${cat.pct_of_expenses}%`, opacity: 0.6 + (5 - i) * 0.08 }}
                      />
                    </div>
                  </div>
                  <span className="text-xs text-tertiary w-10 text-right mono">{formatPct(cat.pct_of_expenses)}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}

function PurchasingPowerLens({
  label,
  value,
  description,
  suffix,
  invert = false,
  good,
}: {
  label: string
  value: number | null | undefined
  description: string
  suffix: string
  invert?: boolean
  good?: (v: number) => boolean
}) {
  const hasValue = value != null

  const color = hasValue
    ? good
      ? good(value) ? 'text-accent-green' : 'text-accent-amber'
      : invert
        ? value > 20 ? 'text-accent-red' : value > 5 ? 'text-accent-amber' : 'text-accent-green'
        : 'text-text-primary'
    : 'text-text-tertiary'

  return (
    <div className="space-y-1">
      <p className="text-[10px] uppercase tracking-wider text-text-tertiary font-mono">{label}</p>
      <p className={cn('text-2xl font-semibold mono', color)}>
        {hasValue ? `${value.toFixed(1)}${suffix}` : '—'}
      </p>
      <p className="text-xs text-text-tertiary">{description}</p>
    </div>
  )
}

function EmptyState() {
  const { setActiveTab } = useAppStore()

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <div className="w-16 h-16 rounded-2xl bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center mb-6">
        <Zap className="w-8 h-8 text-[var(--accent-green)] opacity-80" />
      </div>
      <h2 className="text-xl font-semibold text-primary mb-2">Ready to analyze your finances</h2>
      <p className="text-sm text-secondary max-w-sm mb-6">
        Upload your Rial CSV export to get started. The dashboard will populate with your spending analysis, runway projections, purchasing power, and auto-generated financial narrative.
      </p>
      <button
        onClick={() => setActiveTab('upload')}
        className="flex items-center gap-2 h-9 px-4 bg-[var(--accent-green)] text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
      >
        Upload your first CSV
      </button>
    </div>
  )
}
