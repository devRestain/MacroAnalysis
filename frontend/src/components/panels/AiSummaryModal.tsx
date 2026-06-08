import { X, Bot } from 'lucide-react'
import { AiSummaryResponse } from '../../lib/api'

interface Props {
  summary: AiSummaryResponse | null
  loading: boolean
  onClose: () => void
}

export function AiSummaryModal({ summary, loading, onClose }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative w-full max-w-2xl max-h-[85vh] bg-surface-card border border-surface-border rounded-t-2xl sm:rounded-2xl flex flex-col overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center gap-2 px-5 py-4 border-b border-surface-border">
          <Bot size={16} className="text-accent" />
          <div className="flex-1">
            <div className="text-sm font-semibold text-text-primary">AI 일일 거시 브리핑</div>
            {summary && (
              <div className="text-xs text-text-secondary">
                {new Date(summary.date).toLocaleDateString('ko-KR', {
                  year: 'numeric', month: 'long', day: 'numeric',
                })} · {summary.model}
              </div>
            )}
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-surface-hover rounded transition-colors">
            <X size={16} className="text-text-secondary" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {loading && (
            <div className="text-center text-text-muted text-sm py-8">요약 로딩 중...</div>
          )}
          {!loading && !summary && (
            <div className="text-center text-text-muted text-sm py-8">
              오늘의 AI 요약이 아직 생성되지 않았습니다.<br />
              <span className="text-xs">매일 오전 6:30 KST에 자동 생성됩니다.</span>
            </div>
          )}
          {summary && (
            <div className="prose prose-sm prose-invert max-w-none">
              <div className="text-text-primary text-sm leading-7 whitespace-pre-wrap">
                {summary.body}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
