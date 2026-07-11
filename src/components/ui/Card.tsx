import { cn } from '@/lib/utils'

interface CardProps {
  children: React.ReactNode
  className?: string
  onClick?: () => void
  hoverable?: boolean
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

const paddingStyles = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
}

export function Card({ children, className, onClick, hoverable, padding = 'md' }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-surface rounded-xl border border-[var(--border)]',
        hoverable && 'cursor-pointer transition-colors duration-150 hover:bg-[var(--surface-elevated)]',
        onClick && 'cursor-pointer',
        paddingStyles[padding],
        className
      )}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('flex items-center justify-between mb-4', className)}>{children}</div>
}

export function CardTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return <h3 className={cn('text-sm font-medium text-secondary', className)}>{children}</h3>
}
