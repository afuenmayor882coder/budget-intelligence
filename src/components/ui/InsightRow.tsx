import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus, ChevronDown, AlertTriangle, CheckCircle, Info } from 'lucide-react'
import { cn } from '@/lib/utils'

interface InsightRowProps {
  id: string
  subject: string
  text: string
  direction?: 'up' | 'down' | 'steady'
  severity?: 'critical' | 'warning' | 'notice' | 'info'
  magnitude?: string
  onExpand?: (id: string) => void
  expandedText?: string
}

const DIRECTION_ICON = {
  up: TrendingUp,
  down: TrendingDown,
  steady: Minus,
}

const SEVERITY_COLOR = {
  critical: 'text-accent-red',
  warning: 'text-accent-amber',
  notice: 'text-accent-blue',
  info: 'text-text-tertiary',
}

export function InsightRow({
  id,
  subject,
  text,
  direction = 'steady',
  severity = 'info',
  magnitude,
  onExpand,
  expandedText,
}: InsightRowProps) {
  const [open, setOpen] = useState(false)
  const DirectionIcon = DIRECTION_ICON[direction]

  const handleToggle = () => {
    setOpen(!open)
    if (!open && onExpand) onExpand(id)
  }

  return (
    <div className="border-b border-border last:border-0 py-2.5">
      <button
        className="w-full flex items-start gap-2.5 text-left group"
        onClick={handleToggle}
      >
        <DirectionIcon
          size={14}
          className={cn(
            'mt-0.5 shrink-0',
            direction === 'up' && severity === 'warning' ? 'text-accent-red' :
            direction === 'up' ? 'text-accent-green' :
            direction === 'down' ? 'text-accent-red' :
            'text-text-tertiary',
          )}
        />
        <div className="flex-1 min-w-0">
          <span className="text-xs font-medium text-text-primary">{subject}</span>
          <span className="text-xs text-text-secondary ml-2 leading-relaxed">{text}</span>
        </div>
        {expandedText && (
          <ChevronDown
            size={12}
            className={cn(
              'mt-0.5 text-text-tertiary shrink-0 transition-transform duration-200',
              open && 'rotate-180',
            )}
          />
        )}
      </button>

      <AnimatePresence>
        {open && expandedText && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <p className="text-xs text-text-tertiary leading-relaxed mt-2 pl-[22px]">
              {expandedText}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
