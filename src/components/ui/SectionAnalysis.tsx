import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { NarrativeBlock } from './NarrativeBlock'

interface SectionAnalysisProps {
  text: string
  loading?: boolean
  onRefresh?: () => void
  className?: string
  label?: string
}

export function SectionAnalysis({ text, loading = false, onRefresh, className, label }: SectionAnalysisProps) {
  if (loading) {
    return (
      <div className={cn('space-y-1.5', className)}>
        <div className="h-3.5 bg-surface-elevated animate-pulse rounded w-full" />
        <div className="h-3.5 bg-surface-elevated animate-pulse rounded w-4/5" />
      </div>
    )
  }

  if (!text) return null

  return (
    <motion.div
      className={cn('', className)}
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {label && (
        <span className="font-mono text-[9px] uppercase tracking-widest text-text-tertiary block mb-1.5">
          {label}
        </span>
      )}
      <NarrativeBlock
        text={text}
        variant="compact"
        collapsible={text.length > 200}
        onRefresh={onRefresh}
      />
    </motion.div>
  )
}
