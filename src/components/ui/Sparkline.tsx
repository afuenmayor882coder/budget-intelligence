import { useMemo } from 'react'

interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  color?: string
  strokeWidth?: number
  className?: string
}

export function Sparkline({
  data,
  width = 80,
  height = 28,
  color = 'var(--accent-green)',
  strokeWidth = 1.5,
}: SparklineProps) {
  const path = useMemo(() => {
    if (!data || data.length < 2) return ''
    const min = Math.min(...data)
    const max = Math.max(...data)
    const range = max - min || 1
    const padding = 2

    const points = data.map((v, i) => {
      const x = padding + (i / (data.length - 1)) * (width - padding * 2)
      const y = padding + ((1 - (v - min) / range) * (height - padding * 2))
      return `${x},${y}`
    })

    return 'M ' + points.join(' L ')
  }, [data, width, height])

  if (!data || data.length < 2) {
    return <svg width={width} height={height} />
  }

  const isPositive = data[data.length - 1] >= data[0]
  const lineColor = color === 'auto'
    ? (isPositive ? 'var(--accent-green)' : 'var(--accent-red)')
    : color

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <path
        d={path}
        fill="none"
        stroke={lineColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
