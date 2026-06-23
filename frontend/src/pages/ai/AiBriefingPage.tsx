import { useState } from 'react'
import { Send } from 'lucide-react'
import { AiSummaryType } from '../../entities/aiSummary/types'
import { getTypedAiSummary, sendAiChat } from '../../shared/api/ai'
import { Card } from '../../shared/components/Card'
import { useLanguage } from '../../shared/i18n'
import { DisabledState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'

const summaryConfigs: { type: AiSummaryType; titleKey: string; days: number; targetKey?: string }[] = [
  { type: 'macro', titleKey: 'ai.summary.macro', days: 7 },
  { type: 'market', titleKey: 'ai.summary.market', days: 7 },
  { type: 'calendar', titleKey: 'ai.summary.calendar', days: 30 },
  { type: 'communication', titleKey: 'ai.summary.communication', days: 30, targetKey: 'Powell' },
]

export function AiBriefingPage() {
  const { t } = useLanguage()
  return (
    <div className="page-shell animate-fade-up">
      <div className="grid gap-4 xl:grid-cols-2">
        {summaryConfigs.map((config) => <SummaryCard key={`${config.type}-${config.targetKey ?? 'all'}`} {...config} />)}
        <AiChatPanel />
      </div>
    </div>
  )
}

function SummaryCard({ type, titleKey, days, targetKey }: { type: AiSummaryType; titleKey: string; days: number; targetKey?: string }) {
  const { t, label } = useLanguage()
  const summary = useResource(() => getTypedAiSummary(type, { days, targetKey }), [type, days, targetKey], { optional: true })
  const title = t(titleKey)
  return (
    <Card title={title} eyebrow={targetKey ? `${label('summaryType', type, type)} / ${targetKey}` : label('summaryType', type, type)} tone={type === 'communication' ? 'rose' : type === 'calendar' ? 'amber' : 'blue'}>
      {summary.state.status === 'success' ? (
        <article>
          <h2 className="text-xl font-extrabold leading-8 tracking-[-0.02em]">{summary.state.data.headline ?? title}</h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-text-secondary">{summary.state.data.body ?? t('ai.summaryBodyFallback')}</p>
          <div className="mt-4 text-xs font-medium text-text-muted">{summary.state.data.summaryDate ?? '-'} · {summary.state.data.modelUsed ?? t('ai.modelUnavailable')}</div>
        </article>
      ) : summary.state.status === 'disabled' ? <DisabledState label={t('ai.summaryDisabled')} /> : summary.state.status === 'error' ? <ErrorState label={t('ai.summaryError')} /> : <LoadingState />}
    </Card>
  )
}

function AiChatPanel() {
  const { t } = useLanguage()
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
      setError(t('ai.chatUnavailable'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title={t('ai.card.chat')} eyebrow={t('ai.card.chatEyebrow')} tone="green" className="xl:col-span-2">
      <div className="min-h-56 space-y-3">
        {messages.length === 0 && <p className="text-sm text-text-muted">{t('ai.chatEmpty')}</p>}
        {messages.map((message, index) => (
          <div key={index} className={`max-w-3xl rounded-[20px] border px-4 py-3 text-sm leading-7 shadow-sm ${message.role === 'user' ? 'ml-auto border-accent/20 bg-accent/10' : 'border-surface-border bg-white/80'}`}>
            {message.content}
          </div>
        ))}
        {loading && <LoadingState label={t('ai.chatLoading')} />}
        {error && <ErrorState label={error} />}
      </div>
      <div className="mt-4 flex gap-2 border-t border-surface-border pt-4">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => event.key === 'Enter' && submit(input)}
          className="min-w-0 flex-1 rounded-full border border-surface-border bg-white px-4 py-3 text-sm outline-none transition-colors focus:border-accent"
          placeholder={t('ai.chatPlaceholder')}
        />
        <button onClick={() => submit(input)} disabled={!input.trim() || loading} className="inline-flex items-center gap-2 rounded-full bg-accent px-4 py-3 text-sm font-bold text-white disabled:opacity-40">
          <Send size={14} />{t('ai.send')}
        </button>
      </div>
    </Card>
  )
}
