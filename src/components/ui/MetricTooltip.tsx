import { useState, useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'
import type { VerdictExplanation } from './VerdictCard'

interface MetricTooltipProps {
  children: React.ReactNode
  explanation: VerdictExplanation | string
  className?: string
}

export function MetricTooltip({ children, explanation, className }: MetricTooltipProps) {
  const [visible, setVisible] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!visible) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setVisible(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [visible])

  const verdict = typeof explanation === 'string' ? explanation : explanation.verdict
  const color = typeof explanation === 'string' ? 'neutral' : (explanation.color || 'neutral')

  const borderColor = {
    green: 'border-[var(--accent-green)]/40',
    amber: 'border-[var(--accent-amber)]/40',
    red: 'border-[var(--accent-red)]/40',
    neutral: 'border-[var(--border)]',
  }[color as string] || 'border-[var(--border)]'

  return (
    <div
      ref={ref}
      className={cn('relative inline-flex', className)}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      <span className="cursor-help border-b border-dotted border-[var(--text-tertiary)]">{children}</span>
      {visible && (
        <div
          className={cn(
            'absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64',
            'p-3 rounded-lg border bg-[var(--surface-elevated)] shadow-lg',
            'text-xs text-secondary leading-relaxed',
            borderColor,
          )}
          role="tooltip"
        >
          {verdict}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px border-4 border-transparent border-t-[var(--surface-elevated)]" />
        </div>
      )}
    </div>
  )
}
