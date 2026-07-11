import { useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { useAppStore } from '@/stores/appStore'
import { Navigation } from '@/components/layout/Navigation'
import { CommandBar } from '@/components/layout/CommandBar'
import { Dashboard } from '@/pages/Dashboard'
import { UploadPage } from '@/pages/Upload'
import { IncomePage } from '@/pages/Income'
import { SubscriptionsPage } from '@/pages/Subscriptions'
import { MacroPage } from '@/pages/Macro'
import { RatesPage } from '@/pages/Rates'
import { ScenariosPage } from '@/pages/Scenarios'
import { ChatPage } from '@/pages/Chat'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function AppContent() {
  const { activeTab, theme } = useAppStore()

  // Apply theme on mount
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  return (
    <div className="min-h-screen flex flex-col bg-base">
      <Navigation />
      <CommandBar />
      <main className="flex-1">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'upload' && <UploadPage />}
        {activeTab === 'income' && <IncomePage />}
        {activeTab === 'subscriptions' && <SubscriptionsPage />}
        {activeTab === 'macro' && <MacroPage />}
        {activeTab === 'rates' && <RatesPage />}
        {activeTab === 'scenarios' && <ScenariosPage />}
        {activeTab === 'chat' && <ChatPage />}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
      <Toaster
        position="bottom-right"
        theme="dark"
        toastOptions={{
          style: {
            background: 'var(--surface-elevated)',
            border: '1px solid var(--border)',
            color: 'var(--text-primary)',
            fontSize: '13px',
          },
        }}
      />
    </QueryClientProvider>
  )
}
