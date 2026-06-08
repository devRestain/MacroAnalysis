import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api, AiSummaryResponse, SectorRow } from '../lib/api'
import { Zone1Alerts } from '../components/zones/Zone1Alerts'
import { Zone2Grid } from '../components/zones/Zone2Grid'
import { Zone3Trio } from '../components/zones/Zone3Trio'
import { Zone4Heatmap } from '../components/zones/Zone4Heatmap'
import { Zone5Sectors } from '../components/zones/Zone5Sectors'
import { Zone6Equities } from '../components/zones/Zone6Equities'
import { SidePanel } from '../components/panels/SidePanel'
import { ChatDrawer } from '../components/panels/ChatDrawer'
import { AiSummaryModal } from '../components/panels/AiSummaryModal'
import { RefreshCw, Activity } from 'lucide-react'

export function Home() {
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [aiModalOpen, setAiModalOpen] = useState(false)

  const { data: summary, loading: summaryLoading, refetch } = useApi(
    () => api.summary(),
    [],
    5 * 60 * 1000  // refresh every 5 minutes
  )

  const { data: changes } = useApi(
    () => api.changes(),
    [],
    10 * 60 * 1000
  )

  const { data: sectors } = useApi(
    () => api.sectors(),
    [],
    30 * 60 * 1000
  )

  const { data: aiSummary, loading: aiLoading } = useApi(
    () => api.aiSummary().catch(() => null as unknown as AiSummaryResponse),
    []
  )

  const selectedSnap = selectedKey && summary?.snapshots[selectedKey]
    ? summary.snapshots[selectedKey]
    : null

  const sectorRows: SectorRow[] = sectors?.sectors ?? []

  const updatedAt = summary?.updated_at
    ? new Date(summary.updated_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
    : null

  return (
    <div className="min-h-screen bg-surface text-text-primary">
      {/* Sticky Header */}
      <header className="sticky top-0 z-40 bg-surface/95 backdrop-blur-sm border-b border-surface-border">
        <div className="flex items-center justify-between px-4 h-10">
          <div className="flex items-center gap-2">
            <Activity size={16} className="text-accent" />
            <span className="text-sm font-semibold text-text-primary">MacroWatch</span>
          </div>
          <div className="flex items-center gap-4 text-xs text-text-secondary">
            {summary?.fomc.days_left != null && (
              <span className="font-mono">
                FOMC <span className="text-accent">D-{summary.fomc.days_left}</span>
              </span>
            )}
            {updatedAt && (
              <span>최종 수집 {updatedAt}</span>
            )}
            <button
              onClick={refetch}
              disabled={summaryLoading}
              className="flex items-center gap-1 hover:text-text-primary transition-colors disabled:opacity-40"
            >
              <RefreshCw size={12} className={summaryLoading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      </header>

      {summaryLoading && !summary && (
        <div className="flex items-center justify-center h-64 text-text-muted text-sm">
          데이터 수집 중...
        </div>
      )}

      {summary && (
        <>
          <Zone1Alerts alerts={summary.alerts} onSelect={setSelectedKey} />
          <Zone2Grid
            snapshots={summary.snapshots}
            equities={summary.equities}
            onSelect={setSelectedKey}
          />
          <Zone3Trio
            yieldCurve={summary.yield_curve}
            aiHeadline={summary.ai_headline}
            newsPreview={summary.news_preview}
            onOpenChat={() => setChatOpen(true)}
            onOpenAiSummary={() => setAiModalOpen(true)}
          />
          {changes && (
            <Zone4Heatmap changes={changes.changes} onSelect={setSelectedKey} />
          )}
          <Zone5Sectors
            sectors={sectorRows}
            fomc={summary.fomc}
          />
          <Zone6Equities equities={summary.equities} />
        </>
      )}

      {/* Overlays */}
      {selectedKey && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/30"
            onClick={() => setSelectedKey(null)}
          />
          <SidePanel
            indicatorKey={selectedKey}
            snapshot={selectedSnap}
            onClose={() => setSelectedKey(null)}
          />
        </>
      )}

      {chatOpen && <ChatDrawer onClose={() => setChatOpen(false)} />}

      {aiModalOpen && (
        <AiSummaryModal
          summary={aiSummary}
          loading={aiLoading}
          onClose={() => setAiModalOpen(false)}
        />
      )}
    </div>
  )
}
