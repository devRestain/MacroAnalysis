import { ReactNode } from 'react'
import { Activity, BrainCircuit, CalendarDays, LineChart, Newspaper, Radio, ServerCog, Signal } from 'lucide-react'

const nav = [
  { href: '/dashboard', label: 'Dashboard', icon: Activity },
  { href: '/indicators', label: 'Indicators', icon: LineChart },
  { href: '/calendar', label: 'Calendar', icon: CalendarDays },
  { href: '/communications', label: 'Communications', icon: Radio },
  { href: '/narrative', label: 'Narrative', icon: Signal },
  { href: '/news', label: 'News', icon: Newspaper },
  { href: '/ai', label: 'AI', icon: BrainCircuit },
  { href: '/system', label: 'System', icon: ServerCog },
]

export function AppShell({ children, route }: { children: ReactNode; route: string }) {
  return (
    <div className="min-h-screen bg-surface text-text-primary">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-56 border-r border-surface-border bg-surface/95 lg:block">
        <div className="flex h-14 items-center gap-2 border-b border-surface-border px-4">
          <Activity size={18} className="text-accent" />
          <div>
            <div className="text-sm font-semibold">MacroAnalysis</div>
            <div className="text-[11px] text-text-muted">Macro analysis console</div>
          </div>
        </div>
        <nav className="space-y-1 px-2 py-3">
          {nav.map((item) => {
            const Icon = item.icon
            const active = route === item.href || (item.href !== '/dashboard' && route.startsWith(item.href))
            return (
              <a
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
                  active ? 'bg-surface-hover text-text-primary' : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary'
                }`}
              >
                <Icon size={15} />
                {item.label}
              </a>
            )
          })}
        </nav>
      </aside>

      <header className="sticky top-0 z-30 border-b border-surface-border bg-surface/95 backdrop-blur lg:hidden">
        <div className="flex h-12 items-center gap-2 overflow-x-auto px-3">
          <span className="shrink-0 text-sm font-semibold">MacroAnalysis</span>
          {nav.map((item) => (
            <a key={item.href} href={item.href} className="shrink-0 px-2 py-1 text-xs text-text-secondary">
              {item.label}
            </a>
          ))}
        </div>
      </header>

      <main className="lg:pl-56">{children}</main>
    </div>
  )
}

