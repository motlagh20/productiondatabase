/**
 * UI-only context: theme (light/dark) + language (fa/en) + direction.
 *
 * The redesign prototype kept its production data in a localStorage
 * `ProductionContext`; that store is deliberately NOT ported — the Django API is
 * the only source of truth here. What survives is the presentation state, which
 * genuinely belongs in the browser.
 */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { translations } from '../i18n/translations'

export type Theme = 'light' | 'dark'
export type Lang = 'fa' | 'en'

const THEME_KEY = 'mes_theme'
const LANG_KEY = 'mes_lang'

interface UIContextValue {
  theme: Theme
  lang: Lang
  isRTL: boolean
  t: (typeof translations)['fa']
  toggleTheme: () => void
  setLang: (lang: Lang) => void
}

const UIContext = createContext<UIContextValue | null>(null)

function readStored<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  const raw = localStorage.getItem(key)
  return allowed.includes(raw as T) ? (raw as T) : fallback
}

export function UIProvider({ children }: { children: ReactNode }) {
  // Persian RTL + factory-floor light are the defaults the owner works in.
  const [theme, setTheme] = useState<Theme>(() => readStored(THEME_KEY, ['light', 'dark'] as const, 'light'))
  const [lang, setLangState] = useState<Lang>(() => readStored(LANG_KEY, ['fa', 'en'] as const, 'fa'))

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem(THEME_KEY, theme)
  }, [theme])

  useEffect(() => {
    document.documentElement.lang = lang
    document.documentElement.dir = lang === 'fa' ? 'rtl' : 'ltr'
    localStorage.setItem(LANG_KEY, lang)
  }, [lang])

  const value = useMemo<UIContextValue>(
    () => ({
      theme,
      lang,
      isRTL: lang === 'fa',
      t: translations[lang],
      toggleTheme: () => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark')),
      setLang: setLangState,
    }),
    [theme, lang],
  )

  return <UIContext.Provider value={value}>{children}</UIContext.Provider>
}

export function useUI(): UIContextValue {
  const ctx = useContext(UIContext)
  if (!ctx) throw new Error('useUI must be used inside <UIProvider>')
  return ctx
}
