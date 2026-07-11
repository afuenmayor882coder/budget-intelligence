import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react'
import { macro } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/stores/appStore'

interface ChipProps {
  label: string
  value: string | null
  sub?: string
  severity?: 'ok' | 'warn' | 'danger' | 'neutral'
  onClick?: () => void
}

function MacroChip({ label, value, sub, severity = 'neutral', onClick }: ChipProps) {
  const valueColor = {
    ok: 'text-accent-green',
    warn: 'text-accent-amber',
    danger: 'text-accent-red',
    neutral: 'text-primary',
  }[severity]

  return (
    <button
      className={cn(
        'flex flex-col items-start px-3 py-2 rounded-lg border bg-[var(--surface)] transition-all duration-150 min-w-[110px]',
        onClick
          ? 'border-[var(--border)] hover:border-[var(--text-tertiary)] cursor-pointer'
          : 'border-[var(--border)] cursor-default'
      )}
      onClick={onClick}
    >
      <span className="text-[9px] font-mono uppercase tracking-wider text-tertiary mb-0.5 whitespace-nowrap">
        {label}
      </span>
      {value != null ? (
        <span className={cn('mono text-sm font-semibold', valueColor)}>{value}</span>
      ) : (
        <span className="mono text-sm text-tertiary">—</span>
      )}
      {sub && <span className="text-[10px] text-tertiary mt-0.5 whitespace-nowrap">{sub}</span>}
    </button>
  )
}

export function MacroChipStrip() {
  const { setActiveTab } = useAppStore()

  const { data: macroSummary } = useQuery({
    queryKey: ['macro-summary'],
    queryFn: macro.summary,
    staleTime: 5 * 60_000,
    retry: 1,
  })

  const { data: ipcLatest } = useQuery({
    queryKey: ['macro-ipc-latest'],
    queryFn: macro.ipcLatest,
    staleTime: 5 * 60_000,
    retry: 1,
  })

  if (!macroSummary && !ipcLatest) return null

  const ipcPct = ipcLatest?.var_pct ?? macroSummary?.ipc_var_pct
  const m2Val = macroSummary?.m2_growth_pct
  const cestaUsd = macroSummary?.cesta_usd
  const oilRevenue = macroSummary?.oil_revenue_latest_bn

  const ipcSeverity =
    ipcPct == null ? 'neutral' : ipcPct > 10 ? 'danger' : ipcPct > 5 ? 'warn' : 'ok'

  const m2Severity =
    m2Val == null ? 'neutral' : m2Val > 15 ? 'danger' : m2Val > 8 ? 'warn' : 'ok'

  const goMacro = () => setActiveTab('macro')

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-[10px] text-tertiary uppercase tracking-wider font-mono mr-1 hidden sm:inline">
        Macro
      </span>

      {ipcPct != null && (
        <MacroChip
          label="IPC (monthly)"
          value={`${ipcPct > 0 ? '+' : ''}${ipcPct.toFixed(1)}%`}
          sub={ipcLatest ? `${ipcLatest.year}-${String(ipcLatest.month).padStart(2, '0')}` : undefined}
          severity={ipcSeverity}
          onClick={goMacro}
        />
      )}

      {m2Val != null && (
        <MacroChip
          label="M2 Growth"
          value={`${m2Val > 0 ? '+' : ''}${m2Val.toFixed(1)}%`}
          sub="mom"
          severity={m2Severity}
          onClick={goMacro}
        />
      )}

      {cestaUsd != null && (
        <MacroChip
          label="Cesta Básica"
          value={`$${cestaUsd.toFixed(0)}`}
          sub="latest"
          severity="neutral"
          onClick={goMacro}
        />
      )}

      {oilRevenue != null && (
        <MacroChip
          label="Oil Revenue"
          value={`$${oilRevenue.toFixed(1)}B`}
          sub="annual est."
          severity="neutral"
          onClick={goMacro}
        />
      )}

      {ipcPct == null && m2Val == null && cestaUsd == null && (
        <button
          className="text-xs text-tertiary hover:text-secondary transition-colors flex items-center gap-1"
          onClick={goMacro}
        >
          <AlertTriangle className="w-3 h-3" />
          Upload macro data to see indicators
        </button>
      )}
    </div>
  )
}
