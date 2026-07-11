import { useEffect, useCallback } from 'react'
import { Command } from 'cmdk'
import { LayoutDashboard, Upload, DollarSign, CreditCard, TrendingUp, RefreshCw, Sun, Moon } from 'lucide-react'
import { useAppStore } from '@/stores/appStore'
import type { Tab } from '@/lib/types'

const navItems: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: 'upload', label: 'Upload Data', icon: <Upload className="w-4 h-4" /> },
  { id: 'income', label: 'Income & Salary', icon: <DollarSign className="w-4 h-4" /> },
  { id: 'subscriptions', label: 'Subscriptions', icon: <CreditCard className="w-4 h-4" /> },
  { id: 'macro', label: 'Macro Analysis', icon: <TrendingUp className="w-4 h-4" /> },
  { id: 'rates', label: 'Exchange Rates', icon: <RefreshCw className="w-4 h-4" /> },
]

export function CommandBar() {
  const { commandBarOpen, setCommandBarOpen, setActiveTab, toggleTheme, theme } = useAppStore()

  const close = useCallback(() => setCommandBarOpen(false), [setCommandBarOpen])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCommandBarOpen(!commandBarOpen)
      }
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [commandBarOpen, setCommandBarOpen, close])

  if (!commandBarOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]"
      onClick={(e) => e.target === e.currentTarget && close()}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={close} />

      {/* Command panel */}
      <div className="relative w-full max-w-lg mx-4 bg-[var(--surface-elevated)] border border-[var(--border)] rounded-xl shadow-2xl overflow-hidden">
        <Command className="flex flex-col">
          <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--border)]">
            <svg className="w-4 h-4 text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <Command.Input
              placeholder="Jump to..."
              className="flex-1 bg-transparent text-sm text-primary placeholder:text-tertiary outline-none"
              autoFocus
            />
            <kbd className="text-[10px] font-medium text-tertiary bg-[var(--border)] px-1.5 py-0.5 rounded">ESC</kbd>
          </div>

          <Command.List className="max-h-72 overflow-y-auto py-2">
            <Command.Empty className="py-6 text-center text-sm text-tertiary">No results found.</Command.Empty>

            <Command.Group heading={<span className="px-3 py-1 text-[11px] font-medium text-tertiary uppercase tracking-wider">Navigate</span>}>
              {navItems.map((item) => (
                <Command.Item
                  key={item.id}
                  value={item.label}
                  onSelect={() => {
                    setActiveTab(item.id)
                    close()
                  }}
                  className="flex items-center gap-3 px-3 py-2 mx-1 rounded-lg text-sm text-secondary cursor-pointer aria-selected:bg-[var(--surface)] aria-selected:text-primary hover:bg-[var(--surface)] hover:text-primary transition-colors"
                >
                  <span className="text-tertiary">{item.icon}</span>
                  {item.label}
                </Command.Item>
              ))}
            </Command.Group>

            <Command.Group heading={<span className="px-3 py-1 text-[11px] font-medium text-tertiary uppercase tracking-wider">Actions</span>}>
              <Command.Item
                value="toggle theme dark light"
                onSelect={() => { toggleTheme(); close() }}
                className="flex items-center gap-3 px-3 py-2 mx-1 rounded-lg text-sm text-secondary cursor-pointer aria-selected:bg-[var(--surface)] aria-selected:text-primary hover:bg-[var(--surface)] hover:text-primary transition-colors"
              >
                {theme === 'dark'
                  ? <Sun className="w-4 h-4 text-tertiary" />
                  : <Moon className="w-4 h-4 text-tertiary" />}
                {theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  )
}
