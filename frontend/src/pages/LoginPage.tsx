/** Login — obtains a DRF token and stores it. Redesign-styled, dual-theme. */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Factory, KeyRound, LogIn } from 'lucide-react'

import { apiErrorMessage, login } from '../api'
import { useUI } from '../context/UIContext'
import { Field, TextInput, Banner } from '../components/ui'
import { ThemeToggle, LangSwitch } from '../components/UIControls'

export default function LoginPage() {
  const navigate = useNavigate()
  const { t } = useUI()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await login(username, password)
      navigate('/dryer', { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-slate-100 via-amber-50 to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 px-4">
      <div className="absolute top-4 right-4 flex items-center gap-2">
        <ThemeToggle />
        <LangSwitch />
      </div>

      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center gap-3 mb-6">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-amber-600 via-orange-500 to-rose-500 flex items-center justify-center shadow-xl shadow-orange-500/20">
            <Factory className="w-8 h-8 text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-xl font-extrabold text-slate-900 dark:text-white">{t.app_title}</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t.brand_sub}</p>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xl p-6">
          <form onSubmit={submit} className="flex flex-col gap-4">
            <Field label={t.username} required>
              <TextInput
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                dir="ltr"
                required
              />
            </Field>
            <Field label={t.password} required>
              <TextInput
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                dir="ltr"
                required
              />
            </Field>
            <button
              type="submit"
              disabled={busy}
              className="w-full py-2.5 rounded-xl bg-gradient-to-l from-amber-600 to-orange-500 hover:from-amber-500 hover:to-orange-400 text-white font-bold text-sm shadow-lg shadow-orange-500/20 transition-all hover:scale-[1.01] disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {busy ? <>{t.logging_in}</> : <><LogIn className="w-4 h-4" />{t.login}</>}
            </button>
            {error && <Banner kind="error">{error}</Banner>}
          </form>
        </div>

        <p className="mt-4 text-center text-[11px] text-slate-400 dark:text-slate-500 flex items-center justify-center gap-1">
          <KeyRound className="w-3 h-3" />
          Token Authentication · mes_app @ PostgreSQL
        </p>
      </div>
    </div>
  )
}
