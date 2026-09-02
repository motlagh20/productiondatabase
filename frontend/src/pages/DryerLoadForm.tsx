/**
 * Dryer chamber load (`/dryer/load`) — F1 first step: register a load on an
 * EMPTY chamber. Only load-side fields are sent; readings and unload come later
 * through their own views. Preselects the chamber when arrived from the
 * dashboard via router state.
 */
import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ArrowDownToLine, History } from 'lucide-react'

import {
  apiErrorMessage,
  fetchDryerChamberStatus,
  fetchDryerCycles,
  fetchOperators,
  fetchProducts,
  postDryerCycle,
  type DryerChamberStatus,
  type DryerCycleData,
  type Operator,
  type Product,
} from '../api'
import { useUI } from '../context/UIContext'
import { Banner, Field, PageHeader, Panel, PanelTitle, SelectInput, SubmitButton, TextInput, tableCls, thCls, trCls } from '../components/ui'
import JalaliDatePicker from '../components/JalaliDatePicker'
import { todayJalali } from '../jalali'

function nowTime(): string {
  return new Date().toTimeString().slice(0, 5)
}

export default function DryerLoadForm() {
  const { t } = useUI()
  const navigate = useNavigate()
  const location = useLocation() as { state: { chamberId?: number } | null }

  const [chambers, setChambers] = useState<DryerChamberStatus[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [operators, setOperators] = useState<Operator[]>([])
  const [history, setHistory] = useState<DryerCycleData[]>([])

  const emptyChambers = useMemo(() => chambers.filter((c) => c.derived_status === 'empty'), [chambers])

  const [chamberId, setChamberId] = useState('')
  const [productId, setProductId] = useState('')
  const [fingerCount, setFingerCount] = useState('')
  const [operatorId, setOperatorId] = useState('')
  const [loadDate, setLoadDate] = useState(todayJalali())
  const [loadTime, setLoadTime] = useState(nowTime())

  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = () => {
    fetchDryerChamberStatus().then(setChambers).catch(() => {})
    fetchDryerCycles().then(setHistory).catch(() => {})
  }

  useEffect(() => {
    Promise.all([fetchProducts(), fetchOperators()])
      .then(([p, o]) => {
        setProducts(p)
        setOperators(o)
      })
      .catch((e) => setError(apiErrorMessage(e)))
    reload()
  }, [])

  // Dashboard preselection
  useEffect(() => {
    if (location.state?.chamberId) setChamberId(String(location.state.chamberId))
  }, [location.state])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const data = await postDryerCycle({
        chamber_id: Number(chamberId),
        product_id: productId ? Number(productId) : undefined,
        finger_count: fingerCount ? Number(fingerCount) : undefined,
        load_operator_id: operatorId ? Number(operatorId) : undefined,
        load_date: loadDate,
        load_time: loadTime || undefined,
      })
      setResult(`${t.submit_load} ✓ (cycle #${data.dryer_cycle_id})`)
      setFingerCount('')
      reload()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon={ArrowDownToLine}
        title={t.dryer_load_title}
        color="sky"
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

      {emptyChambers.length === 0 && <Banner kind="info">{t.no_empty_chamber}</Banner>}

      <Panel className="p-6">
        <form onSubmit={submit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Field label={t.chamber} required>
            <SelectInput value={chamberId} onChange={(e) => setChamberId(e.target.value)} required>
              <option value="">—</option>
              {emptyChambers.map((c) => (
                <option key={c.chamber_id} value={c.chamber_id}>
                  {c.chamber_code}
                </option>
              ))}
            </SelectInput>
          </Field>
          <Field label={t.product_select}>
            <SelectInput value={productId} onChange={(e) => setProductId(e.target.value)}>
              <option value="">—</option>
              {products.map((p) => (
                <option key={p.product_id} value={p.product_id}>
                  {p.product_name_setting}
                </option>
              ))}
            </SelectInput>
          </Field>
          <Field label={t.finger_count}>
            <TextInput type="number" value={fingerCount} onChange={(e) => setFingerCount(e.target.value)} inputMode="numeric" />
          </Field>
          <Field label={t.load_operator}>
            <SelectInput value={operatorId} onChange={(e) => setOperatorId(e.target.value)}>
              <option value="">—</option>
              {operators.map((o) => (
                <option key={o.operator_id} value={o.operator_id}>
                  {o.full_name || o.operator_code}
                </option>
              ))}
            </SelectInput>
          </Field>
          <Field label={t.load_date} required>
            <JalaliDatePicker value={loadDate} onChange={(v) => setLoadDate(v ?? '')} placeholder="YYYY.MM.DD" />
          </Field>
          <Field label={t.load_time}>
            <TextInput type="time" value={loadTime} onChange={(e) => setLoadTime(e.target.value)} />
          </Field>
          <div className="md:col-span-3 pt-1">
            <SubmitButton busy={busy} color="sky">
              {t.submit_load}
            </SubmitButton>
          </div>
        </form>
      </Panel>

      <Panel className="p-5">
        <PanelTitle icon={History} title={t.recent_loads} />
        <div className="overflow-x-auto">
          <table className={tableCls}>
            <thead>
              <tr>
                <th className={thCls}>#</th>
                <th className={thCls}>{t.chamber}</th>
                <th className={thCls}>{t.product_select}</th>
                <th className={thCls}>{t.load_date}</th>
                <th className={thCls}>{t.finger_count}</th>
                <th className={thCls}>{t.readings_count}</th>
                <th className={thCls}>{t.actions}</th>
              </tr>
            </thead>
            <tbody>
              {history.slice(0, 15).map((c, i) => (
                <tr key={c.dryer_cycle_id} className={trCls}>
                  <td className="p-2.5 text-slate-400 tabular-nums">{i + 1}</td>
                  <td className="p-2.5 font-bold text-slate-900 dark:text-white">{c.chamber_code}</td>
                  <td className="p-2.5 text-amber-600 dark:text-amber-400 font-semibold">{c.product_name || '—'}</td>
                  <td className="p-2.5 text-slate-600 dark:text-slate-300 tabular-nums">
                    {c.load_date} {c.load_time ?? ''}
                  </td>
                  <td className="p-2.5 text-slate-600 dark:text-slate-300 tabular-nums">{c.finger_count ?? '—'}</td>
                  <td className="p-2.5 text-slate-600 dark:text-slate-300 tabular-nums">{c.readings.length}</td>
                  <td className="p-2.5">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        c.unload_date
                          ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
                          : 'bg-sky-500/15 text-sky-700 dark:text-sky-400 border-sky-500/30'
                      }`}
                    >
                      {c.unload_date ? t.chamber_status_dried : t.chamber_status_drying}
                    </span>
                  </td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr>
                  <td colSpan={7} className="p-4 text-center text-slate-400">
                    {t.no_data}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}
