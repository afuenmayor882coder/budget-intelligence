import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, CreditCard, AlertCircle, Zap, TrendingDown, ChevronDown, ChevronUp } from 'lucide-react'
import { subscriptions as subsApi } from '@/lib/api'
import { formatUSD, formatVES, cn } from '@/lib/utils'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { SectionAnalysis } from '@/components/ui/SectionAnalysis'
import type { Subscription, SubOptimizationResult, RankedSub } from '@/lib/types'
import { toast } from 'sonner'

const freqOptions = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'annual', label: 'Annual' },
  { value: 'quarterly', label: 'Quarterly' },
]

const currencyOptions = [
  { value: 'USD', label: 'USD' },
  { value: 'VES', label: 'VES (Bs)' },
]

interface SubForm {
  name: string
  amount: string
  currency: string
  frequency: string
  category: string
  account: string
  next_payment_date: string
  essential: boolean
  active: boolean
  notes: string
}

const defaultForm: SubForm = {
  name: '',
  amount: '',
  currency: 'USD',
  frequency: 'monthly',
  category: '',
  account: '',
  next_payment_date: '',
  essential: false,
  active: true,
  notes: '',
}

const actionColor = (action: RankedSub['action']) => {
  if (action === 'review') return 'text-accent-red'
  if (action === 'monitor') return 'text-accent-amber'
  return 'text-accent-green'
}

const actionBadge = (action: RankedSub['action']) => {
  if (action === 'review') return <Badge variant="red">Review</Badge>
  if (action === 'monitor') return <Badge variant="amber">Monitor</Badge>
  return <Badge variant="green">Keep</Badge>
}

export function SubscriptionsPage() {
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<SubForm>(defaultForm)
  const [showOptimizer, setShowOptimizer] = useState(true)
  const queryClient = useQueryClient()

  const { data: subs = [], isLoading } = useQuery<Subscription[]>({
    queryKey: ['subscriptions'],
    queryFn: subsApi.list,
  })

  const { data: optimization, isLoading: optLoading } = useQuery<SubOptimizationResult>({
    queryKey: ['subscriptions-optimize'],
    queryFn: subsApi.optimize,
    staleTime: 5 * 60_000,
    enabled: subs.length > 0,
  })

  const createMutation = useMutation({
    mutationFn: (data: object) => subsApi.create(data),
    onSuccess: () => {
      toast.success('Subscription added')
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] })
      queryClient.invalidateQueries({ queryKey: ['subscriptions-optimize'] })
      queryClient.invalidateQueries({ queryKey: ['kpis'] })
      queryClient.invalidateQueries({ queryKey: ['runway'] })
      setShowForm(false)
      setForm(defaultForm)
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: object }) => subsApi.update(id, data),
    onSuccess: () => {
      toast.success('Subscription updated')
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] })
      queryClient.invalidateQueries({ queryKey: ['subscriptions-optimize'] })
      queryClient.invalidateQueries({ queryKey: ['kpis'] })
      queryClient.invalidateQueries({ queryKey: ['runway'] })
      setEditingId(null)
      setShowForm(false)
      setForm(defaultForm)
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => subsApi.delete(id),
    onSuccess: () => {
      toast.success('Subscription removed')
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] })
      queryClient.invalidateQueries({ queryKey: ['subscriptions-optimize'] })
      queryClient.invalidateQueries({ queryKey: ['kpis'] })
      queryClient.invalidateQueries({ queryKey: ['runway'] })
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data = {
      ...form,
      amount: parseFloat(form.amount),
      category: form.category || null,
      account: form.account || null,
      next_payment_date: form.next_payment_date || null,
      notes: form.notes || null,
    }
    if (editingId !== null) {
      updateMutation.mutate({ id: editingId, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const startEdit = (s: Subscription) => {
    setEditingId(s.id)
    setForm({
      name: s.name,
      amount: String(s.amount),
      currency: s.currency,
      frequency: s.frequency,
      category: s.category ?? '',
      account: s.account ?? '',
      next_payment_date: s.next_payment_date ?? '',
      essential: s.essential,
      active: s.active,
      notes: s.notes ?? '',
    })
    setShowForm(true)
  }

  const toMonthly = (s: Subscription) => {
    let m = s.amount
    if (s.frequency === 'annual') m = s.amount / 12
    if (s.frequency === 'quarterly') m = s.amount / 3
    return s.currency === 'USD' ? m : m / 700
  }

  const totalMonthlyUSD = subs.filter((s) => s.active).reduce((acc, s) => acc + toMonthly(s), 0)
  const usdSubs = subs.filter((s) => s.active && s.currency === 'USD')

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-primary">Subscriptions</h1>
          <p className="text-sm text-secondary mt-1">Track recurring payments and their FX impact</p>
        </div>
        <Button
          variant="primary"
          size="sm"
          icon={<Plus className="w-3.5 h-3.5" />}
          onClick={() => { setShowForm(true); setEditingId(null); setForm(defaultForm) }}
        >
          Add
        </Button>
      </div>

      {/* Summary */}
      {subs.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <Card padding="md">
            <p className="text-xs text-tertiary uppercase tracking-wider mb-2">Monthly Total</p>
            <p className="mono text-2xl font-semibold text-primary">{formatUSD(optimization?.total_monthly_usd ?? totalMonthlyUSD)}</p>
            <p className="text-xs text-tertiary mt-1">{subs.filter((s) => s.active).length} active</p>
          </Card>
          <Card padding="md">
            <p className="text-xs text-tertiary uppercase tracking-wider mb-2">USD-exposed</p>
            <p className="mono text-2xl font-semibold text-primary">{optimization?.usd_subs_count ?? usdSubs.length}</p>
            <p className="text-xs text-tertiary mt-1">FX-denominated</p>
          </Card>
          <Card padding="md">
            <p className="text-xs text-tertiary uppercase tracking-wider mb-2">Potential Savings</p>
            <p className={cn('mono text-2xl font-semibold', (optimization?.potential_monthly_savings_usd ?? 0) > 0 ? 'text-accent-green' : 'text-primary')}>
              {optimization ? formatUSD(optimization.potential_monthly_savings_usd) : '—'}
            </p>
            <p className="text-xs text-tertiary mt-1">if review items cancelled</p>
          </Card>
        </div>
      )}

      {/* Optimizer panel */}
      {subs.length > 0 && (
        <Card padding="md">
          <button
            className="w-full flex items-center justify-between"
            onClick={() => setShowOptimizer((v) => !v)}
          >
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-accent-amber" />
              <span className="text-sm font-medium text-primary">Subscription Optimizer</span>
              {optimization?.cancel_candidates?.length > 0 && (
                <Badge variant="red">{optimization.cancel_candidates.length} to review</Badge>
              )}
            </div>
            {showOptimizer
              ? <ChevronUp className="w-4 h-4 text-tertiary" />
              : <ChevronDown className="w-4 h-4 text-tertiary" />
            }
          </button>

          {showOptimizer && (
            <div className="mt-4 space-y-3">
              {optLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
                </div>
              ) : optimization?.ranked_subscriptions?.length > 0 ? (
                <>
                  {optimization.income_pct_of_subs != null && (
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--surface-elevated)]">
                      <div className="text-xs text-secondary">
                        Subscriptions consume{' '}
                        <span className={cn(
                          'font-semibold mono',
                          optimization.income_pct_of_subs > 20 ? 'text-accent-red' : optimization.income_pct_of_subs > 10 ? 'text-accent-amber' : 'text-accent-green'
                        )}>
                          {optimization.income_pct_of_subs.toFixed(1)}%
                        </span>
                        {' '}of income ·{' '}
                        <span className="text-primary font-medium">{formatUSD(optimization.potential_annual_savings_usd)}/yr</span>
                        {' '}potential savings
                      </div>
                    </div>
                  )}
                  <div className="space-y-2">
                    {optimization.ranked_subscriptions.map((sub) => (
                      <div
                        key={sub.id}
                        className="flex items-center gap-3 p-3 rounded-lg border border-[var(--border)] hover:border-[var(--text-tertiary)] transition-colors"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-primary truncate">{sub.name}</span>
                            {actionBadge(sub.action)}
                            {sub.essential && <Badge variant="green">Essential</Badge>}
                          </div>
                          <p className="text-xs text-tertiary mt-0.5 truncate">{sub.reason}</p>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <p className="mono text-sm font-medium text-primary">{formatUSD(sub.monthly_usd)}/mo</p>
                          {sub.income_pct > 0 && (
                            <p className="text-xs text-tertiary mono">{sub.income_pct.toFixed(1)}% income</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  {optimization.cancel_candidates?.length > 0 && (
                    <SectionAnalysis
                      text={`Cancel candidates: ${optimization.cancel_candidates.map(c => c.name).join(', ')}. Cancelling these would save ${formatUSD(optimization.potential_annual_savings_usd)} per year.`}
                      label="Optimizer Insight"
                      className="mt-2"
                    />
                  )}
                </>
              ) : (
                <div className="text-center py-4 text-tertiary text-sm">
                  <TrendingDown className="w-6 h-6 mx-auto mb-1 opacity-30" />
                  <p>No optimization data yet</p>
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {/* FX warning */}
      {usdSubs.length > 0 && (
        <div className="bg-[var(--surface)] border border-[var(--accent-amber)] border-opacity-30 rounded-xl p-3 flex items-center gap-3">
          <AlertCircle className="w-4 h-4 text-accent-amber flex-shrink-0" />
          <p className="text-xs text-secondary">
            <span className="font-medium text-primary">{usdSubs.length} USD subscriptions</span> are exposed to Binance/BCV rate changes. Cost in VES rises automatically with exchange rate.
            {optimization?.fx_change_6m_pct != null && (
              <span className="ml-1 text-accent-amber font-medium">
                FX +{optimization.fx_change_6m_pct.toFixed(1)}% last 6mo.
              </span>
            )}
          </p>
        </div>
      )}

      {/* Form */}
      {showForm && (
        <Card padding="md">
          <h3 className="text-sm font-medium text-primary mb-4">
            {editingId !== null ? 'Edit Subscription' : 'New Subscription'}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Name"
                placeholder="e.g. Cursor AI, Netflix"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
              <Input
                label="Amount"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                required
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <Select
                label="Currency"
                options={currencyOptions}
                value={form.currency}
                onChange={(e) => setForm({ ...form, currency: e.target.value })}
              />
              <Select
                label="Frequency"
                options={freqOptions}
                value={form.frequency}
                onChange={(e) => setForm({ ...form, frequency: e.target.value })}
              />
              <Input
                label="Next payment"
                type="date"
                value={form.next_payment_date}
                onChange={(e) => setForm({ ...form, next_payment_date: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Category (optional)"
                placeholder="e.g. Productivity, Entertainment"
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              />
              <Input
                label="Account (optional)"
                placeholder="e.g. Binance, Wells Fargo"
                value={form.account}
                onChange={(e) => setForm({ ...form, account: e.target.value })}
              />
            </div>
            <div className="flex items-center gap-4 pt-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.essential}
                  onChange={(e) => setForm({ ...form, essential: e.target.checked })}
                  className="w-3.5 h-3.5 accent-[var(--accent-green)]"
                />
                <span className="text-xs text-secondary">Essential</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.active}
                  onChange={(e) => setForm({ ...form, active: e.target.checked })}
                  className="w-3.5 h-3.5 accent-[var(--accent-green)]"
                />
                <span className="text-xs text-secondary">Active</span>
              </label>
            </div>
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
              <Button variant="ghost" size="sm" type="button" onClick={() => { setShowForm(false); setEditingId(null); setForm(defaultForm) }}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                type="submit"
                loading={createMutation.isPending || updateMutation.isPending}
              >
                {editingId !== null ? 'Update' : 'Add'}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Subscriptions list */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
        </div>
      ) : subs.length > 0 ? (
        <div className="space-y-2">
          {subs.map((s) => (
            <Card key={s.id} padding="md">
              <div className="flex items-center gap-4">
                <div className={cn(
                  'w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0',
                  s.active ? 'bg-surface-elevated' : 'bg-surface-elevated opacity-50'
                )}>
                  <CreditCard className="w-4 h-4 text-secondary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className={cn('text-sm font-medium', s.active ? 'text-primary' : 'text-secondary line-through')}>
                      {s.name}
                    </p>
                    {!s.active && <Badge variant="outline">Inactive</Badge>}
                    {s.essential && <Badge variant="green">Essential</Badge>}
                    <Badge variant={s.currency === 'USD' ? 'amber' : 'default'}>{s.currency}</Badge>
                  </div>
                  <p className="text-xs text-tertiary mt-0.5">
                    <span className="mono">
                      {s.currency === 'USD' ? formatUSD(s.amount) : formatVES(s.amount)}
                    </span>
                    {' / '}
                    {freqOptions.find((f) => f.value === s.frequency)?.label.toLowerCase()}
                    {s.account && ` · ${s.account}`}
                    {s.next_payment_date && ` · next: ${s.next_payment_date}`}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  <span className="mono text-sm font-medium text-primary mr-2">
                    {formatUSD(toMonthly(s))}/mo
                  </span>
                  <Button variant="ghost" size="sm" onClick={() => startEdit(s)} aria-label="Edit">
                    <Pencil className="w-3.5 h-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      if (confirm(`Remove "${s.name}"?`)) deleteMutation.mutate(s.id)
                    }}
                    aria-label="Delete"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-accent-red" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-tertiary text-sm">
          <CreditCard className="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p>No subscriptions yet</p>
          <p className="text-xs mt-1">Add your recurring payments to track FX impact and optimize spending</p>
        </div>
      )}
    </div>
  )
}
