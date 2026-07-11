import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

interface NumberCounterProps {
  value: number
  duration?: number
  decimals?: number
  prefix?: string
  suffix?: string
  className?: string
  formatter?: (v: number) => string
}

export function NumberCounter({
  value,
  duration = 600,
  decimals = 2,
  prefix = '',
  suffix = '',
  className,
  formatter,
}: NumberCounterProps) {
  const [displayed, setDisplayed] = useState(0)
  const startTime = useRef<number | null>(null)
  const startValue = useRef(0)
  const rafRef = useRef<number>(0)

  const prefersReduced = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    if (prefersReduced) {
      setDisplayed(value)
      return
    }

    startValue.current = displayed
    startTime.current = null

    const animate = (timestamp: number) => {
      if (!startTime.current) startTime.current = timestamp
      const elapsed = timestamp - startTime.current
      const progress = Math.min(elapsed / duration, 1)
      // ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      const current = startValue.current + (value - startValue.current) * eased
      setDisplayed(current)

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate)
      } else {
        setDisplayed(value)
      }
    }

    cancelAnimationFrame(rafRef.current)
    rafRef.current = requestAnimationFrame(animate)

    return () => cancelAnimationFrame(rafRef.current)
  }, [value]) // eslint-disable-line react-hooks/exhaustive-deps

  const formatted = formatter
    ? formatter(displayed)
    : `${prefix}${displayed.toFixed(decimals)}${suffix}`

  return (
    <span className={cn('mono tabular-nums', className)} aria-live="polite">
      {formatted}
    </span>
  )
}
