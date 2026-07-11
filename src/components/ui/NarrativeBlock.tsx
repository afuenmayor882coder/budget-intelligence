import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'

interface NarrativeBlockProps {
  text: string
  className?: string
  collapsible?: boolean
  maxLines?: number
  onRefresh?: () => void
  loading?: boolean
  variant?: 'default' | 'editorial' | 'compact'
}

export function NarrativeBlock({
  text,
  className,
  collapsible = false,
  maxLines = 6,
  onRefresh,
  loading = false,
  variant = 'default',
}: NarrativeBlockProps) {
  const [expanded, setExpanded] = useState(false)

  if (loading) {
    return (
      <div className={cn('space-y-2', className)}>
        <div className="h-4 bg-surface-elevated animate-pulse rounded w-full" />
        <div className="h-4 bg-surface-elevated animate-pulse rounded w-5/6" />
        <div className="h-4 bg-surface-elevated animate-pulse rounded w-4/5" />
      </div>
    )
  }

  if (!text) return null

  const sentences = text.split(/(?<=[.!?])\s+/)
  const shouldCollapse = collapsible && sentences.length > 3

  return (
    <div className={cn('group relative', className)}>
      <AnimatePresence initial={false}>
        <motion.p
          className={cn(
            'leading-relaxed text-text-secondary',
            variant === 'editorial' && 'font-serif text-text-primary',
            variant === 'compact' && 'text-sm',
            variant === 'default' && 'text-sm',
          )}
          style={
            shouldCollapse && !expanded
              ? { display: '-webkit-box', WebkitLineClamp: maxLines, WebkitBoxOrient: 'vertical', overflow: 'hidden' }
              : {}
          }
        >
          {text}
        </motion.p>
      </AnimatePresence>

      <div className="flex items-center gap-3 mt-2">
        {shouldCollapse && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-text-tertiary hover:text-text-secondary transition-colors"
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {expanded ? 'Read less' : 'Read more'}
          </button>
        )}

        {onRefresh && (
          <button
            onClick={onRefresh}
            className="flex items-center gap-1 text-xs text-text-tertiary hover:text-accent-green transition-colors opacity-0 group-hover:opacity-100 ml-auto"
            title="Get alternate phrasing"
          >
            <RefreshCw size={11} />
            <span>Rephrase</span>
          </button>
        )}
      </div>
    </div>
  )
}
