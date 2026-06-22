import { ReactNode } from 'react'
import { Activity, BrainCircuit, CalendarDays, LineChart, Newspaper, Radio, ServerCog, Signal } from 'lucide-react'
import { useLanguage } from '../i18n'

const nav = [
  { href: '/dashboard', labelKey: 'nav.dashboard', metaKey: 'nav.dashboardMeta', icon: Activity },
  { href: '/indicators', labelKey: 'nav.indicators', metaKey: 'nav.indicatorsMeta', icon: LineChart },
  { href: '/calendar', labelKey: 'nav.calendar', metaKey: 'nav.calendarMeta', icon: CalendarDays },
  { href: '/communications', labelKey: 'nav.communications', metaKey: 'nav.communicationsMeta', icon: Radio },
  { href: '/narrative', labelKey: 'nav.narrative', metaKey: 'nav.narrativeMeta', icon: Signal },
  { href: '/news', labelKey: 'nav.news', metaKey: 'nav.newsMeta', icon: Newspaper },
  { href: '/ai', labelKey: 'nav.ai', metaKey: 'nav.aiMeta', icon: BrainCircuit },
  { href: '/system', labelKey: 'nav.system', metaKey: 'nav.systemMeta', icon: ServerCog },
]

export function AppShell({ children, route }: { children: ReactNode; route: string }) {
  const { locale, setLocale, t } = useLanguage()

  return (
    <div className="min-h-screen bg-surface text-text-primary">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 border-r border-surface-border bg-[#f9fbfd] px-4 py-5 xl:block">
        <div className="flex items-center gap-3 px-2 pb-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-surface-border bg-white text-accent">
            <Activity size={16} />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-extrabold tracking-[-0.02em]">{t('app.title')}</div>
            <div className="text-[11px] text-text-muted">{t('app.tagline')}</div>
          </div>
        </div>
        <div className="mb-3 flex items-center justify-between gap-2 px-2">
          <div className="text-[11px] font-bold uppercase tracking-[0.22em] text-text-muted">{t('app.entities')}</div>
          <div className="inline-flex rounded-full border border-surface-border bg-white p-1 text-[11px] font-bold">
            <button
              onClick={() => setLocale('ko')}
              className={`rounded-full px-2 py-1 ${locale === 'ko' ? 'bg-accent text-white' : 'text-text-muted'}`}
            >
              {t('locale.ko')}
            </button>
            <button
              onClick={() => setLocale('en')}
              className={`rounded-full px-2 py-1 ${locale === 'en' ? 'bg-accent text-white' : 'text-text-muted'}`}
            >
              {t('locale.en')}
            </button>
          </div>
        </div>
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
                  <div className="truncate text-sm font-semibold">{t(item.labelKey)}</div>
                  <div className="truncate text-[11px] text-text-muted">{t(item.metaKey)}</div>
                </div>
              </a>
            )
          })}
        </nav>
      </aside>

      <header className="sticky top-0 z-30 border-b border-surface-border bg-surface/95 backdrop-blur xl:hidden">
        <div className="flex h-14 items-center gap-3 overflow-x-auto px-3">
          <span className="shrink-0 text-sm font-extrabold tracking-[-0.02em]">{t('app.title')}</span>
          <button
            onClick={() => setLocale(locale === 'ko' ? 'en' : 'ko')}
            className="shrink-0 rounded-full border border-surface-border bg-white px-3 py-1.5 text-[11px] font-bold text-text-secondary"
          >
            {locale === 'ko' ? t('locale.en') : t('locale.ko')}
          </button>
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
              {t(item.labelKey)}
            </a>
          ))}
        </div>
      </header>

      <main className="relative xl:pl-60">{children}</main>
    </div>
  )
}
