import { useState } from 'react'
import { Send } from 'lucide-react'
import { AiSummaryType } from '../../entities/aiSummary/types'
import { getTypedAiSummary, sendAiChat } from '../../shared/api/ai'
import { Card } from '../../shared/components/Card'
import { DisabledState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'

const summaryConfigs: { type: AiSummaryType; title: string; days: number; targetKey?: string }[] = [
  { type: 'macro', title: 'Macro Summary', days: 7 },
  { type: 'market', title: 'Market Summary', days: 7 },
  { type: 'calendar', title: 'Calendar Summary', days: 30 },
  { type: 'communication', title: 'Communication Summary', days: 30, targetKey: 'Powell' },
]

export function AiBriefingPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-6 lg:px-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">AI Briefing</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">Typed AI summaries for macro, market, calendar, and communication contexts.</p>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        {summaryConfigs.map((config) => <SummaryCard key={`${config.type}-${config.targetKey ?? 'all'}`} {...config} />)}
        <AiChatPanel />
      </div>
    </div>
  )
}

function SummaryCard({ type, title, days, targetKey }: { type: AiSummaryType; title: string; days: number; targetKey?: string }) {
  const summary = useResource(() => getTypedAiSummary(type, { days, targetKey }), [type, days, targetKey], { optional: true })
  return (
    <Card title={title} eyebrow={targetKey ? `${type} / ${targetKey}` : type}>
      {summary.state.status === 'success' ? (
        <article>
          <h2 className="text-lg font-semibold leading-7">{summary.state.data.headline ?? title}</h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-text-secondary">{summary.state.data.body ?? 'No summary body available.'}</p>
          <div className="mt-4 text-xs text-text-muted">{summary.state.data.summaryDate ?? '-'} · {summary.state.data.modelUsed ?? 'model unavailable'}</div>
        </article>
      ) : summary.state.status === 'disabled' ? <DisabledState label="AI summary is not enabled or not authorized." /> : summary.state.status === 'error' ? <ErrorState label="AI summary could not be loaded." /> : <LoadingState />}
    </Card>
  )
}

function AiChatPanel() {
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(text: string) {
    if (!text.trim() || loading) return
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setInput('')
    setLoading(true)
    setError(null)
    try {
      const reply = await sendAiChat(text)
      setMessages((prev) => [...prev, { role: 'assistant', content: reply.reply }])
    } catch {
      setError('AI chat is unavailable in the current environment.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="AI Chat" eyebrow="optional X-API-Key on chat only" className="xl:col-span-2">
      <div className="min-h-56 space-y-3">
        {messages.length === 0 && <p className="text-sm text-text-muted">Ask about latest collected macro context, policy communications, or watch items.</p>}
        {messages.map((message, index) => (
          <div key={index} className={`max-w-3xl border px-3 py-2 text-sm leading-6 ${message.role === 'user' ? 'ml-auto border-accent/30 bg-accent/10' : 'border-surface-border bg-surface-hover'}`}>
            {message.content}
          </div>
        ))}
        {loading && <LoadingState label="Generating briefing response..." />}
        {error && <ErrorState label={error} />}
      </div>
      <div className="mt-4 flex gap-2 border-t border-surface-border pt-4">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => event.key === 'Enter' && submit(input)}
          className="min-w-0 flex-1 border border-surface-border bg-surface-hover px-3 py-2 text-sm outline-none focus:border-accent"
          placeholder="Ask for macro context..."
        />
        <button onClick={() => submit(input)} disabled={!input.trim() || loading} className="inline-flex items-center gap-2 bg-accent/20 px-3 py-2 text-sm text-accent disabled:opacity-40">
          <Send size={14} />Send
        </button>
      </div>
    </Card>
  )
}

