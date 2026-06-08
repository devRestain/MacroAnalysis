import { Home } from './pages/Home'
import { News } from './pages/News'
import { Fomc } from './pages/Fomc'

function getRoute() {
  const hashRoute = window.location.hash.replace('#', '')
  return hashRoute || window.location.pathname || '/'
}

export default function App() {
  const route = getRoute()

  if (route === '/') return <Home />
  if (route === '/news') return <News />
  if (route === '/fomc') return <Fomc />
  return <Home />
}
