/**
 * Shared dual-theme UI primitives for the redesign shell.
 *
 * The prototype hardcoded dark surfaces (bg-slate-900 everywhere); these
 * components carry the light/dark variant pairs every page needs, so views stay
 * terse and the factory-floor light mode actually works.
 */
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

export const inputCls =
  'w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:border-sky-400'

export const tableCls = 'w-full text-right text-xs'
export const thCls =
  'p-2.5 font-semibold bg-slate-100 dark:bg-slate-800/80 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700'
export const trCls = 'border-b border-slate-100 dark:border-slate-800/60 hover:bg-slate-50 dark:hover:bg-slate-800/40'

export function PageHeader({
  icon: Icon,
  title,
  subtitle,
  color = 'sky',
  actions,
}: {
  icon: LucideIcon
  title: string
  subtitle?: string
  color?: 'sky' | 'amber' | 'cyan' | 'rose' | 'emerald' | 'indigo'
  actions?: ReactNode
}) {
  const colors: Record<string, string> = {
    sky: 'bg-sky-500/15 text-sky-600 dark:text-sky-400 border-sky-500/20',
    amber: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/20',
    cyan: 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 border-cyan-500/20',
    rose: 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/20',
    emerald: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
    indigo: 'bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border-indigo-500/20',
  }
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-xl border flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white">{title}</h1>
          {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm ${className}`}>
      {children}
    </div>
  )
}

export function PanelTitle({ icon: Icon, title, aside }: { icon: LucideIcon; title: string; aside?: ReactNode }) {
  return (
    <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800 mb-4">
      <div className="flex items-center gap-2">
        <Icon className="w-5 h-5 text-slate-400" />
        <h2 className="text-sm font-bold text-slate-900 dark:text-white">{title}</h2>
      </div>
      {aside}
    </div>
  )
}

export function Field({ label, required, children }: { label: string; required?: boolean; children: ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1.5">
        {label} {required && <span className="text-rose-500">*</span>}
      </label>
      {children}
    </div>
  )
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputCls} ${props.className ?? ''}`} />
}

export function SelectInput(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${inputCls} ${props.className ?? ''}`} />
}

export function Banner({ kind, children }: { kind: 'ok' | 'error' | 'info'; children: ReactNode }) {
  const cls =
    kind === 'ok'
      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300'
      : kind === 'error'
        ? 'bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300'
        : 'bg-sky-500/10 border-sky-500/30 text-sky-700 dark:text-sky-300'
  return <div className={`p-4 rounded-xl border text-sm ${cls}`}>{children}</div>
}

export function SubmitButton({
  busy,
  children,
  color = 'sky',
  className = '',
}: {
  busy: boolean
  children: ReactNode
  color?: 'sky' | 'amber' | 'cyan' | 'rose' | 'emerald' | 'indigo'
  className?: string
}) {
  const colors: Record<string, string> = {
    sky: 'bg-sky-600 hover:bg-sky-500 text-white shadow-sky-600/20',
    amber: 'bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-amber-500/20',
    cyan: 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-600/20',
    rose: 'bg-rose-600 hover:bg-rose-500 text-white shadow-rose-600/20',
    emerald: 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20',
    indigo: 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/20',
  }
  return (
    <button
      type="submit"
      disabled={busy}
      className={`w-full py-2.5 rounded-xl font-bold text-sm shadow-lg transition-all hover:scale-[1.01] disabled:opacity-60 disabled:hover:scale-100 ${colors[color]} ${className}`}
    >
      {busy ? '…' : children}
    </button>
  )
}
