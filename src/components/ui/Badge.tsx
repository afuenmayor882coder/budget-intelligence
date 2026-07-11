import { cn } from '@/lib/utils'

type BadgeVariant = 'default' | 'green' | 'red' | 'amber' | 'blue' | 'outline'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  className?: string
  dot?: boolean
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-surface-elevated text-secondary border-subtle border',
  green: 'bg-accent-green-muted text-accent-green border border-[var(--accent-green)] border-opacity-20',
  red: 'bg-accent-red-muted text-accent-red border border-[var(--accent-red)] border-opacity-20',
  amber: 'bg-accent-amber-muted text-accent-amber border border-[var(--accent-amber)] border-opacity-20',
  blue: 'bg-accent-blue-muted text-accent-blue border border-[var(--accent-blue)] border-opacity-20',
  outline: 'border-subtle border text-tertiary',
}

export function Badge({ children, variant = 'default', className, dot }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium tracking-wider uppercase mono',
        variantStyles[variant],
        className
      )}
    >
      {dot && (
        <span
          className={cn(
            'inline-block w-1.5 h-1.5 rounded-full',
            variant === 'green' && 'bg-[var(--accent-green)]',
            variant === 'red' && 'bg-[var(--accent-red)]',
            variant === 'amber' && 'bg-[var(--accent-amber)]',
            variant === 'blue' && 'bg-[var(--accent-blue)]',
            variant === 'default' && 'bg-[var(--text-secondary)]',
            variant === 'outline' && 'bg-[var(--text-tertiary)]'
          )}
        />
      )}
      {children}
    </span>
  )
}
