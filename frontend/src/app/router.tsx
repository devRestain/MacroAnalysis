import { DashboardPage } from '../pages/dashboard/DashboardPage'
import { IndicatorsPage } from '../pages/indicators/IndicatorsPage'
import { IndicatorDetailPage } from '../pages/indicators/IndicatorDetailPage'
import { CalendarPage } from '../pages/calendar/CalendarPage'
import { CommunicationsPage } from '../pages/communications/CommunicationsPage'
import { NarrativePage } from '../pages/narrative/NarrativePage'
import { NewsPage } from '../pages/news/NewsPage'
import { AiBriefingPage } from '../pages/ai/AiBriefingPage'
import { SystemStatusPage } from '../pages/system/SystemStatusPage'
import { AppShell } from '../shared/components/AppShell'

export function getCurrentRoute() {
  const hashRoute = window.location.hash.replace('#', '')
  return hashRoute || window.location.pathname || '/'
}

function normalizeRoute(route: string) {
  if (route === '/' || route === '') return '/dashboard'
  if (route === '/fomc') return '/calendar'
  return route.replace(/\/$/, '') || '/dashboard'
}

export function Router() {
  const route = normalizeRoute(getCurrentRoute())
  const indicatorMatch = route.match(/^\/indicators\/([^/]+)$/)

  let page = <DashboardPage />
  if (route === '/dashboard') page = <DashboardPage />
  else if (route === '/indicators') page = <IndicatorsPage />
  else if (indicatorMatch) page = <IndicatorDetailPage indicatorKey={decodeURIComponent(indicatorMatch[1])} />
  else if (route === '/calendar') page = <CalendarPage />
  else if (route === '/communications') page = <CommunicationsPage />
  else if (route === '/narrative') page = <NarrativePage />
  else if (route === '/news') page = <NewsPage />
  else if (route === '/ai') page = <AiBriefingPage />
  else if (route === '/system') page = <SystemStatusPage />

  return <AppShell route={route}>{page}</AppShell>
}

