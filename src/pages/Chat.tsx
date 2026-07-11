import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Send, Bot, User, Trash2, Key, ChevronDown, ChevronUp, Sparkles, Info } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { chat as chatApi } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { Card } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import type { ChatMessage } from '@/lib/types'
import { toast } from 'sonner'

const CONVERSATION_ID = 'main'

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user'
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
      className={cn('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}
    >
      {/* Avatar */}
      <div className={cn(
        'w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5',
        isUser
          ? 'bg-[var(--accent-green)]/20 text-[var(--accent-green)]'
          : 'bg-[var(--surface-elevated)] text-secondary'
      )}>
        {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
      </div>

      {/* Bubble */}
      <div className={cn(
        'max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
        isUser
          ? 'bg-[var(--accent-green)]/15 border border-[var(--accent-green)]/25 text-primary rounded-tr-sm'
          : 'bg-[var(--surface)] border border-[var(--border)] text-primary rounded-tl-sm'
      )}>
        {isUser ? (
          <p>{msg.content}</p>
        ) : (
          <div className="prose prose-sm prose-invert max-w-none
            prose-p:my-1 prose-ul:my-1 prose-li:my-0.5
            prose-strong:text-primary prose-code:text-[var(--accent-green)]
            prose-code:bg-[var(--surface-elevated)] prose-code:px-1 prose-code:rounded">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        )}

        <div className={cn(
          'flex items-center gap-2 mt-2 pt-1.5 border-t',
          isUser ? 'border-[var(--accent-green)]/20' : 'border-[var(--border)]'
        )}>
          <span className="text-[10px] text-tertiary">
            {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          {msg.category && !isUser && (
            <Badge variant="default" className="text-[9px] py-0 h-4">{msg.category}</Badge>
          )}
          {msg.source && msg.source !== 'rule_based' && !isUser && (
            <Badge variant="green" className="text-[9px] py-0 h-4">
              <Sparkles className="w-2.5 h-2.5 mr-0.5" />
              {msg.source}
            </Badge>
          )}
        </div>
      </div>
    </motion.div>
  )
}

function ApiKeyConfig() {
  const [open, setOpen] = useState(false)
  const { chatAnthropicKey, chatOpenaiKey, setChatAnthropicKey, setChatOpenaiKey } = useAppStore()
  const [localAnthropic, setLocalAnthropic] = useState(chatAnthropicKey)
  const [localOpenai, setLocalOpenai] = useState(chatOpenaiKey)

  const save = () => {
    setChatAnthropicKey(localAnthropic.trim())
    setChatOpenaiKey(localOpenai.trim())
    toast.success('API keys saved')
    setOpen(false)
  }

  const hasKey = Boolean(chatAnthropicKey || chatOpenaiKey)

  return (
    <div className="border-b border-[var(--border)]">
      <button
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-[var(--surface)] transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-2">
          <Key className="w-3.5 h-3.5 text-tertiary" />
          <span className="text-xs text-secondary">LLM API Key</span>
          {hasKey ? (
            <Badge variant="green">Connected</Badge>
          ) : (
            <Badge variant="default">Rule-based mode</Badge>
          )}
        </div>
        {open ? <ChevronUp className="w-3.5 h-3.5 text-tertiary" /> : <ChevronDown className="w-3.5 h-3.5 text-tertiary" />}
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3">
          <p className="text-xs text-tertiary flex items-start gap-1.5">
            <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
            Keys are stored locally in your browser only. Without a key, the assistant uses
            rule-based analysis (no LLM). With a key, responses are enhanced by Claude / GPT.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Anthropic API Key"
              type="password"
              placeholder="sk-ant-..."
              value={localAnthropic}
              onChange={(e) => setLocalAnthropic(e.target.value)}
            />
            <Input
              label="OpenAI API Key"
              type="password"
              placeholder="sk-..."
              value={localOpenai}
              onChange={(e) => setLocalOpenai(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2">
            {hasKey && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setChatAnthropicKey('')
                  setChatOpenaiKey('')
                  setLocalAnthropic('')
                  setLocalOpenai('')
                  toast.success('API keys removed')
                }}
              >
                Remove keys
              </Button>
            )}
            <Button variant="primary" size="sm" onClick={save}>Save</Button>
          </div>
        </div>
      )}
    </div>
  )
}

function SuggestionPill({ text, onClick }: { text: string; onClick: () => void }) {
  return (
    <button
      className="px-3 py-1.5 text-xs rounded-full border border-[var(--border)] text-secondary hover:text-primary hover:border-[var(--text-tertiary)] transition-all duration-150 text-left whitespace-nowrap"
      onClick={onClick}
    >
      {text}
    </button>
  )
}

export function ChatPage() {
  const { chatAnthropicKey, chatOpenaiKey } = useAppStore()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const { data: suggestionsData } = useQuery({
    queryKey: ['chat-suggestions'],
    queryFn: chatApi.getSuggestions,
    staleTime: 5 * 60_000,
    retry: 1,
  })
  const suggestions: string[] = suggestionsData?.suggestions ?? []

  // Load conversation history on mount
  const { data: history } = useQuery({
    queryKey: ['chat-history'],
    queryFn: () => chatApi.getHistory(CONVERSATION_ID),
    retry: 1,
  })

  useEffect(() => {
    if (history?.messages && history.messages.length > 0 && messages.length === 0) {
      const hydrated: ChatMessage[] = history.messages.map((m: any, i: number) => ({
        id: `hist-${i}`,
        role: m.role,
        content: m.content,
        timestamp: new Date().toISOString(),
      }))
      setMessages(hydrated)
    }
  }, [history])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking])

  const sendMessage = async (text: string) => {
    const msgText = text.trim()
    if (!msgText) return

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: msgText,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsThinking(true)

    try {
      const res = await chatApi.sendMessage({
        message: msgText,
        conversation_id: CONVERSATION_ID,
        anthropic_api_key: chatAnthropicKey || undefined,
        openai_api_key: chatOpenaiKey || undefined,
      })

      const assistantMsg: ChatMessage = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: res.reply,
        category: res.category,
        mode: res.mode,
        source: res.source,
        timestamp: res.timestamp,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err: any) {
      toast.error(err.message ?? 'Chat failed')
      setMessages((prev) => [...prev, {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        timestamp: new Date().toISOString(),
      }])
    } finally {
      setIsThinking(false)
    }
  }

  const clearChat = async () => {
    try {
      await chatApi.clearHistory(CONVERSATION_ID)
      setMessages([])
      toast.success('Conversation cleared')
    } catch {
      setMessages([])
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 h-[calc(100vh-3.5rem)] flex flex-col gap-0">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-lg font-semibold text-primary flex items-center gap-2">
            <Bot className="w-5 h-5 text-[var(--accent-green)]" />
            Financial Assistant
          </h1>
          <p className="text-xs text-tertiary mt-0.5">
            {chatAnthropicKey || chatOpenaiKey
              ? 'LLM-enhanced · asks answered from your live data'
              : 'Rule-based analysis · add an API key for LLM responses'}
          </p>
        </div>
        {messages.length > 0 && (
          <Button variant="ghost" size="sm" onClick={clearChat}>
            <Trash2 className="w-3.5 h-3.5 mr-1.5" />
            Clear
          </Button>
        )}
      </div>

      {/* Chat container */}
      <Card className="flex-1 flex flex-col overflow-hidden" padding="none">
        <ApiKeyConfig />

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {isEmpty && (
            <div className="flex flex-col items-center justify-center h-full text-center gap-4 py-8">
              <div className="w-14 h-14 rounded-2xl bg-[var(--surface-elevated)] border border-[var(--border)] flex items-center justify-center">
                <Bot className="w-7 h-7 text-[var(--accent-green)] opacity-80" />
              </div>
              <div>
                <p className="text-sm font-medium text-primary mb-1">Ask me anything about your finances</p>
                <p className="text-xs text-tertiary max-w-xs">
                  I analyse your uploaded data in real time — spending, forecasts, purchasing power, runway, and more.
                </p>
              </div>

              {suggestions.length > 0 && (
                <div className="flex flex-wrap gap-2 justify-center max-w-md">
                  {suggestions.map((q, i) => (
                    <SuggestionPill key={i} text={q} onClick={() => sendMessage(q)} />
                  ))}
                </div>
              )}
            </div>
          )}

          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
          </AnimatePresence>

          {isThinking && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-3"
            >
              <div className="w-7 h-7 rounded-full bg-[var(--surface-elevated)] flex items-center justify-center flex-shrink-0">
                <Bot className="w-3.5 h-3.5 text-secondary" />
              </div>
              <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
                {[0, 1, 2].map((i) => (
                  <motion.span
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-[var(--text-tertiary)]"
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                  />
                ))}
              </div>
            </motion.div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Suggestions row (when messages exist) */}
        {!isEmpty && suggestions.length > 0 && (
          <div className="px-4 py-2 border-t border-[var(--border)] flex gap-2 overflow-x-auto no-scrollbar">
            {suggestions.slice(0, 4).map((q, i) => (
              <SuggestionPill key={i} text={q} onClick={() => sendMessage(q)} />
            ))}
          </div>
        )}

        {/* Input */}
        <div className="px-4 py-3 border-t border-[var(--border)] flex gap-3 items-end">
          <textarea
            className={cn(
              'flex-1 resize-none rounded-xl border border-[var(--border)] bg-[var(--surface)]',
              'text-sm text-primary placeholder:text-tertiary',
              'px-3 py-2.5 min-h-[42px] max-h-[120px]',
              'focus:outline-none focus:border-[var(--accent-green)]/60',
              'transition-colors duration-150'
            )}
            placeholder="Ask about your finances… (Enter to send, Shift+Enter for newline)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isThinking}
          />
          <Button
            variant="primary"
            size="sm"
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isThinking}
            className="h-[42px] w-[42px] p-0 flex items-center justify-center flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </Card>
    </div>
  )
}
