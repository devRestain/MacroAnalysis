import { ReactNode } from 'react'
import { Activity, BrainCircuit, CalendarDays, LineChart, Newspaper, Radio, ServerCog, Signal } from 'lucide-react'

const nav = [
  { href: '/dashboard', label: 'Dashboard', meta: 'Overview', icon: Activity },
  { href: '/indicators', label: 'Indicators', meta: 'Observations', icon: LineChart },
  { href: '/calendar', label: 'Calendar', meta: 'Events', icon: CalendarDays },
  { href: '/communications', label: 'Communications', meta: 'Fed trail', icon: Radio },
  { href: '/narrative', label: 'Narrative', meta: 'Signals', icon: Signal },
  { href: '/news', label: 'News', meta: 'Coverage', icon: Newspaper },
  { href: '/ai', label: 'AI', meta: 'Briefings', icon: BrainCircuit },
  { href: '/system', label: 'System', meta: 'Health', icon: ServerCog },
]

export function AppShell({ children, route }: { children: ReactNode; route: string }) {
  return (
    <div className="min-h-screen bg-surface text-text-primary">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 border-r border-surface-border bg-[#f9fbfd] px-4 py-5 xl:block">
        <div className="flex items-center gap-3 px-2 pb-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-surface-border bg-white text-accent">
            <Activity size={16} />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-extrabold tracking-[-0.02em]">MacroAnalysis</div>
            <div className="text-[11px] text-text-muted">Macro intelligence</div>
          </div>
        </div>
        <div className="mb-3 px-2 text-[11px] font-bold uppercase tracking-[0.22em] text-text-muted">Entities</div>
        <nav className="space-y-1">
          {nav.map((item) => {
            const Icon = item.icon
            const active = route === item.href || (item.href !== '/dashboard' && route.startsWith(item.href))
            return (
              <a
                key={item.href}
                href={item.href}
                className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 ${
                  active ? 'bg-white text-text-primary' : 'text-text-secondary hover:bg-white hover:text-text-primary'
                }`}
              >
                <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border ${
                  active ? 'border-accent/20 bg-accent/5 text-accent' : 'border-surface-border bg-white text-text-secondary'
                }`}>
                  <Icon size={15} />
                </div>
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold">{item.label}</div>
                  <div className="truncate text-[11px] text-text-muted">{item.meta}</div>
                </div>
              </a>
            )
          })}
        </nav>
      </aside>

      <header className="sticky top-0 z-30 border-b border-surface-border bg-surface/95 backdrop-blur xl:hidden">
        <div className="flex h-14 items-center gap-3 overflow-x-auto px-3">
          <span className="shrink-0 text-sm font-extrabold tracking-[-0.02em]">MacroAnalysis</span>
          {nav.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold ${
                route === item.href || (item.href !== '/dashboard' && route.startsWith(item.href))
                  ? 'bg-white text-accent shadow-sm'
                  : 'text-text-secondary'
              }`}
            >
              {item.label}
            </a>
          ))}
        </div>
      </header>

      <main className="relative xl:pl-60">{children}</main>
    </div>
  )
}
