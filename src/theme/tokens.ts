export const colors = {
  dark: {
    bg: '#0d0d0d',
    surface: '#171717',
    surfaceElevated: '#1f1f1f',
    border: '#262626',
    textPrimary: '#ececec',
    textSecondary: '#a0a0a0',
    textTertiary: '#6b6b6b',
  },
  light: {
    bg: '#ffffff',
    surface: '#fafafa',
    surfaceElevated: '#f5f5f5',
    border: '#e5e5e5',
    textPrimary: '#0d0d0d',
    textSecondary: '#525252',
    textTertiary: '#a3a3a3',
  },
  accent: {
    green: '#10a37f',
    red: '#ef4444',
    blue: '#3b82f6',
    amber: '#f59e0b',
  },
}

export const typography = {
  fontSans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  fontMono: "'JetBrains Mono', 'IBM Plex Mono', 'Fira Code', monospace",
  scale: {
    display: { size: '48px', lineHeight: '1.1' },
    h1: { size: '32px', lineHeight: '1.2' },
    h2: { size: '24px', lineHeight: '1.3' },
    h3: { size: '18px', lineHeight: '1.4' },
    body: { size: '14px', lineHeight: '1.5' },
    small: { size: '12px', lineHeight: '1.4' },
    heroMono: { size: '56px', lineHeight: '1', letterSpacing: '-0.02em' },
  },
}

export const motion = {
  easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
  duration: {
    fast: 0.15,
    normal: 0.25,
    slow: 0.4,
  },
  variants: {
    fadeUp: {
      hidden: { opacity: 0, y: 8 },
      visible: { opacity: 1, y: 0 },
    },
    fadeIn: {
      hidden: { opacity: 0 },
      visible: { opacity: 1 },
    },
    stagger: {
      visible: {
        transition: { staggerChildren: 0.04 },
      },
    },
    scaleIn: {
      hidden: { opacity: 0, scale: 0.97 },
      visible: { opacity: 1, scale: 1 },
    },
  },
}
