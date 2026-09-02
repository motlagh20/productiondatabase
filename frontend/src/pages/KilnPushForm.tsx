/** F3 — ثبت هل دادن به کوره (واگن وارد تونل می‌شود؛ ظرفیت ثابت ۴۴ در سمت سرور اعمال می‌شود). */
import { useEffect, useState } from 'react'
import { Activity, Clock, Flame, History } from 'lucide-react'

import {
  apiErrorMessage,
  fetchActiveWagons,
  fetchKilnPushes,
  fetchOperators,
  fetchSensors,
  postKilnPush,
  type ActiveWagon,
  type KilnPushData,
  type Operator,
  type Sensor,
} from '../api'
import { useUI } from '../context/UIContext'
import { Banner, Field, PageHeader, Panel, PanelTitle, SelectInput, SubmitButton, TextInput, tableCls, thCls, trCls } from '../components/ui'
import JalaliDatePicker from '../components/JalaliDatePicker'
import { SHIFTS, todayJalali } from '../jalali'

export default function KilnPushForm() {
  const { t } = useUI()
  const [operators, setOperators] = useState<Operator[]>([])
  const [sensors, setSensors] = useState<Sensor[]>([])
  const [active, setActive] = useState<ActiveWagon[]>([])
  const [history, setHistory] = useState<KilnPushData[]>([])
  const [temps, setTemps] = useState<Record<string, string>>({})

  const [wagonId, setWagonId] = useState('')
  const [operatorId, setOperatorId] = useState('')
  const [shift, setShift] = useState('')
  const [pushDate, setPushDate] = useState(todayJalali())
  const [pushTime, setPushTime] = useState('')

  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reloadHistory = () => {
    fetchKilnPushes()
      .then(setHistory)
      .catch(() => {})
  }

  useEffect(() => {
    Promise.all([fetchOperators(), fetchSensors(), fetchActiveWagons()])
      .then(([o, s, a]) => {
        setOperators(o)
        setSensors(s)
        setActive(a)
      })
      .catch((e) => setError(apiErrorMessage(e)))
    reloadHistory()
  }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const readings = sensors
        .filter((s) => temps[s.sensor_code])
        .map((s) => ({ sensor_code: s.sensor_code, temperature_c: temps[s.sensor_code] }))
      const data = await postKilnPush({
        wagon_id: Number(wagonId),
        push_date: pushDate,
        operator_id: operatorId ? Number(operatorId) : undefined,
        shift: shift ? Number(shift) : undefined,
        push_time: pushTime || undefined,
        readings,
      })
      setResult(`${t.submit_push} ✓ (${t.push_seq} ${data.push_seq})`)
      setWagonId('')
      setTemps({})
      reloadHistory()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const shiftLabel = (v: number) => (v === 1 ? t.shift_morning : v === 2 ? t.shift_evening : t.shift_night)

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon={Flame}
        title={t.kiln_title}
        subtitle={t.app_title}
        color="rose"
        actions={
          <div className="flex items-center gap-3 bg-rose-500/10 px-4 py-2 rounded-xl border border-rose-500/20">
            <Clock className="w-4 h-4 text-rose-500 dark:text-rose-400" />
            <span className="text-xs text-slate-600 dark:text-slate-300">{t.push_time}:</span>
            <span className="text-sm font-black text-rose-600 dark:text-rose-400 tabular-nums">45'</span>
          </div>
        }
      />

      {result && <Banner kind="ok">{result}</Banner>}
      {error && <Banner kind="error">{error}</Banner>}
      {active.length === 0 && <Banner kind="info">{t.no_active_wagon}</Banner>}

      <form onSubmit={submit} className="flex flex-col gap-5">
        <Panel className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label={t.wagon_no} required>
              <SelectInput value={wagonId} onChange={(e) => setWagonId(e.target.value)} required>
                <option value="">—</option>
                {active.map((w) => (
                  <option key={w.wagon_id} value={w.wagon_id}>
                    {t.wagon_no} {w.plate}
                  </option>
                ))}
              </SelectInput>
            </Field>
            <Field label={t.push_date} required>
              <JalaliDatePicker value={pushDate} onChange={(v) => setPushDate(v ?? '')} placeholder="YYYY.MM.DD" />
            </Field>
            <Field label={t.push_time}>
              <TextInput type="time" value={pushTime} onChange={(e) => setPushTime(e.target.value)} />
            </Field>
            <Field label={t.operator}>
              <SelectInput value={operatorId} onChange={(e) => setOperatorId(e.target.value)}>
                <option value="">—</option>
                {operators.map((o) => (
                  <option key={o.operator_id} value={o.operator_id}>
                    {o.full_name || o.operator_code}
                  </option>
                ))}
              </SelectInput>
            </Field>
            <Field label={t.shift}>
              <SelectInput value={shift} onChange={(e) => setShift(e.target.value)}>
                <option value="">—</option>
                {SHIFTS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {shiftLabel(s.value)}
                  </option>
                ))}
              </SelectInput>
            </Field>
          </div>
        </Panel>

        <Panel className="p-6">
          <div className="pb-3 border-b border-slate-200 dark:border-slate-800 mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-rose-500 dark:text-rose-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-white">{t.burner_zones}</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {sensors.map((s) => (
              <div key={s.sensor_id}>
                <label className="block text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1 truncate">
                  {s.sensor_name || s.sensor_code}
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={temps[s.sensor_code] ?? ''}
                  onChange={(e) => setTemps({ ...temps, [s.sensor_code]: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-sm text-slate-900 dark:text-white tabular-nums focus:border-rose-400 focus:outline-none"
                  placeholder="—"
                />
              </div>
            ))}
          </div>
        </Panel>

        <div>
          <SubmitButton busy={busy} color="rose">
            {t.submit_push}
          </SubmitButton>
        </div>
      </form>

      <Panel className="p-5">
        <PanelTitle icon={History} title={t.kiln_log_title} />
        <div className="overflow-x-auto">
          <table className={tableCls}>
            <thead>
              <tr>
                <th className={thCls}>{t.push_seq}</th>
                <th className={thCls}>{t.push_date}</th>
                <th className={thCls}>{t.wagon_no}</th>
                <th className={thCls}>{t.product_select}</th>
                <th className={thCls}>{t.exit_push_seq}</th>
                <th className={thCls}>{t.actions}</th>
              </tr>
            </thead>
            <tbody>
              {history.slice(0, 15).map((p) => (
                <tr key={p.kiln_push_id} className={trCls}>
                  <td className="p-2.5 text-slate-400 tabular-nums">{p.push_seq}</td>
                  <td className="p-2.5 text-slate-600 dark:text-slate-300 tabular-nums">
                    {p.push_date} {p.push_time ?? ''}
                  </td>
                  <td className="p-2.5 font-bold text-slate-900 dark:text-white">{p.plate}</td>
                  <td className="p-2.5 text-amber-600 dark:text-amber-400 font-semibold">{p.product_name || '—'}</td>
                  <td className="p-2.5 text-slate-600 dark:text-slate-300 tabular-nums">{p.exit_push_seq ?? '—'}</td>
                  <td className="p-2.5">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        p.discharged
                          ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
                          : 'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/30'
                      }`}
                    >
                      {p.discharged ? t.discharged : t.in_tunnel}
                    </span>
                  </td>
                </tr>
              ))}
              {history.length === 0 && (
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