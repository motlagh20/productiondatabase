/**
 * Setting entry (`/setting`) — chamber-centric batch: one loaded DRYER chamber
 * discharges into 1..4 wagons. Product is event-level; per-wagon we capture
 * glaze, start/end time, packages, khesht. Sends `chamber_id` (the serializer key).
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layers, Plus, RotateCcw, Trash2, UserCheck } from 'lucide-react'

import {
  apiErrorMessage,
  fetchChambers,
  fetchGlazes,
  fetchOperators,
  fetchProducts,
  fetchWagons,
  postSettingEvent,
  type Chamber,
  type Glaze,
  type Operator,
  type Product,
  type Wagon,
} from '../api'
import { useUI } from '../context/UIContext'
import { Banner, Field, PageHeader, Panel, SelectInput, SubmitButton, TextInput } from '../components/ui'
import JalaliDatePicker from '../components/JalaliDatePicker'
import { SHIFTS, todayJalali } from '../jalali'

interface WagonRow {
  key: number
  wagonId: string
  glazeId: string
  startTime: string
  endTime: string
  packages: string
  khesht: string
}

let rowKey = 0
function emptyRow(): WagonRow {
  return { key: rowKey++, wagonId: '', glazeId: '', startTime: '', endTime: '', packages: '', khesht: '' }
}

export default function SettingEntryForm() {
  const { t } = useUI()
  const navigate = useNavigate()

  const [wagons, setWagons] = useState<Wagon[]>([])
  const [chambers, setChambers] = useState<Chamber[]>([])
  const [operators, setOperators] = useState<Operator[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [glazes, setGlazes] = useState<Glaze[]>([])

  const loadedDryerChambers = chambers.filter((c) => c.chamber_type === 'DRYER')

  const [chamberId, setChamberId] = useState('')
  const [productId, setProductId] = useState('')
  const [supervisorId, setSupervisorId] = useState('')
  const [operatorId, setOperatorId] = useState('')
  const [shift, setShift] = useState('')
  const [dateJalali, setDateJalali] = useState(todayJalali())
  const [personnelCount, setPersonnelCount] = useState('')
  const [fingersCount, setFingersCount] = useState('')
  const [columnsCount, setColumnsCount] = useState('')
  const [dryerWaste, setDryerWaste] = useState('')
  const [rows, setRows] = useState<WagonRow[]>([emptyRow()])

  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchWagons(true), fetchChambers(true), fetchOperators(), fetchProducts(), fetchGlazes()])
      .then(([w, c, o, p, g]) => {
        setWagons(w)
        setChambers(c)
        setOperators(o)
        setProducts(p)
        setGlazes(g)
      })
      .catch((e) => setError(apiErrorMessage(e)))
  }, [])

  const shiftLabel = (value: number) => (value === 1 ? t.shift_morning : value === 2 ? t.shift_evening : t.shift_night)

  function updateRow(key: number, patch: Partial<WagonRow>) {
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)))
  }
  function addRow() {
    setRows((rs) => (rs.length < 4 ? [...rs, emptyRow()] : rs))
  }
  function removeRow(key: number) {
    setRows((rs) => (rs.length > 1 ? rs.filter((r) => r.key !== key) : rs))
  }
  function reset() {
    setChamberId('')
    setProductId('')
    setSupervisorId('')
    setOperatorId('')
    setShift('')
    setPersonnelCount('')
    setFingersCount('')
    setColumnsCount('')
    setDryerWaste('')
    setRows([emptyRow()])
    setResult(null)
    setError(null)
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const wagonPayload = rows
        .filter((r) => r.wagonId)
        .map((r) => ({
          wagon_id: Number(r.wagonId),
          glaze_id: r.glazeId ? Number(r.glazeId) : undefined,
          start_time: r.startTime || undefined,
          end_time: r.endTime || undefined,
          packages: r.packages ? Number(r.packages) : undefined,
          khesht_count: r.khesht ? Number(r.khesht) : undefined,
        }))
      if (wagonPayload.length === 0) throw new Error(t.error_msg)
      const data = await postSettingEvent({
        chamber_id: Number(chamberId),
        product_id: productId ? Number(productId) : undefined,
        supervisor_id: supervisorId ? Number(supervisorId) : undefined,
        operator_id: operatorId ? Number(operatorId) : undefined,
        shift: shift ? Number(shift) : undefined,
        date_jalali: dateJalali,
        personnel_count: personnelCount ? Number(personnelCount) : undefined,
        fingers_count: fingersCount ? Number(fingersCount) : undefined,
        columns_count: columnsCount ? Number(columnsCount) : undefined,
        dryer_waste: dryerWaste ? Number(dryerWaste) : undefined,
        wagons: wagonPayload,
      })
      const tripCount = (data.trip_ids || []).length
      setResult(`${t.success_msg} — ${t.setting_event_id}: #${data.setting_event_id} (${tripCount} ${t.wagons_count})`)
      setRows([emptyRow()])
      navigate('/setting/log', { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon={Layers}
        title={t.setting_title}
        subtitle={t.app_title}
        color="amber"
        actions={
          <button
            type="button"
            onClick={reset}
            className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold flex items-center gap-1.5 border border-slate-300 dark:border-slate-700"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            {t.reset_form}
          </button>
        }
      />

      {result && <Banner kind="ok">{result}</Banner>}
      {error && <Banner kind="error">{error}</Banner>}
      {loadedDryerChambers.length === 0 && <Banner kind="info">{t.no_data}</Banner>}

      <form onSubmit={submit} className="flex flex-col gap-5 space-y-0">
        {/* Master parameters */}
        <Panel className="p-6">
          <div className="pb-3 border-b border-slate-200 dark:border-slate-800 mb-4 flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-amber-500 dark:text-amber-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-white">{t.setting_title}</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <Field label={t.setting_date} required>
              <JalaliDatePicker value={dateJalali} onChange={(v) => setDateJalali(v ?? '')} placeholder="YYYY.MM.DD" />
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
            <Field label={t.chamber} required>
              <SelectInput value={chamberId} onChange={(e) => setChamberId(e.target.value)} required>
                <option value="">—</option>
                {loadedDryerChambers.map((c) => (
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
                    {p.product_name_setting || `#${p.product_id}`}
                  </option>
                ))}
              </SelectInput>
            </Field>
            <Field label={t.supervisor}>
              <SelectInput value={supervisorId} onChange={(e) => setSupervisorId(e.target.value)}>
                <option value="">—</option>
                {operators.map((o) => (
                  <option key={o.operator_id} value={o.operator_id}>
                    {o.full_name || o.operator_code}
                  </option>
                ))}
              </SelectInput>
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
            <Field label={t.personnel_count}>
              <TextInput type="number" value={personnelCount} onChange={(e) => setPersonnelCount(e.target.value)} inputMode="numeric" />
            </Field>
            <Field label={t.fingers_count}>
              <TextInput type="number" value={fingersCount} onChange={(e) => setFingersCount(e.target.value)} inputMode="numeric" />
            </Field>
            <Field label={t.columns_count}>
              <TextInput type="number" value={columnsCount} onChange={(e) => setColumnsCount(e.target.value)} inputMode="numeric" />
            </Field>
            <Field label={t.dryer_waste}>
              <TextInput type="number" value={dryerWaste} onChange={(e) => setDryerWaste(e.target.value)} inputMode="numeric" />
            </Field>
          </div>
        </Panel>

        {/* Wagons */}
        <Panel className="p-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800 mb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                {t.wagons_count}: {rows.length}
              </h2>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{t.wagon_limit_hint}</p>
            </div>
            {rows.length < 4 && (
              <button
                type="button"
                onClick={addRow}
                className="px-3 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold flex items-center gap-1.5"
              >
                <Plus className="w-4 h-4" />
                {t.add_wagon}
              </button>
            )}
          </div>

          <div className="flex flex-col gap-4">
            {rows.map((r, idx) => (
              <div key={r.key} className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="px-2.5 py-0.5 rounded-lg bg-amber-500/20 text-amber-700 dark:text-amber-400 text-xs font-bold border border-amber-500/30">
                    #{idx + 1}
                  </span>
                  {rows.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeRow(r.key)}
                      className="text-slate-400 hover:text-rose-500 p-1 transition-colors"
                      title={t.remove_wagon}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                  <Field label={t.wagon_no} required>
                    <SelectInput value={r.wagonId} onChange={(e) => updateRow(r.key, { wagonId: e.target.value })} required>
                      <option value="">—</option>
                      {wagons.map((w) => (
                        <option key={w.wagon_id} value={w.wagon_id}>
                          {w.wagon_name}
                        </option>
                      ))}
                    </SelectInput>
                  </Field>
                  <Field label={t.glaze_override}>
                    <SelectInput value={r.glazeId} onChange={(e) => updateRow(r.key, { glazeId: e.target.value })}>
                      <option value="">—</option>
                      {glazes.map((g) => (
                        <option key={g.glaze_id} value={g.glaze_id}>
                          {g.glaze_name || g.glaze_code}
                        </option>
                      ))}
                    </SelectInput>
                  </Field>
                  <Field label={t.start_time}>
                    <TextInput type="time" value={r.startTime} onChange={(e) => updateRow(r.key, { startTime: e.target.value })} />
                  </Field>
                  <Field label={t.end_time}>
                    <TextInput type="time" value={r.endTime} onChange={(e) => updateRow(r.key, { endTime: e.target.value })} />
                  </Field>
                  <Field label={t.packages_count}>
                    <TextInput type="number" value={r.packages} onChange={(e) => updateRow(r.key, { packages: e.target.value })} inputMode="numeric" />
                  </Field>
                  <Field label={t.khesht_count}>
                    <TextInput type="number" value={r.khesht} onChange={(e) => updateRow(r.key, { khesht: e.target.value })} inputMode="numeric" />
                  </Field>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <div className="md:col-span-4 pt-1">
          <SubmitButton busy={busy} color="amber">
            {t.submit_setting}
          </SubmitButton>
        </div>
      </form>
    </div>
  )
}