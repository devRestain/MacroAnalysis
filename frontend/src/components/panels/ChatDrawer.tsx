import { useState, useRef, useEffect } from 'react'
import { X, Send, Bot, User } from 'lucide-react'
import { api } from '../../lib/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const QUICK_PROMPTS = [
  '지금 경기 사이클은 어느 단계인가요?',
  'HY 크레딧 스프레드 현황을 해석해주세요.',
  '섹터 로테이션 신호가 있나요?',
  '다음 FOMC 결과를 어떻게 예상하시나요?',
]

interface Props {
  onClose: () => void
}

export function ChatDrawer({ onClose }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send(text: string) {
    if (!text.trim() || loading) return
    const userMsg: Message = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)
    try {
      const res = await api.aiChat(text)
      setMessages((prev) => [...prev, { role: 'assistant', content: res.reply }])
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'AI 응답 중 오류가 발생했습니다.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-x-0 bottom-0 h-[65vh] bg-surface-card border-t border-surface-border z-50 flex flex-col animate-slide-up shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <Bot size={16} className="text-accent" />
          <span className="text-sm font-semibold text-text-primary">AI 채팅</span>
          <span className="text-xs text-text-muted">— 오늘 지표 데이터 자동 주입</span>
        </div>
        <button onClick={onClose} className="p-1.5 hover:bg-surface-hover rounded transition-colors">
          <X size={16} className="text-text-secondary" />
        </button>
      </div>

      {/* Quick prompts */}
      {messages.length === 0 && (
        <div className="flex flex-wrap gap-2 px-4 py-3 border-b border-surface-border">
          {QUICK_PROMPTS.map((p) => (
            <button
              key={p}
              onClick={() => send(p)}
              className="text-xs px-2.5 py-1.5 bg-surface-hover hover:bg-accent/20 hover:text-accent text-text-secondary rounded transition-colors"
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
              msg.role === 'user' ? 'bg-accent/20' : 'bg-surface-hover'
            }`}>
              {msg.role === 'user'
                ? <User size={12} className="text-accent" />
                : <Bot size={12} className="text-text-secondary" />
              }
            </div>
            <div className={`max-w-[80%] text-sm leading-relaxed whitespace-pre-wrap px-3 py-2 rounded-lg ${
              msg.role === 'user'
                ? 'bg-accent/20 text-text-primary'
                : 'bg-surface-hover text-text-primary'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-6 h-6 rounded-full bg-surface-hover flex items-center justify-center">
              <Bot size={12} className="text-text-secondary" />
            </div>
            <div className="bg-surface-hover px-3 py-2 rounded-lg">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-1.5 h-1.5 bg-text-muted rounded-full animate-pulse-soft"
                    style={{ animationDelay: `${i * 0.2}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-surface-border flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send(input)}
          placeholder="거시경제에 대해 질문하세요..."
          className="flex-1 bg-surface-hover border border-surface-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent/50 transition-colors"
        />
        <button
          onClick={() => send(input)}
          disabled={!input.trim() || loading}
          className="px-3 py-2 bg-accent/20 hover:bg-accent/30 disabled:opacity-40 text-accent rounded-lg transition-colors"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  )
}
