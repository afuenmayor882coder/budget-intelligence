import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Tab, Theme } from '@/lib/types'

interface AppState {
  theme: Theme
  activeTab: Tab
  commandBarOpen: boolean
  chatAnthropicKey: string
  chatOpenaiKey: string
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
  setActiveTab: (tab: Tab) => void
  setCommandBarOpen: (open: boolean) => void
  setChatAnthropicKey: (key: string) => void
  setChatOpenaiKey: (key: string) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      theme: 'dark',
      activeTab: 'dashboard',
      commandBarOpen: false,
      chatAnthropicKey: '',
      chatOpenaiKey: '',

      setTheme: (theme) => {
        set({ theme })
        document.documentElement.setAttribute('data-theme', theme)
      },

      toggleTheme: () => {
        const next = get().theme === 'dark' ? 'light' : 'dark'
        set({ theme: next })
        document.documentElement.setAttribute('data-theme', next)
      },

      setActiveTab: (tab) => set({ activeTab: tab }),
      setCommandBarOpen: (open) => set({ commandBarOpen: open }),
      setChatAnthropicKey: (key) => set({ chatAnthropicKey: key }),
      setChatOpenaiKey: (key) => set({ chatOpenaiKey: key }),
    }),
    {
      name: 'budget-app-state',
      partialize: (state) => ({
        theme: state.theme,
        activeTab: state.activeTab,
        chatAnthropicKey: state.chatAnthropicKey,
        chatOpenaiKey: state.chatOpenaiKey,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          document.documentElement.setAttribute('data-theme', state.theme)
        }
      },
    }
  )
)
