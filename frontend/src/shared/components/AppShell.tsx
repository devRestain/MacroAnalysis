import { ReactNode } from 'react'
import { Activity, BrainCircuit, CalendarDays, LineChart, Newspaper, Radio, RefreshCw, ServerCog, Signal } from 'lucide-react'
import { useLanguage } from '../i18n'

const nav = [
  { href: '/dashboard', labelKey: 'nav.dashboard', icon: Activity },
  { href: '/indicators', labelKey: 'nav.indicators', icon: LineChart },
  { href: '/calendar', labelKey: 'nav.calendar', icon: CalendarDays },
  { href: '/communications', labelKey: 'nav.communications', icon: Radio },
  { href: '/narrative', labelKey: 'nav.narrative', icon: Signal },
  { href: '/news', labelKey: 'nav.news', icon: Newspaper },
  { href: '/ai', labelKey: 'nav.ai', icon: BrainCircuit },
  { href: '/system', labelKey: 'nav.system', icon: ServerCog },
]

export function AppShell({ children, route }: { children: ReactNode; route: string }) {
  const { locale, setLocale, t } = useLanguage()
  const showRefresh = route === '/dashboard'

  return (
    <div className="min-h-screen bg-surface text-text-primary">
      <header className="sticky top-0 z-40 border-b border-surface-border/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex w-full max-w-[1800px] items-center gap-3 px-4 py-3 lg:px-5 2xl:px-6">
          <a href="/dashboard" className="inline-flex shrink-0 items-center gap-3 rounded-full border border-surface-border bg-white px-3 py-2 shadow-sm shadow-slate-200/50">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-accent/10 text-accent">
              <Activity size={16} />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-extrabold tracking-[-0.03em] text-text-primary">{t('app.title')}</span>
              <span className="block text-[11px] text-text-muted">{t('app.tagline')}</span>
            </span>
          </a>
          <nav className="no-scrollbar flex min-w-0 flex-1 items-center gap-2 overflow-x-auto">
            {nav.map((item) => {
              const Icon = item.icon
              const active = route === item.href || (item.href !== '/dashboard' && route.startsWith(item.href))
              return (
                <a
                  key={item.href}
                  href={item.href}
                  className={`inline-flex shrink-0 items-center gap-2 rounded-full border px-3 py-2 text-sm font-semibold transition-colors ${
                    active
                      ? 'border-accent/20 bg-accent/10 text-accent'
                      : 'border-transparent bg-transparent text-text-secondary hover:border-surface-border hover:bg-white hover:text-text-primary'
                  }`}
                >
                  <Icon size={15} />
                  <span>{t(item.labelKey)}</span>
                </a>
              )
            })}
          </nav>
          <div className="flex shrink-0 items-center gap-2">
            {showRefresh && (
              <button
                onClick={() => window.dispatchEvent(new CustomEvent('macro:dashboard-refresh'))}
                className="inline-flex items-center gap-2 rounded-full border border-surface-border bg-white px-3.5 py-2 text-xs font-bold text-text-secondary shadow-sm shadow-slate-200/50 hover:border-accent/35 hover:text-accent"
              >
                <RefreshCw size={13} />
                {t('dashboard.refresh')}
              </button>
            )}
            <div className="inline-flex rounded-full border border-surface-border bg-white p-1 text-[11px] font-bold shadow-sm shadow-slate-200/50">
              <button
                onClick={() => setLocale('ko')}
                className={`rounded-full px-2.5 py-1.5 ${locale === 'ko' ? 'bg-accent text-white' : 'text-text-muted'}`}
              >
                {t('locale.ko')}
              </button>
              <button
                onClick={() => setLocale('en')}
                className={`rounded-full px-2.5 py-1.5 ${locale === 'en' ? 'bg-accent text-white' : 'text-text-muted'}`}
              >
                {t('locale.en')}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="relative">{children}</main>
    </div>
  )
}
