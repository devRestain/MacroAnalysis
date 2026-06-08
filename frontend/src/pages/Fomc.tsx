import { Activity, ArrowLeft } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'

function fmtProb(v: number | null | undefined) {
  return v == null ? '—' : `${(v * 100).toFixed(0)}%`
}

export function Fomc() {
  const { data, loading, error } = useApi(() => api.fomc(), [], 30 * 60 * 1000)
  const meetings = data?.meetings ?? []
  const nextMeeting = meetings.find((m) => new Date(m.date).getTime() >= Date.now())

  return (
    <div className="min-h-screen bg-surface text-text-primary">
      <header className="sticky top-0 z-40 bg-surface/95 backdrop-blur-sm border-b border-surface-border">
        <div className="flex items-center justify-between px-4 h-10">
          <a href="/" className="flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors">
            <ArrowLeft size={14} />
            <span className="text-xs">대시보드</span>
          </a>
          <div className="flex items-center gap-2">
            <Activity size={16} className="text-accent" />
            <span className="text-sm font-semibold">FOMC 현황</span>
          </div>
          <div className="w-16" />
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-5 space-y-4">
        {loading && <div className="py-16 text-center text-sm text-text-muted">FOMC 데이터 로딩 중...</div>}
        {error && <div className="py-16 text-center text-sm text-signal-red">FOMC 데이터를 불러오지 못했습니다.</div>}

        {!loading && !error && (
          <>
            <section className="grid grid-cols-1 md:grid-cols-2 gap-px bg-surface-border border border-surface-border">
              <div className="bg-surface-card p-4">
                <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-3">다음 회의</h2>
                {nextMeeting ? (
                  <>
                    <div className="text-2xl font-mono font-bold">
                      {new Date(nextMeeting.date).toLocaleDateString('ko-KR', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })}
                    </div>
                    <div className="mt-2 text-xs text-text-secondary">
                      발표 금리 {nextMeeting.rate ?? '미정'} · 변동폭 {nextMeeting.change_bp ?? '미정'}
                    </div>
                  </>
                ) : (
                  <div className="text-sm text-text-muted">예정된 회의가 없습니다.</div>
                )}
              </div>

              <div className="bg-surface-card p-4">
                <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-3">시장 기대</h2>
                {data?.fedwatch ? (
                  <>
                    <div className="grid grid-cols-3 gap-2">
                      <ProbCell label="동결" value={fmtProb(data.fedwatch.prob_hold)} color="text-signal-green" />
                      <ProbCell label="인하" value={fmtProb(data.fedwatch.prob_cut)} color="text-accent" />
                      <ProbCell label="인상" value={fmtProb(data.fedwatch.prob_hike)} color="text-signal-red" />
                    </div>
                    <div className="mt-3 text-xs text-text-muted">Fed Funds futures 기반 추정</div>
                  </>
                ) : (
                  <div className="text-sm text-text-muted">시장 기대 데이터가 아직 없습니다.</div>
                )}
              </div>
            </section>

            <section className="border border-surface-border bg-surface-card">
              <div className="px-4 py-3 border-b border-surface-border">
                <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-widest">회의 일정</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-surface-border text-text-muted">
                      <th className="px-4 py-2 text-left font-medium">일자</th>
                      <th className="px-4 py-2 text-left font-medium">결정 금리</th>
                      <th className="px-4 py-2 text-left font-medium">변동폭</th>
                    </tr>
                  </thead>
                  <tbody>
                    {meetings.map((meeting) => (
                      <tr key={meeting.date} className="border-b border-surface-border/50">
                        <td className="px-4 py-2 font-mono">
                          {new Date(meeting.date).toLocaleDateString('ko-KR')}
                        </td>
                        <td className="px-4 py-2 font-mono">{meeting.rate ?? '—'}</td>
                        <td className="px-4 py-2 font-mono">{meeting.change_bp ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  )
}

function ProbCell({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-surface-hover px-3 py-2">
      <div className="text-xs text-text-secondary">{label}</div>
      <div className={`mt-1 font-mono text-lg font-semibold ${color}`}>{value}</div>
    </div>
  )
}
