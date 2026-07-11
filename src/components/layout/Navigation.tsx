import { LayoutDashboard, Upload, DollarSign, CreditCard, TrendingUp, RefreshCw, Sun, Moon, Search, FlaskConical, MessageSquare } from 'lucide-react'
import { useAppStore } from '@/stores/appStore'
import { cn } from '@/lib/utils'
import type { Tab } from '@/lib/types'

const tabs: { id: Tab; label: string; icon: React.ReactNode; badge?: string }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: 'upload', label: 'Upload', icon: <Upload className="w-4 h-4" /> },
  { id: 'income', label: 'Income', icon: <DollarSign className="w-4 h-4" /> },
  { id: 'subscriptions', label: 'Subscriptions', icon: <CreditCard className="w-4 h-4" /> },
  { id: 'macro', label: 'Macro', icon: <TrendingUp className="w-4 h-4" /> },
  { id: 'rates', label: 'Rates', icon: <RefreshCw className="w-4 h-4" /> },
  { id: 'scenarios', label: 'Scenarios', icon: <FlaskConical className="w-4 h-4" /> },
  { id: 'chat', label: 'Chat', icon: <MessageSquare className="w-4 h-4" />, badge: 'AI' },
]

export function Navigation() {
  const { activeTab, setActiveTab, toggleTheme, theme, setCommandBarOpen } = useAppStore()

  return (
    <header className="sticky top-0 z-40 h-14 flex items-center justify-between px-4 border-b border-[var(--border)] bg-[var(--bg)] backdrop-blur-sm bg-opacity-80">
      {/* Logo */}
      <div className="flex items-center gap-3 min-w-[140px]">
        <div className="w-6 h-6 rounded bg-[var(--accent-green)] opacity-90 flex items-center justify-center">
          <TrendingUp className="w-3.5 h-3.5 text-white" />
        </div>
        <span className="text-sm font-semibold text-primary tracking-tight">Budget Intel</span>
      </div>

      {/* Tab navigation */}
      <nav className="flex items-center gap-0.5" aria-label="Main navigation">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            aria-current={activeTab === tab.id ? 'page' : undefined}
            className={cn(
              'flex items-center gap-1.5 px-3 h-8 rounded-lg text-sm transition-all duration-150',
              activeTab === tab.id
                ? 'text-primary bg-[var(--surface-elevated)]'
                : 'text-secondary hover:text-primary hover:bg-[var(--surface)]'
            )}
          >
            {tab.icon}
            <span className="hidden sm:inline">{tab.label}</span>
            {tab.badge && (
              <span className="hidden sm:inline text-[9px] font-mono font-bold tracking-wider px-1 py-0.5 rounded bg-[var(--accent-green)]/20 text-[var(--accent-green)]">
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* Right actions */}
      <div className="flex items-center gap-1 min-w-[140px] justify-end">
        <button
          onClick={() => setCommandBarOpen(true)}
          className="flex items-center gap-1.5 h-7 px-2 rounded-lg text-xs text-tertiary border border-[var(--border)] hover:text-secondary hover:border-[var(--text-tertiary)] transition-all duration-150"
          aria-label="Open command bar"
        >
          <Search className="w-3 h-3" />
          <span className="hidden md:inline">⌘K</span>
        </button>
        <button
          onClick={toggleTheme}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-tertiary hover:text-secondary hover:bg-[var(--surface)] transition-all duration-150"
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>
    </header>
  )
}
