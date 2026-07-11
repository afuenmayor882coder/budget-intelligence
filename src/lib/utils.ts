import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatUSD(value: number, compact = false): string {
  if (compact && Math.abs(value) >= 1000) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(value)
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatVES(value: number, compact = false): string {
  if (compact && Math.abs(value) >= 1000) {
    const formatted = new Intl.NumberFormat('en-US', {
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(value)
    return `${formatted} Bs`
  }
  return `${new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)} Bs`
}

export function formatPct(value: number, signed = false): string {
  const abs = Math.abs(value)
  const formatted = `${abs.toFixed(1)}%`
  if (!signed) return formatted
  return value >= 0 ? `+${formatted}` : `-${formatted}`
}

export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'

  const trimmed = dateStr.trim()
  let normalized = trimmed

  if (!trimmed.includes('T')) {
    if (/^\d{4}-\d{2}-\d{2} \d/.test(trimmed)) {
      // Backend returns SQL-style datetimes: "2026-07-10 14:37:30"
      normalized = trimmed.replace(' ', 'T')
    } else if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
      normalized = `${trimmed}T00:00:00`
    }
  }

  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return trimmed

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

export function formatMonthYear(year: number, month: number): string {
  const date = new Date(year, month - 1, 1)
  return new Intl.DateTimeFormat('en-US', { month: 'short', year: 'numeric' }).format(date)
}

export function monthName(month: number): string {
  return new Date(2000, month - 1, 1).toLocaleString('en-US', { month: 'long' })
}

export function deltaColor(value: number, invertColors = false): string {
  if (value === 0) return 'var(--text-secondary)'
  const positive = value > 0
  if (invertColors) return positive ? 'var(--accent-red)' : 'var(--accent-green)'
  return positive ? 'var(--accent-green)' : 'var(--accent-red)'
}

export function clampValue(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

export function generateId(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}
