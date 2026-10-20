import type { CSSProperties } from 'react'

// Apple system colors (light appearance)
export const COLORS = ['#007AFF', '#34C759', '#FF9500', '#FF3B30', '#AF52DE', '#FF2D55']

export const GRID = '#e5e5ea'

// Tooltip as a frosted material panel
export const tooltipStyle: CSSProperties = {
  backgroundColor: 'rgba(255, 255, 255, 0.82)',
  backdropFilter: 'blur(20px) saturate(180%)',
  WebkitBackdropFilter: 'blur(20px) saturate(180%)',
  border: '1px solid rgba(0, 0, 0, 0.06)',
  borderRadius: 12,
  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.12)',
  fontSize: 12,
}

// Series draw in on a short eased curve; off entirely for reduced motion
export const chartMotion = {
  isAnimationActive: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  animationDuration: 700,
  animationEasing: 'ease-out' as const,
}
