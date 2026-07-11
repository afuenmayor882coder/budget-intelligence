import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, ReferenceLine,
} from 'recharts'
import { Target, Zap, Activity, ChevronDown, ChevronUp } from 'lucide-react'
import { scenarios as scenariosApi, subscriptions as subsApi } from '@/lib/api'
import { formatUSD, formatPct, formatNumber, cn } from '@/lib/utils'
import { Card, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { SectionAnalysis } from '@/components/ui/SectionAnalysis'
import type { SavingPlan, MacroShockResult } from '@/lib/types'
import { toast } from 'sonner'

// ── Saving planner ──────────────────────────────────────────────

function SavingPlanner() {
  const [open, setOpen] = useState(true)
  const [targetUSD, setTargetUSD] = useState('')
  const [targetName, setTargetName] = useState('')
  const [targetMonths, setTargetMonths] = useState('')
  const [result, setResult] = useState<SavingPlan | null>(null)
  const [loading, setLoading] = useState(false)

  const { data: presets = [] } = useQuery({
    queryKey: ['scenario-presets'],
    queryFn: scenariosApi.presets,
  })

  const runPlan = async () => {
    if (!targetUSD) { toast.error('Enter a target amount'); return }
    setLoading(true)
    try {
      const res = await scenariosApi.savingGoal({
        target_usd: parseFloat(targetUSD),
        target_name: targetName || undefined,
        target_months: targetMonths ? parseInt(targetMonths) : undefined,
      })
      setResult(res)
    } catch (err: any) {
      toast.error(err.message ?? 'Calculation failed')
    } finally {
      setLoading(false)
    }
  }

  const timelineChartData = result?.timelines?.map((t) => ({
    name: `${t.months}mo`,
    'Required/mo': t.required_monthly_usd,
    feasible: t.feasible,
  })) ?? []

  return (
    <Card padding="md">
      <button className="w-full flex items-center justify-between" onClick={() => setOpen((v) => !v)}>
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-accent-green" />
          <span className="text-sm font-medium text-primary">Saving Goal Planner</span>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-tertiary" /> : <ChevronDown className="w-4 h-4 text-tertiary" />}
      </button>

      {open && (
        <div className="mt-4 space-y-4">
          {/* Presets */}
          {(presets as any[]).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {(presets as any[]).map((p: any) => (
                <button
                  key={p.name}
                  className="px-3 h-7 rounded-full border border-[var(--border)] text-xs text-secondary hover:border-[var(--accent-green)] hover:text-primary transition-colors"
                  onClick={() => { setTargetName(p.name); setTargetUSD(String(p.target_usd)) }}
                >
                  {p.name} · {formatUSD(p.target_usd)}
                </button>
              ))}
            </div>
          )}

          {/* Inputs */}
          <div className="grid grid-cols-3 gap-3">
            <Input
              label="Goal name"
              placeholder="e.g. Emergency fund"
              value={targetName}
              onChange={(e) => setTargetName(e.target.value)}
            />
            <Input
              label="Target (USD)"
              type="number"
              min="1"
              placeholder="5000"
              value={targetUSD}
              onChange={(e) => setTargetUSD(e.target.value)}
              required
            />
            <Input
              label="Deadline (months, optional)"
              type="number"
              min="1"
              placeholder="12"
              value={targetMonths}
              onChange={(e) => setTargetMonths(e.target.value)}
            />
          </div>

          <div className="flex justify-end">
            <Button variant="primary" size="sm" onClick={runPlan} loading={loading}>
              Calculate Plan
            </Button>
          </div>

          {/* Result */}
          {result && (
            <div className="space-y-4 pt-4 border-t border-[var(--border)]">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-tertiary font-mono mb-1">Target</p>
                  <p className="mono text-lg font-semibold text-primary">{formatUSD(result.target_usd)}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-tertiary font-mono mb-1">Monthly Surplus</p>
                  <p className={cn('mono text-lg font-semibold', result.monthly_surplus_usd >= 0 ? 'text-accent-green' : 'text-accent-red')}>
                    {formatUSD(result.monthly_surplus_usd)}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-tertiary font-mono mb-1">Months Needed</p>
                  <p className="mono text-lg font-semibold text-primary">
                    {result.months_needed != null ? `${result.months_needed}mo` : 'Not feasible'}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-tertiary font-mono mb-1">Feasibility</p>
                  <p className={cn(
                    'mono text-lg font-semibold',
                    result.feasibility_score >= 0.7 ? 'text-accent-green' : result.feasibility_score >= 0.4 ? 'text-accent-amber' : 'text-accent-red'
                  )}>
                    {(result.feasibility_score * 100).toFixed(0)}%
                  </p>
                </div>
              </div>

              {result.completion_date && (
                <p className="text-xs text-secondary">
                  Estimated completion: <span className="font-medium text-primary">{result.completion_date}</span>
                  {' · '}FX drift: <span className="mono">{formatPct(result.monthly_fx_drift_pct)}/mo</span>
                </p>
              )}

              {timelineChartData.length > 0 && (
                <div>
                  <p className="text-xs text-tertiary mb-2">Required monthly contribution by deadline</p>
                  <ResponsiveContainer width="100%" height={160}>
                    <BarChart data={timelineChartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} vertical={false} />
                      <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}`} width={45} />
                      <Tooltip
                        formatter={(v: any) => [formatUSD(Number(v)), 'Required/mo']}
                        contentStyle={{ background: 'var(--surface-elevated)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }}
                      />
                      <Bar
                        dataKey="Required/mo"
                        radius={[3, 3, 0, 0]}
                        fill="var(--accent-green)"
                        opacity={0.75}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {result.fx_adjusted_ves_needed != null && (
                <SectionAnalysis
                  text={`At current FX drift of ${formatPct(result.monthly_fx_drift_pct)}/mo, you'll need Bs ${formatNumber(result.fx_adjusted_ves_needed, 0)} by completion. Plan contributions in USD to hedge FX exposure.`}
                  label="FX Advisory"
                />
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

// ── What-If Simulator ────────────────────────────────────────────

function MacroShockSimulator() {
  const [open, setOpen] = useState(true)
  const [ipcPct, setIpcPct] = useState('5')
  const [fxPct, setFxPct] = useState('20')
  const [incomePct, setIncomePct] = useState('0')
  const [horizon, setHorizon] = useState('12')
  const [result, setResult] = useState<MacroShockResult | null>(null)
  const [loading, setLoading] = useState(false)

  const runShock = async () => {
    setLoading(true)
    try {
      const res = await scenariosApi.macroShock({
        ipc_monthly_change_pct: parseFloat(ipcPct),
        fx_devaluation_pct: parseFloat(fxPct),
        income_change_pct: parseFloat(incomePct),
        horizon_months: parseInt(horizon),
      })
      setResult(res)
    } catch (err: any) {
      toast.error(err.message ?? 'Simulation failed')
    } finally {
      setLoading(false)
    }
  }

  const monthlyChart = result?.monthly_simulation?.map((m) => ({
    name: `M${m.month}`,
    Income: m.income_usd,
    Expenses: m.expenses_usd,
    Net: m.net_usd,
    Balance: m.cumulative_balance_usd,
  })) ?? []

  const impact = result?.impact

  return (
    <Card padding="md">
      <button className="w-full flex items-center justify-between" onClick={() => setOpen((v) => !v)}>
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-accent-red" />
          <span className="text-sm font-medium text-primary">Macro Shock Simulator</span>
          <Badge variant="outline">What-If</Badge>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-tertiary" /> : <ChevronDown className="w-4 h-4 text-tertiary" />}
      </button>

      {open && (
        <div className="mt-4 space-y-4">
          <p className="text-xs text-secondary">Model an economic shock and see the impact on your finances over time.</p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Input
              label="IPC additional (%/mo)"
              type="number"
              step="0.5"
              placeholder="5"
              value={ipcPct}
              onChange={(e) => setIpcPct(e.target.value)}
            />
            <Input
              label="FX devaluation (%)"
              type="number"
              step="5"
              placeholder="20"
              value={fxPct}
              onChange={(e) => setFxPct(e.target.value)}
            />
            <Input
              label="Income change (%)"
              type="number"
              step="5"
              placeholder="0"
              value={incomePct}
              onChange={(e) => setIncomePct(e.target.value)}
            />
            <Input
              label="Horizon (months)"
              type="number"
              min="1"
              max="60"
              placeholder="12"
              value={horizon}
              onChange={(e) => setHorizon(e.target.value)}
            />
          </div>

          <div className="flex justify-end">
            <Button variant="primary" size="sm" onClick={runShock} loading={loading}>
              Run Simulation
            </Button>
          </div>

          {result && (
            <div className="space-y-4 pt-4 border-t border-[var(--border)]">
              {/* Impact summary */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  {
                    label: 'Annual Net Change',
                    value: impact?.annual_net_change_usd != null ? formatUSD(impact.annual_net_change_usd) : '—',
                    bad: (impact?.annual_net_change_usd ?? 0) < 0,
                  },
                  {
                    label: 'Change %',
                    value: impact?.annual_net_change_pct != null ? formatPct(impact.annual_net_change_pct) : '—',
                    bad: (impact?.annual_net_change_pct ?? 0) < 0,
                  },
                  {
                    label: 'Income Erosion',
                    value: impact?.income_erosion_usd_12m != null ? formatUSD(impact.income_erosion_usd_12m) : '—',
                    bad: true,
                  },
                  {
                    label: 'Expense Inflation',
                    value: impact?.expense_inflation_usd_12m != null ? formatUSD(impact.expense_inflation_usd_12m) : '—',
                    bad: true,
                  },
                ].map(({ label, value, bad }) => (
                  <div key={label}>
                    <p className="text-[10px] uppercase tracking-wider text-tertiary font-mono mb-1">{label}</p>
                    <p className={cn('mono text-lg font-semibold', bad ? 'text-accent-red' : 'text-accent-green')}>
                      {value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Shocked vs baseline */}
              {result.baseline && result.shocked && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-[var(--surface-elevated)] space-y-1.5">
                    <p className="text-xs font-medium text-secondary">Baseline</p>
                    <p className="text-xs text-tertiary">Income: <span className="mono text-primary">{formatUSD(result.baseline.monthly_income_usd)}/mo</span></p>
                    <p className="text-xs text-tertiary">Expenses: <span className="mono text-primary">{formatUSD(result.baseline.monthly_expenses_usd)}/mo</span></p>
                    <p className="text-xs text-tertiary">FX Rate: <span className="mono text-primary">{formatNumber(result.baseline.current_fx_rate, 0)} Bs</span></p>
                  </div>
                  <div className="p-3 rounded-lg bg-[var(--surface)] border border-[var(--accent-red)] border-opacity-30 space-y-1.5">
                    <p className="text-xs font-medium text-accent-red">After Shock</p>
                    <p className="text-xs text-tertiary">Income: <span className={cn('mono', result.shocked.monthly_income_usd < result.baseline.monthly_income_usd ? 'text-accent-red' : 'text-primary')}>{formatUSD(result.shocked.monthly_income_usd)}/mo</span></p>
                    <p className="text-xs text-tertiary">Inflation: <span className="mono text-accent-amber">{formatPct(result.shocked.total_monthly_inflation_pct)}/mo</span></p>
                    <p className="text-xs text-tertiary">FX Rate: <span className="mono text-accent-red">{formatNumber(result.shocked.shocked_fx_rate, 0)} Bs</span></p>
                  </div>
                </div>
              )}

              {/* Monthly simulation chart */}
              {monthlyChart.length > 0 && (
                <>
                  <p className="text-xs text-secondary font-medium">Projected monthly balance under shock</p>
                  <ResponsiveContainer width="100%" height={200}>
                    <AreaChart data={monthlyChart} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="balanceGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} vertical={false} />
                      <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}`} width={55} />
                      <ReferenceLine y={0} stroke="var(--accent-red)" strokeDasharray="4 2" strokeWidth={1} />
                      <Tooltip
                        formatter={(v: any, name: string) => [formatUSD(Number(v)), name]}
                        contentStyle={{ background: 'var(--surface-elevated)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }}
                      />
                      <Area type="monotone" dataKey="Balance" stroke="var(--accent-blue)" strokeWidth={1.5} fill="url(#balanceGrad)" dot={false} />
                      <Area type="monotone" dataKey="Net" stroke="var(--accent-green)" strokeWidth={1} fill="none" dot={false} strokeDasharray="3 3" />
                    </AreaChart>
                  </ResponsiveContainer>
                  <SectionAnalysis
                    text={`Under this shock scenario, annual net changes by ${formatUSD(impact?.annual_net_change_usd ?? 0)}. Income erosion from inflation totals ${formatUSD(impact?.income_erosion_usd_12m ?? 0)} over ${horizon} months.`}
                    label="Shock Analysis"
                  />
                </>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

// ── Sub Toggle Simulator ─────────────────────────────────────────

function SubToggleSimulator() {
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<number[]>([])
  const [result, setResult] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)

  const { data: subs = [] } = useQuery({
    queryKey: ['subscriptions'],
    queryFn: subsApi.list,
  })

  const runToggle = async () => {
    if (selected.length === 0) { toast.error('Select at least one subscription'); return }
    setLoading(true)
    try {
      const res = await scenariosApi.subToggle({ sub_ids: selected, toggle_state: false })
      setResult(res)
    } catch (err: any) {
      toast.error(err.message ?? 'Simulation failed')
    } finally {
      setLoading(false)
    }
  }

  const toggle = (id: number) =>
    setSelected((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id])

  return (
    <Card padding="md">
      <button className="w-full flex items-center justify-between" onClick={() => setOpen((v) => !v)}>
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-accent-amber" />
          <span className="text-sm font-medium text-primary">Subscription Cancel Impact</span>
          <Badge variant="outline">What-If</Badge>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-tertiary" /> : <ChevronDown className="w-4 h-4 text-tertiary" />}
      </button>

      {open && (
        <div className="mt-4 space-y-4">
          <p className="text-xs text-secondary">Select subscriptions to cancel and see the impact on your runway and savings.</p>

          {(subs as any[]).filter((s: any) => s.active).length === 0 ? (
            <p className="text-xs text-tertiary py-2">No active subscriptions to simulate</p>
          ) : (
            <div className="space-y-1.5">
              {(subs as any[]).filter((s: any) => s.active).map((s: any) => (
                <label key={s.id} className="flex items-center gap-3 p-2.5 rounded-lg border border-[var(--border)] cursor-pointer hover:border-[var(--text-tertiary)] transition-colors">
                  <input
                    type="checkbox"
                    checked={selected.includes(s.id)}
                    onChange={() => toggle(s.id)}
                    className="w-3.5 h-3.5 accent-[var(--accent-green)]"
                  />
                  <span className="text-sm text-primary flex-1">{s.name}</span>
                  <span className="text-xs mono text-tertiary">{s.currency} {s.amount}/{s.frequency}</span>
                  {!s.essential && <Badge variant="amber" className="text-[10px]">Non-essential</Badge>}
                </label>
              ))}
            </div>
          )}

          <div className="flex justify-end">
            <Button variant="primary" size="sm" onClick={runToggle} loading={loading} disabled={selected.length === 0}>
              Simulate Cancel
            </Button>
          </div>

          {result && (
            <div className="space-y-3 pt-4 border-t border-[var(--border)]">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-tertiary font-mono mb-1">Monthly Savings</p>
                  <p className="mono text-lg font-semibold text-accent-green">
                    {result.monthly_savings_usd != null ? formatUSD(result.monthly_savings_usd) : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-tertiary font-mono mb-1">Annual Savings</p>
                  <p className="mono text-lg font-semibold text-accent-green">
                    {result.annual_savings_usd != null ? formatUSD(result.annual_savings_usd) : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-tertiary font-mono mb-1">Runway Extension</p>
                  <p className="mono text-lg font-semibold text-primary">
                    {result.runway_extension_days != null ? `+${result.runway_extension_days} days` : '—'}
                  </p>
                </div>
              </div>
              {result.new_savings_rate_pct != null && (
                <p className="text-xs text-secondary">
                  New savings rate: <span className="mono font-medium text-accent-green">{formatPct(result.new_savings_rate_pct)}</span>
                  {result.old_savings_rate_pct != null && ` (was ${formatPct(result.old_savings_rate_pct)})`}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

// ── Page ─────────────────────────────────────────────────────────

export function ScenariosPage() {
  const { data: timeline, isLoading: tlLoading } = useQuery({
    queryKey: ['scenarios-timeline'],
    queryFn: () => scenariosApi.timeline(18),
    staleTime: 5 * 60_000,
  })

  const tlChart = (timeline?.months ?? []).map((m: any) => ({
    name: m.label ?? `M${m.month}`,
    Income: m.projected_income_usd,
    Expenses: m.projected_expenses_usd,
    Net: m.projected_net_usd,
  }))

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-primary">Scenarios & Planning</h1>
        <p className="text-sm text-secondary mt-1">Model saving goals and macro shocks on your financial future</p>
      </div>

      {/* Baseline timeline */}
      <Card padding="md">
        <CardHeader>
          <CardTitle>18-Month Baseline Projection</CardTitle>
          <span className="text-xs text-tertiary">Current trend</span>
        </CardHeader>
        {tlLoading ? (
          <Skeleton className="h-48 w-full" />
        ) : tlChart.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={tlChart} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="incomeGrad2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--accent-green)" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="var(--accent-green)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="expGrad2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--accent-red)" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="var(--accent-red)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} interval={2} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}`} width={50} />
              <ReferenceLine y={0} stroke="var(--border)" strokeWidth={1} />
              <Tooltip
                formatter={(v: any, name: string) => [formatUSD(Number(v)), name]}
                contentStyle={{ background: 'var(--surface-elevated)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }}
              />
              <Area type="monotone" dataKey="Income" stroke="var(--accent-green)" strokeWidth={1.5} fill="url(#incomeGrad2)" dot={false} />
              <Area type="monotone" dataKey="Expenses" stroke="var(--accent-red)" strokeWidth={1.5} fill="url(#expGrad2)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-48 flex items-center justify-center text-tertiary text-sm">
            Upload transactions and income to see baseline projection
          </div>
        )}
      </Card>

      {/* Saving planner */}
      <SavingPlanner />

      {/* Macro shock */}
      <MacroShockSimulator />

      {/* Sub toggle */}
      <SubToggleSimulator />
    </div>
  )
}
