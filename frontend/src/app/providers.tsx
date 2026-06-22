import { ReactNode } from 'react'
import { LanguageProvider } from '../shared/i18n'

export function Providers({ children }: { children: ReactNode }) {
  return <LanguageProvider>{children}</LanguageProvider>
}
