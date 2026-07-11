import { motion } from 'framer-motion'
import { AlertTriangle, AlertCircle, Info, X, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

export type AlertSeverity = 'critical' | 'warning' | 'notice' | 'info'

interface AlertCardProps {
  severity: AlertSeverity
  subject: string
  text: string
  insightId?: string
  onDismiss?: (id: string) => void
  onClick?: () => void
  compact?: boolean
}

const SEVERITY_CONFIG: Record<AlertSeverity, {
  icon: React.ComponentType<{ size?: number; className?: string }>
  bg: string
  border: string
  iconColor: string
  label: string
}> = {
  critical: {
    icon: AlertCircle,
    bg: 'bg-accent-red/5',
    border: 'border-accent-red/20',
    iconColor: 'text-accent-red',
    label: 'CRITICAL',
  },
  warning: {
    icon: AlertTriangle,
    bg: 'bg-accent-amber/5',
    border: 'border-accent-amber/20',
    iconColor: 'text-accent-amber',
    label: 'WARNING',
  },
  notice: {
    icon: AlertTriangle,
    bg: 'bg-accent-blue/5',
    border: 'border-accent-blue/20',
    iconColor: 'text-accent-blue',
    label: 'NOTICE',
  },
  info: {
    icon: Info,
    bg: 'bg-surface',
    border: 'border-border',
    iconColor: 'text-text-tertiary',
    label: 'INFO',
  },
}

export function AlertCard({
  severity,
  subject,
  text,
  insightId,
  onDismiss,
  onClick,
  compact = false,
}: AlertCardProps) {
  const config = SEVERITY_CONFIG[severity]
  const Icon = config.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      className={cn(
        'relative rounded-lg border p-3 transition-all',
        config.bg,
        config.border,
        onClick && 'cursor-pointer hover:scale-[1.005]',
      )}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        <Icon size={16} className={cn('mt-0.5 shrink-0', config.iconColor)} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className={cn(
              'font-mono text-[9px] font-semibold tracking-wider uppercase',
              config.iconColor,
            )}>
              {config.label}
            </span>
            <span className="text-xs font-medium text-text-primary truncate">{subject}</span>
          </div>
          {!compact && (
            <p className="text-xs text-text-secondary leading-relaxed">{text}</p>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {onClick && <ChevronRight size={12} className="text-text-tertiary" />}
          {onDismiss && insightId && (
            <button
              onClick={(e) => { e.stopPropagation(); onDismiss(insightId) }}
              className="text-text-tertiary hover:text-text-secondary transition-colors p-0.5"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  )
}
