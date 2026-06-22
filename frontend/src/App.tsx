import { LanguageProvider } from './shared/i18n'
import { DashboardPage } from './pages/dashboard/DashboardPage'
import { IndicatorsPage } from './pages/indicators/IndicatorsPage'
import { IndicatorDetailPage } from './pages/indicators/IndicatorDetailPage'
import { CalendarPage } from './pages/calendar/CalendarPage'
import { CommunicationsPage } from './pages/communications/CommunicationsPage'
import { NarrativePage } from './pages/narrative/NarrativePage'
import { NewsPage } from './pages/news/NewsPage'
import { AiBriefingPage } from './pages/ai/AiBriefingPage'
import { SystemStatusPage } from './pages/system/SystemStatusPage'
import { AppShell } from './shared/components/AppShell'

function getCurrentRoute() {
  const hashRoute = window.location.hash.replace('#', '')
  return hashRoute || window.location.pathname || '/'
}

function normalizeRoute(route: string) {
  if (route === '/' || route === '') return '/dashboard'
  if (route === '/fomc') return '/calendar'
  return route.replace(/\/$/, '') || '/dashboard'
}

function renderCurrentPage(route: string) {
  const indicatorMatch = route.match(/^\/indicators\/([^/]+)$/)

  if (route === '/dashboard') return <DashboardPage />
  if (route === '/indicators') return <IndicatorsPage />
  if (indicatorMatch) return <IndicatorDetailPage indicatorKey={decodeURIComponent(indicatorMatch[1])} />
  if (route === '/calendar') return <CalendarPage />
  if (route === '/communications') return <CommunicationsPage />
  if (route === '/narrative') return <NarrativePage />
  if (route === '/news') return <NewsPage />
  if (route === '/ai') return <AiBriefingPage />
  if (route === '/system') return <SystemStatusPage />
  return <DashboardPage />
}

export default function App() {
  const route = normalizeRoute(getCurrentRoute())

  return (
    <LanguageProvider>
      <AppShell route={route}>{renderCurrentPage(route)}</AppShell>
    </LanguageProvider>
  )
}
