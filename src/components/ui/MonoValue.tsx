import { cn } from '@/lib/utils'

interface MonoValueProps {
  value: string | number
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | 'hero'
  className?: string
  color?: 'primary' | 'secondary' | 'green' | 'red' | 'amber' | 'blue'
  prefix?: string
  suffix?: string
}

const sizeStyles = {
  xs: 'text-xs',
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-xl',
  xl: 'text-3xl font-semibold',
  hero: 'text-5xl font-semibold tracking-tight',
}

const colorStyles = {
  primary: 'text-primary',
  secondary: 'text-secondary',
  green: 'text-accent-green',
  red: 'text-accent-red',
  amber: 'text-accent-amber',
  blue: 'text-accent-blue',
}

export function MonoValue({ value, size = 'md', className, color = 'primary', prefix, suffix }: MonoValueProps) {
  return (
    <span className={cn('mono inline-flex items-baseline gap-0.5', colorStyles[color], sizeStyles[size], className)}>
      {prefix && <span className="text-[0.6em] text-secondary">{prefix}</span>}
      {value}
      {suffix && <span className="text-[0.6em] text-secondary ml-0.5">{suffix}</span>}
    </span>
  )
}
