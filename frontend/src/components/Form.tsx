/** Shared form primitives (RTL, Persian labels). */
import type { ReactNode } from 'react'

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      {children}
    </label>
  )
}

const inputClass =
  'rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none ' +
  'focus:border-sky-500 focus:ring-2 focus:ring-sky-100 disabled:bg-slate-100'

export function Select({
  value,
  onChange,
  options,
  placeholder = 'انتخاب کنید',
}: {
  value: string
  onChange: (v: string) => void
  options: { value: string | number; label: string }[]
  placeholder?: string
}) {
  return (
    <select className={inputClass} value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">{placeholder}</option>
      {options.map((o, idx) => (
        <option key={idx} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  )
}

export function Input({
  value,
  onChange,
  type = 'text',
  step,
}: {
  value: string
  onChange: (v: string) => void
  type?: string
  step?: string
}) {
  return (
    <input
      className={inputClass}
      type={type}
      step={step}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

export function SubmitButton({ children, busy }: { children: ReactNode; busy?: boolean }) {
  return (
    <button
      type="submit"
      disabled={busy}
      className="mt-2 rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white
                 transition hover:bg-sky-700 disabled:bg-slate-400"
    >
      {busy ? 'در حال ارسال…' : children}
    </button>
  )
}

export function Banner({ kind, children }: { kind: 'ok' | 'error'; children: ReactNode }) {
  const styles =
    kind === 'ok'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
      : 'border-rose-200 bg-rose-50 text-rose-800'
  return <div className={`rounded-lg border px-4 py-3 text-sm ${styles}`}>{children}</div>
}

export function Card({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <header className="mb-5">
        <h2 className="text-lg font-bold text-slate-800">{title}</h2>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </header>
      {children}
    </section>
  )
}
