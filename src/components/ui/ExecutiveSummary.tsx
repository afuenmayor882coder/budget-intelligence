import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import { NarrativeBlock } from './NarrativeBlock'

interface ExecutiveSummaryProps {
  text: string
  loading?: boolean
  onRefresh?: () => void
  className?: string
}

export function ExecutiveSummary({ text, loading = false, onRefresh, className }: ExecutiveSummaryProps) {
  if (loading) {
    return (
      <div className={cn('space-y-2 py-4', className)}>
        <div className="h-3 bg-surface-elevated animate-pulse rounded w-16 mb-3" />
        <div className="h-4 bg-surface-elevated animate-pulse rounded w-full" />
        <div className="h-4 bg-surface-elevated animate-pulse rounded w-11/12" />
        <div className="h-4 bg-surface-elevated animate-pulse rounded w-4/5" />
      </div>
    )
  }

  if (!text) return null

  return (
    <motion.div
      className={cn('py-4', className)}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <div className="flex items-center gap-2 mb-3">
        <Sparkles size={12} className="text-accent-green" />
        <span className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary">
          Analysis
        </span>
      </div>

      <NarrativeBlock
        text={text}
        variant="editorial"
        collapsible={true}
        maxLines={5}
        onRefresh={onRefresh}
        className="text-text-primary text-sm leading-relaxed"
      />
    </motion.div>
  )
}
