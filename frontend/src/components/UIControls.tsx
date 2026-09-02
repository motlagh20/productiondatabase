/** Theme + language switches, shared by the navbar and the login screen. */
import { Moon, Sun } from 'lucide-react'

import { useUI } from '../context/UIContext'

export function ThemeToggle() {
  const { theme, lang, toggleTheme, t } = useUI()
  return (
    <button
      id="btn-toggle-theme"
      onClick={toggleTheme}
      title={theme === 'dark' ? t.theme_light : t.theme_dark}
      aria-label={t.theme_toggle}
      className={`px-2.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 border transition-all shadow-sm ${
        theme === 'dark'
          ? 'bg-slate-800 hover:bg-slate-700 text-amber-300 border-slate-700 hover:border-amber-400/50'
          : 'bg-amber-50 hover:bg-amber-100 text-amber-900 border-amber-300 hover:border-amber-500'
      }`}
    >
      {theme === 'dark' ? (
        <>
          <Sun className="w-4 h-4 text-amber-400 fill-amber-400/20" />
          <span className="hidden sm:inline text-[11px] font-bold tracking-tight">
            {lang === 'fa' ? 'روشن کارگاه' : 'Factory Light'}
          </span>
        </>
      ) : (
        <>
          <Moon className="w-4 h-4 text-slate-800 fill-slate-800/20" />
          <span className="hidden sm:inline text-[11px] font-bold tracking-tight">
            {lang === 'fa' ? 'تاریک مانیتورینگ' : 'Dark Mode'}
          </span>
        </>
      )}
    </button>
  )
}

export function LangSwitch() {
  const { lang, setLang } = useUI()
  return (
    <div className="flex items-center bg-slate-100 dark:bg-slate-800/80 p-0.5 rounded-lg border border-slate-300 dark:border-slate-700">
      {(['fa', 'en'] as const).map((code) => (
        <button
          key={code}
          id={`btn-lang-${code}`}
          onClick={() => setLang(code)}
          className={`px-2 py-1 text-[11px] font-bold rounded transition-colors ${
            lang === code
              ? 'bg-amber-500 text-slate-950 shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-950 dark:hover:text-white'
          }`}
        >
          {code.toUpperCase()}
        </button>
      ))}
    </div>
  )
}
