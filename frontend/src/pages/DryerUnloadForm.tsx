/**
 * Dryer unload (`/dryer/unload`) — complete the unload side of a chamber's open
 * cycle. Only chambers whose cycle has no unload_date yet are offered. Preselects
 * the chamber when arrived from the dashboard via router state.
 */
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ArrowUpFromLine, CheckCircle2, History } from 'lucide-react'

import { apiErrorMessage, fetchDryerChamberStatus, fetchDryerCycles, fetchOperators, postDryerUnload, type DryerChamberStatus, type DryerCycleData, type Operator } from '../api'
import { useUI } from '../context/UIContext'
import { Banner, Field, PageHeader, Panel, PanelTitle, SelectInput, SubmitButton, TextInput, tableCls, thCls, trCls } from '../components/ui'
import JalaliDatePicker from '../components/JalaliDatePicker'
import { formatJalali, todayJalali } from '../jalali'

function nowTime(): string {
  return new Date().toTimeString().slice(0, 5)
}

export default function DryerUnloadForm() {
  const { t } = useUI()
  const navigate = useNavigate()
  const location = useLocation() as { state: { chamberId?: number } | null }

  const [chambers, setChambers] = useState<DryerChamberStatus[]>([])
  const [operators, setOperators] = useState<Operator[]>([])
  const [cycles, setCycles] = useState<DryerCycleData[]>([])

  // Chambers with an open cycle that has not been unloaded yet
  const unloadable = chambers.filter((c) => c.is_loaded && c.current_cycle && !c.current_cycle.unload_date)

  const [chamberId, setChamberId] = useState('')
  const [fingerCount, setFingerCount] = useState('')
  const [operatorId, setOperatorId] = useState('')
  const [unloadDate, setUnloadDate] = useState(todayJalali())
  const [unloadTime, setUnloadTime] = useState(nowTime())

  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = () => {
    fetchDryerChamberStatus().then(setChambers).catch(() => {})
    fetchDryerCycles().then(setCycles).catch(() => {})
  }

  useEffect(() => {
    reload()
    fetchOperators().then(setOperators).catch(() => {})
  }, [])

  useEffect(() => {
    if (location.state?.chamberId) setChamberId(String(location.state.chamberId))
  }, [location.state])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const data = await postDryerUnload({
        chamber_id: Number(chamberId),
        unload_date: unloadDate,
        unload_time: unloadTime || undefined,
        unload_operator_id: operatorId ? Number(operatorId) : undefined,
        finger_count: fingerCount ? Number(fingerCount) : undefined,
      })
      setResult(`${t.submit_unload} ✓ (${t.chamber} #${data.dryer_cycle_id})`)
      setFingerCount('')
      reload()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const unloaded = cycles.filter((c) => c.unload_date)

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon={ArrowUpFromLine}
        title={t.dryer_unload_title}
        color="amber"
        actions={
          <button
            onClick={() => navigate('/dryer')}
            className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold border border-slate-300 dark:border-slate-700"
          >
            {t.nav_dryer_dashboard}
          </button>
        }
      />

      {result && <Banner kind="ok">{result}</Banner>}
      {error && <Banner kind="error">{error}</Banner>}
      {unloadable.length === 0 && <Banner kind="info">{t.no_open_cycle}</Banner>}

      <Panel className="p-6">
        <form onSubmit={submit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Field label={t.chamber} required>
            <SelectInput value={chamberId} onChange={(e) => setChamberId(e.target.value)} required>
              <option value="">—</option>
              {unloadable.map((c) => (
                <option key={c.chamber_id} value={c.chamber_id}>
                  {c.chamber_code}
                </option>
              ))}
            </SelectInput>
          </Field>
          <Field label={t.finger_count}>
            <TextInput type="number" value={fingerCount} onChange={(e) => setFingerCount(e.target.value)} inputMode="numeric" />
          </Field>
          <Field label={t.unload_operator}>
            <SelectInput value={operatorId} onChange={(e) => setOperatorId(e.target.value)}>
              <option value="">—</option>
              {operators.map((o) => (
                <option key={o.operator_id} value={o.operator_id}>
                  {o.full_name || o.operator_code}
                </option>
              ))}
            </SelectInput>
          </Field>
          <Field label={t.unload_date} required>
            <JalaliDatePicker value={unloadDate} onChange={(v) => setUnloadDate(v ?? '')} placeholder="YYYY.MM.DD" />
          </Field>
          <Field label={t.unload_time}>
            <TextInput type="time" value={unloadTime} onChange={(e) => setUnloadTime(e.target.value)} />
          </Field>
          <div className="md:col-span-3 pt-1">
            <SubmitButton busy={busy} color="amber">
              {t.submit_unload}
            </SubmitButton>
          </div>
        </form>
      </Panel>

      <Panel className="p-5">
        <PanelTitle icon={History} title={t.recent_unloads} />
        <div className="overflow-x-auto">
          <table className={tableCls}>
            <thead>
              <tr>
                <th className={thCls}>#</th>
                <th className={thCls}>{t.chamber}</th>
                <th className={thCls}>{t.product_select}</th>
                <th className={thCls}>{t.load_date}</th>
                <th className={thCls}>{t.unload_date}</th>
                <th className={thCls}>{t.finger_count}</th>
                <th className={thCls}>{t.actions}</th>
              </tr>
            </thead>
            <tbody>
              {unloaded.slice(0, 15).map((c, i) => (
                <tr key={c.dryer_cycle_id} className={trCls}>
                  <td className="p-2.5 text-slate-400 tabular-nums">{i + 1}</td>
                  <td className="p-2.5 font-bold text-slate-900 dark:text-white">{c.chamber_code}</td>
                  <td className="p-2.5 text-amber-600 dark:text-amber-400 font-semibold">{c.product_name || '—'}</td>
                  <td className="p-2.5 text-slate-600 dark:text-slate-300 tabular-nums">
                    {formatJalali(c.load_date)} {c.load_time ?? ''}
                  </td>
                  <td className="p-2.5 text-emerald-600 dark:text-emerald-400 tabular-nums">
                    {formatJalali(c.unload_date)} {c.unload_time ?? ''}
                  </td>
                  <td className="p-2.5 text-slate-600 dark:text-slate-300 tabular-nums">{c.finger_count ?? '—'}</td>
                  <td className="p-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  </td>
                </tr>
              ))}
              {unloaded.length === 0 && (
                <tr>
                  <td colSpan={7} className="p-4 text-center text-slate-400">{t.no_data}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}