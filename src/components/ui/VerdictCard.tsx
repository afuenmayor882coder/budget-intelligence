import { useState } from 'react'
import { ChevronDown, ChevronUp, Info } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface VerdictExplanation {
  type?: string
  verdict: string
  because?: string
  deep_dive?: string
  severity?: 'excellent' | 'good' | 'moderate' | 'concerning' | 'critical' | 'informational'
  color?: 'green' | 'amber' | 'red' | 'neutral'
  raw?: unknown
}

const severityStyles = {
  green: 'border-[var(--accent-green)]/30 bg-[var(--accent-green)]/5',
  amber: 'border-[var(--accent-amber)]/30 bg-[var(--accent-amber)]/5',
  red: 'border-[var(--accent-red)]/30 bg-[var(--accent-red)]/5',
  neutral: 'border-[var(--border)] bg-[var(--surface-elevated)]',
}

const severityText = {
  green: 'text-[var(--accent-green)]',
  amber: 'text-[var(--accent-amber)]',
  red: 'text-[var(--accent-red)]',
  neutral: 'text-secondary',
}

interface VerdictCardProps {
  explanation: VerdictExplanation
  title?: string
  defaultExpanded?: boolean
  className?: string
}

export function VerdictCard({
  explanation,
  title,
  defaultExpanded = false,
  className,
}: VerdictCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const color = explanation.color || 'neutral'

  return (
    <div
      className={cn(
        'rounded-xl border p-4 transition-colors duration-150',
        severityStyles[color as keyof typeof severityStyles] || severityStyles.neutral,
        className,
      )}
    >
      <div className="flex items-start gap-2">
        <Info className={cn('w-4 h-4 mt-0.5 shrink-0', severityText[color as keyof typeof severityText])} />
        <div className="flex-1 min-w-0">
          {title && (
            <p className="text-xs uppercase tracking-wider text-tertiary mb-1">{title}</p>
          )}
          <p className="text-sm text-primary leading-relaxed">{explanation.verdict}</p>
          {explanation.because && (
            <p className="text-xs text-secondary mt-2 leading-relaxed">{explanation.because}</p>
          )}
          {expanded && explanation.deep_dive && (
            <p className="text-xs text-tertiary mt-3 leading-relaxed border-t border-[var(--border)] pt-3">
              {explanation.deep_dive}
            </p>
          )}
        </div>
        {explanation.deep_dive && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="text-tertiary hover:text-secondary transition-colors p-1"
            aria-label={expanded ? 'Collapse explanation' : 'Expand explanation'}
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        )}
      </div>
    </div>
  )
}
