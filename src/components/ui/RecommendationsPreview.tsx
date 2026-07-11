import { useQuery } from '@tanstack/react-query'
import { ArrowRight, TrendingDown, Target, Zap, AlertTriangle } from 'lucide-react'
import { subscriptions as subsApi, scenarios as scenariosApi } from '@/lib/api'
import { formatUSD, cn } from '@/lib/utils'
import { Card, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { useAppStore } from '@/stores/appStore'

interface Rec {
  id: string
  icon: React.ReactNode
  title: string
  detail: string
  impact?: string
  severity: 'info' | 'warn' | 'critical'
  tab: 'subscriptions' | 'scenarios' | 'income'
}

export function RecommendationsPreview() {
  const { setActiveTab } = useAppStore()

  const { data: optimizer } = useQuery({
    queryKey: ['sub-optimizer'],
    queryFn: subsApi.optimize,
    staleTime: 5 * 60_000,
    retry: 1,
  })

  const { data: goals } = useQuery({
    queryKey: ['scenario-goals'],
    queryFn: scenariosApi.goals,
    staleTime: 5 * 60_000,
    retry: 1,
  })

  const recs: Rec[] = []

  // Subscription recommendations
  const topSubRec = (optimizer as any)?.recommendations?.[0]
  if (topSubRec) {
    recs.push({
      id: 'sub-1',
      icon: <TrendingDown className="w-4 h-4" />,
      title: topSubRec.action === 'cancel'
        ? `Cancel ${topSubRec.name}`
        : `Downgrade ${topSubRec.name}`,
      detail: topSubRec.reason ?? 'Low value score',
      impact: topSubRec.savings_usd != null ? `Save ${formatUSD(topSubRec.savings_usd)}/mo` : undefined,
      severity: topSubRec.score < 0.3 ? 'critical' : topSubRec.score < 0.6 ? 'warn' : 'info',
      tab: 'subscriptions',
    })
  }

  // Second subscription recommendation
  const subRec2 = (optimizer as any)?.recommendations?.[1]
  if (subRec2) {
    recs.push({
      id: 'sub-2',
      icon: <TrendingDown className="w-4 h-4" />,
      title: subRec2.action === 'cancel' ? `Cancel ${subRec2.name}` : `Review ${subRec2.name}`,
      detail: subRec2.reason ?? 'Optimise cost',
      impact: subRec2.savings_usd != null ? `Save ${formatUSD(subRec2.savings_usd)}/mo` : undefined,
      severity: 'info',
      tab: 'subscriptions',
    })
  }

  // Saving goal recommendations
  const pendingGoals = (goals as any[])?.filter((g: any) => !g.completed) ?? []
  if (pendingGoals.length > 0) {
    const g = pendingGoals[0]
    recs.push({
      id: `goal-${g.id}`,
      icon: <Target className="w-4 h-4" />,
      title: `Save for: ${g.name ?? 'Goal'}`,
      detail: `Target ${formatUSD(g.target_usd ?? 0)}`,
      impact: g.months_needed != null ? `~${g.months_needed} months` : undefined,
      severity: 'info',
      tab: 'scenarios',
    })
  }

  // Subscription overspend summary
  const totalPotential = (optimizer as any)?.total_potential_savings_usd
  if (totalPotential != null && totalPotential > 0 && recs.length < 3) {
    recs.push({
      id: 'sub-total',
      icon: <Zap className="w-4 h-4" />,
      title: 'Subscription optimisation',
      detail: `${(optimizer as any)?.recommendations?.length ?? 0} subscriptions to review`,
      impact: `Up to ${formatUSD(totalPotential)}/mo savings`,
      severity: totalPotential > 50 ? 'warn' : 'info',
      tab: 'subscriptions',
    })
  }

  if (recs.length === 0) {
    return (
      <Card padding="md">
        <CardHeader>
          <CardTitle>Smart Recommendations</CardTitle>
        </CardHeader>
        <p className="text-sm text-tertiary text-center py-4">
          Upload transactions and add subscriptions to generate personalised recommendations.
        </p>
      </Card>
    )
  }

  const severityBadge: Record<string, 'red' | 'amber' | 'default'> = {
    critical: 'red',
    warn: 'amber',
    info: 'default',
  }

  return (
    <Card padding="md">
      <CardHeader>
        <CardTitle>Smart Recommendations</CardTitle>
        <span className="text-xs text-tertiary">{recs.length} action{recs.length !== 1 ? 's' : ''}</span>
      </CardHeader>

      <div className="space-y-2 mt-2">
        {recs.slice(0, 3).map((rec) => (
          <button
            key={rec.id}
            className={cn(
              'w-full flex items-center gap-3 p-3 rounded-lg border transition-all duration-150 text-left',
              'border-[var(--border)] hover:border-[var(--text-tertiary)] hover:bg-[var(--surface-elevated)] group'
            )}
            onClick={() => setActiveTab(rec.tab)}
          >
            <div className={cn(
              'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
              rec.severity === 'critical' ? 'bg-[var(--accent-red)]/10 text-accent-red'
              : rec.severity === 'warn' ? 'bg-[var(--accent-amber)]/10 text-accent-amber'
              : 'bg-[var(--surface-elevated)] text-secondary'
            )}>
              {rec.icon}
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-primary truncate">{rec.title}</p>
              <p className="text-xs text-tertiary truncate">{rec.detail}</p>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              {rec.impact && (
                <Badge variant={severityBadge[rec.severity] ?? 'default'}>
                  {rec.impact}
                </Badge>
              )}
              <ArrowRight className="w-3.5 h-3.5 text-tertiary group-hover:text-secondary transition-colors" />
            </div>
          </button>
        ))}
      </div>
    </Card>
  )
}
