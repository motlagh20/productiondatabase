/** F5: register a packing session over 1+ awaiting-discharge trips → each trip completed. */
import { useEffect, useState } from 'react'
import { Package } from 'lucide-react'

import {
  apiErrorMessage,
  fetchAwaitingDischarge,
  fetchOperators,
  fetchProducts,
  postPacking,
  type AwaitingTrip,
  type Operator,
  type Product,
} from '../api'
import { useUI } from '../context/UIContext'
import { Banner, Field, PageHeader, Panel, SelectInput, SubmitButton, TextInput } from '../components/ui'
import JalaliDatePicker from '../components/JalaliDatePicker'
import { SHIFTS, todayJalali } from '../jalali'

interface WagonRow {
  trip_id: number
  plate: string
  product_id: string
  total_count: string
  grade1_count: string
  grade2_count: string
  waste_count: string
}

export default function PackingForm() {
  const { t } = useUI()
  const [awaiting, setAwaiting] = useState<AwaitingTrip[]>([])
  const [operators, setOperators] = useState<Operator[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [controllerId, setControllerId] = useState('')
  const [shift, setShift] = useState('')
  const [workerCount, setWorkerCount] = useState('')
  const [packDate, setPackDate] = useState(todayJalali())
  const [selected, setSelected] = useState<Record<number, WagonRow>>({})
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  function reload() {
    fetchAwaitingDischarge().then(setAwaiting).catch(() => setAwaiting([]))
  }

  useEffect(() => {
    reload()
    fetchOperators().then(setOperators).catch(() => {})
    fetchProducts().then(setProducts).catch(() => {})
  }, [])

  function toggle(t: AwaitingTrip) {
    setSelected((prev) => {
      const next = { ...prev }
      if (next[t.trip_id]) {
        delete next[t.trip_id]
      } else {
        next[t.trip_id] = {
          trip_id: t.trip_id,
          plate: t.plate,
          product_id: '',
          total_count: '',
          grade1_count: '',
          grade2_count: '',
          waste_count: '',
        }
      }
      return next
    })
  }

  function patch(tripId: number, field: keyof WagonRow, value: string) {
    setSelected((prev) => ({ ...prev, [tripId]: { ...prev[tripId], [field]: value } }))
  }

  const shiftLabel = (v: number) => (v === 1 ? t.shift_morning : v === 2 ? t.shift_evening : t.shift_night)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    const rows = Object.values(selected)
    if (rows.length === 0) {
      setError(t.error_msg)
      return
    }
    setBusy(true)
    try {
      const payload = {
        pack_date: packDate,
        shift: shift ? Number(shift) : null,
        worker_count: workerCount ? Number(workerCount) : null,
        controller_id: controllerId ? Number(controllerId) : null,
        wagons: rows.map((r) => ({
          trip_id: r.trip_id,
          product_id: r.product_id ? Number(r.product_id) : null,
          total_count: r.total_count ? Number(r.total_count) : null,
          grade1_count: r.grade1_count ? Number(r.grade1_count) : null,
          grade2_count: r.grade2_count ? Number(r.grade2_count) : null,
          waste_count: r.waste_count ? Number(r.waste_count) : null,
        })),
      }
      const data = await postPacking(payload)
      setResult(`${t.success_msg} (${t.pack_title}) → #${data.packing_header_id}`)
      setSelected({})
      reload()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader icon={Package} title={t.pack_title} subtitle={t.app_title} color="emerald" />

      {result && <Banner kind="ok">{result}</Banner>}
      {error && <Banner kind="error">{error}</Banner>}

      <Panel className="p-6">
        <form onSubmit={submit} className="flex flex-col gap-5">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label={t.pack_date} required>
              <JalaliDatePicker value={packDate} onChange={(v) => setPackDate(v ?? '')} placeholder="YYYY.MM.DD" />
            </Field>
            <Field label={t.controller}>
              <SelectInput value={controllerId} onChange={(e) => setControllerId(e.target.value)}>
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
            <Field label={t.worker_count}>
              <TextInput type="number" value={workerCount} onChange={(e) => setWorkerCount(e.target.value)} inputMode="numeric" />
            </Field>
          </div>

          {awaiting.length === 0 ? (
            <Banner kind="info">{t.no_awaiting_wagon}</Banner>
          ) : (
            <div className="flex flex-col gap-2">
              <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">{t.awaiting_discharge}</span>
              <div className="flex flex-col gap-2">
                {awaiting.map((w) => {
                  const row = selected[w.trip_id]
                  return (
                    <div key={w.trip_id} className="rounded-xl border border-slate-200 dark:border-slate-700 p-3">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" checked={!!row} onChange={() => toggle(w)} className="accent-emerald-600" />
                        <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                          {t.trip_id} {w.trip_id} — {t.wagon_no} {w.plate}
                        </span>
                      </label>
                      {row && (
                        <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 ps-6">
                          <Field label={t.product_select}>
                            <SelectInput value={row.product_id} onChange={(e) => patch(w.trip_id, 'product_id', e.target.value)}>
                              <option value="">—</option>
                              {products.map((p) => (
                                <option key={p.product_id} value={p.product_id}>
                                  {p.product_name_setting || `#${p.product_id}`}
                                </option>
                              ))}
                            </SelectInput>
                          </Field>
                          <Field label={t.total_count}>
                            <TextInput type="number" value={row.total_count} onChange={(e) => patch(w.trip_id, 'total_count', e.target.value)} inputMode="numeric" />
                          </Field>
                          <Field label={t.grade1}>
                            <TextInput type="number" value={row.grade1_count} onChange={(e) => patch(w.trip_id, 'grade1_count', e.target.value)} inputMode="numeric" />
                          </Field>
                          <Field label={t.grade2}>
                            <TextInput type="number" value={row.grade2_count} onChange={(e) => patch(w.trip_id, 'grade2_count', e.target.value)} inputMode="numeric" />
                          </Field>
                          <Field label={t.rejects}>
                            <TextInput type="number" value={row.waste_count} onChange={(e) => patch(w.trip_id, 'waste_count', e.target.value)} inputMode="numeric" />
                          </Field>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <SubmitButton busy={busy} color="emerald">
            {t.submit_pack}
          </SubmitButton>
        </form>
      </Panel>
    </div>
  )
}