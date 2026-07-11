import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, DollarSign, TrendingDown, TrendingUp } from 'lucide-react'
import { income as incomeApi, analysis } from '@/lib/api'
import { formatUSD, formatVES, formatPct, cn } from '@/lib/utils'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { SectionAnalysis } from '@/components/ui/SectionAnalysis'
import type { IncomeSource } from '@/lib/types'
import { toast } from 'sonner'

const freqOptions = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'biweekly', label: 'Bi-weekly' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'annual', label: 'Annual' },
  { value: 'one-time', label: 'One-time' },
]

const currencyOptions = [
  { value: 'USD', label: 'USD' },
  { value: 'VES', label: 'VES (Bs)' },
]

interface IncomeFormData {
  name: string
  amount: string
  currency: string
  frequency: string
  start_date: string
  indexed_to_inflation: boolean
  active: boolean
}

const defaultForm: IncomeFormData = {
  name: '',
  amount: '',
  currency: 'USD',
  frequency: 'monthly',
  start_date: '',
  indexed_to_inflation: false,
  active: true,
}

export function IncomePage() {
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<IncomeFormData>(defaultForm)
  const queryClient = useQueryClient()

  const { data: sources = [], isLoading } = useQuery<IncomeSource[]>({
    queryKey: ['income'],
    queryFn: incomeApi.list,
  })

  const { data: purchasingPower, isLoading: ppLoading } = useQuery({
    queryKey: ['purchasing-power'],
    queryFn: analysis.purchasingPower,
    staleTime: 10 * 60_000,
    enabled: sources.length > 0,
  })

  const { data: narrative } = useQuery({
    queryKey: ['narrative'],
    queryFn: analysis.narrative,
    staleTime: 5 * 60_000,
  })

  const createMutation = useMutation({
    mutationFn: (data: object) => incomeApi.create(data),
    onSuccess: () => {
      toast.success('Income source added')
      queryClient.invalidateQueries({ queryKey: ['income'] })
      queryClient.invalidateQueries({ queryKey: ['kpis'] })
      queryClient.invalidateQueries({ queryKey: ['runway'] })
      queryClient.invalidateQueries({ queryKey: ['purchasing-power'] })
      setShowForm(false)
      setForm(defaultForm)
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: object }) => incomeApi.update(id, data),
    onSuccess: () => {
      toast.success('Income source updated')
      queryClient.invalidateQueries({ queryKey: ['income'] })
      queryClient.invalidateQueries({ queryKey: ['kpis'] })
      queryClient.invalidateQueries({ queryKey: ['runway'] })
      setEditingId(null)
      setShowForm(false)
      setForm(defaultForm)
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => incomeApi.delete(id),
    onSuccess: () => {
      toast.success('Income source deleted')
      queryClient.invalidateQueries({ queryKey: ['income'] })
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
      start_date: form.start_date || null,
    }
    if (editingId !== null) {
      updateMutation.mutate({ id: editingId, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const startEdit = (s: IncomeSource) => {
    setEditingId(s.id)
    setForm({
      name: s.name,
      amount: String(s.amount),
      currency: s.currency,
      frequency: s.frequency,
      start_date: s.start_date ?? '',
      indexed_to_inflation: s.indexed_to_inflation,
      active: s.active,
    })
    setShowForm(true)
  }

  const monthlyUSD = sources
    .filter((s) => s.active)
    .reduce((acc, s) => {
      let monthly = s.amount
      if (s.frequency === 'biweekly') monthly = s.amount * 2.17
      if (s.frequency === 'weekly') monthly = s.amount * 4.33
      if (s.frequency === 'annual') monthly = s.amount / 12
      if (s.currency === 'VES') monthly = monthly / 700
      return acc + monthly
    }, 0)

  const pp = purchasingPower

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-primary">Income & Salary</h1>
          <p className="text-sm text-secondary mt-1">Manage income sources and track real purchasing power</p>
        </div>
        <Button
          variant="primary"
          size="sm"
          icon={<Plus className="w-3.5 h-3.5" />}
          onClick={() => { setShowForm(true); setEditingId(null); setForm(defaultForm) }}
        >
          Add Source
        </Button>
      </div>

      {/* Summary */}
      {sources.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card padding="md">
            <p className="text-xs text-tertiary uppercase tracking-wider mb-2">Est. Monthly</p>
            <p className="mono text-2xl font-semibold text-primary">{formatUSD(monthlyUSD)}</p>
            <p className="text-xs text-tertiary mt-1">{sources.filter((s) => s.active).length} active sources</p>
          </Card>
          <Card padding="md">
            <p className="text-xs text-tertiary uppercase tracking-wider mb-2">Inflation Indexed</p>
            <p className="mono text-2xl font-semibold text-primary">
              {sources.filter((s) => s.indexed_to_inflation).length}
            </p>
            <p className="text-xs text-tertiary mt-1">of {sources.length} sources</p>
          </Card>
          {pp?.lens_cesta_basica?.baskets_covered != null && (
            <Card padding="md">
              <p className="text-xs text-tertiary uppercase tracking-wider mb-2">Cesta Coverage</p>
              <p className={cn(
                'mono text-2xl font-semibold',
                pp.lens_cesta_basica.baskets_covered >= 2 ? 'text-accent-green' : pp.lens_cesta_basica.baskets_covered >= 1 ? 'text-accent-amber' : 'text-accent-red'
              )}>
                {pp.lens_cesta_basica.baskets_covered.toFixed(1)}×
              </p>
              <p className="text-xs text-tertiary mt-1">Baskets per month</p>
            </Card>
          )}
          {pp?.lens_spending?.total_depreciation_pct != null && (
            <Card padding="md">
              <p className="text-xs text-tertiary uppercase tracking-wider mb-2">Real Depreciation</p>
              <p className={cn(
                'mono text-2xl font-semibold',
                pp.lens_spending.total_depreciation_pct > 20 ? 'text-accent-red' : pp.lens_spending.total_depreciation_pct > 5 ? 'text-accent-amber' : 'text-accent-green'
              )}>
                {pp.lens_spending.total_depreciation_pct.toFixed(1)}%
              </p>
              <p className="text-xs text-tertiary mt-1">Personal inflation</p>
            </Card>
          )}
        </div>
      )}

      {/* Purchasing power projections */}
      {sources.length > 0 && (
        <Card padding="md">
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown className="w-4 h-4 text-accent-amber" />
            <h3 className="text-sm font-medium text-primary">Real Income Projections</h3>
            {ppLoading && <span className="text-xs text-tertiary animate-pulse">calculating…</span>}
          </div>

          {pp ? (
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: '3-Month', value: pp.projections?.real_income_3m_usd },
                { label: '6-Month', value: pp.projections?.real_income_6m_usd },
                { label: '12-Month', value: pp.projections?.real_income_12m_usd },
              ].map(({ label, value }) => {
                const change = value != null && pp.monthly_income_usd > 0
                  ? ((value - pp.monthly_income_usd) / pp.monthly_income_usd) * 100
                  : null
                return (
                  <div key={label} className="space-y-1">
                    <p className="text-[10px] uppercase tracking-wider text-tertiary font-mono">{label}</p>
                    <p className={cn('mono text-xl font-semibold', change != null && change < -10 ? 'text-accent-red' : 'text-primary')}>
                      {value != null ? formatUSD(value) : '—'}
                    </p>
                    {change != null && (
                      <div className={cn('flex items-center gap-1', change >= 0 ? 'text-accent-green' : 'text-accent-red')}>
                        {change >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        <span className="text-xs mono">{formatPct(Math.abs(change))} vs now</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="py-4 text-center text-tertiary text-sm">
              {ppLoading
                ? 'Computing purchasing power…'
                : 'Upload IPC data for real income projections'}
            </div>
          )}

          {narrative?.sections?.income && (
            <SectionAnalysis
              text={narrative.sections.income}
              className="mt-4 pt-4 border-t border-[var(--border)]"
              label="Income Analysis"
            />
          )}
        </Card>
      )}

      {/* Form */}
      {showForm && (
        <Card padding="md">
          <h3 className="text-sm font-medium text-primary mb-4">
            {editingId !== null ? 'Edit Income Source' : 'New Income Source'}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Source name"
                placeholder="e.g. Salary, Freelance"
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
                label="Start date"
                type="date"
                value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              />
            </div>
            <div className="flex items-center gap-4 pt-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.indexed_to_inflation}
                  onChange={(e) => setForm({ ...form, indexed_to_inflation: e.target.checked })}
                  className="w-3.5 h-3.5 accent-[var(--accent-green)]"
                />
                <span className="text-xs text-secondary">Indexed to inflation</span>
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
                {editingId !== null ? 'Update' : 'Add Source'}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Sources list */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2].map((i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
        </div>
      ) : sources.length > 0 ? (
        <div className="space-y-2">
          {sources.map((s) => (
            <Card key={s.id} padding="md">
              <div className="flex items-center gap-4">
                <div className={cn(
                  'w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0',
                  s.active ? 'bg-accent-green-muted' : 'bg-surface-elevated'
                )}>
                  {s.active
                    ? <DollarSign className="w-4 h-4 text-accent-green" />
                    : <TrendingDown className="w-4 h-4 text-tertiary" />
                  }
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-primary">{s.name}</p>
                    {!s.active && <Badge variant="outline">Inactive</Badge>}
                    {s.indexed_to_inflation && <Badge variant="blue">Inflation-indexed</Badge>}
                  </div>
                  <p className="text-xs text-tertiary mt-0.5">
                    <span className="mono">{s.currency === 'USD' ? formatUSD(s.amount) : formatVES(s.amount)}</span>
                    {' · '}
                    {freqOptions.find((f) => f.value === s.frequency)?.label}
                    {s.start_date && ` · since ${s.start_date}`}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="sm" onClick={() => startEdit(s)} aria-label="Edit">
                    <Pencil className="w-3.5 h-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      if (confirm(`Delete "${s.name}"?`)) deleteMutation.mutate(s.id)
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
          <DollarSign className="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p>No income sources yet</p>
          <p className="text-xs mt-1">Add your salary and other income to enable runway projections and purchasing power analysis</p>
        </div>
      )}
    </div>
  )
}
