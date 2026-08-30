/** F5: register a packing session over 1+ awaiting-discharge trips → each trip completed. */
import { useEffect, useState } from 'react'
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
import { Banner, Card, Field, Select, SubmitButton } from '../components/Form'
import JalaliDatePicker from '../components/JalaliDatePicker'
import { toJalali } from '../jalali'

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
  const [awaiting, setAwaiting] = useState<AwaitingTrip[]>([])
  const [operators, setOperators] = useState<Operator[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [controllerId, setControllerId] = useState('')
  const [packDate, setPackDate] = useState(toJalali(new Date()))
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

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    const rows = Object.values(selected)
    if (rows.length === 0) {
      setError('حداقل یک واگن از لیست تخلیه انتخاب کنید.')
      return
    }
    setBusy(true)
    try {
      const payload = {
        pack_date: packDate,
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
      setResult(`بسته‌بندی ثبت شد (شناسه ${data.packing_header_id}). ${rows.length} سفر تکمیل شد.`)
      setSelected({})
      reload()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const numClass =
    'w-24 rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100'

  return (
    <Card title="بسته‌بندی" subtitle="یک یا چند واگن از لیست تخلیه را انتخاب و درجه‌بندی کنید — سفر بسته می‌شود.">
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field label="کنترلر">
          <Select
            value={controllerId}
            onChange={setControllerId}
            options={operators.map((o) => ({ value: o.operator_id, label: o.full_name || o.operator_code }))}
          />
        </Field>
        <Field label="تاریخ بسته‌بندی">
          <JalaliDatePicker value={packDate} onChange={(v) => setPackDate(v ?? '')} placeholder="انتخاب تاریخ" />
        </Field>

        {awaiting.length === 0 ? (
          <Banner kind="error">لیست تخلیه خالی است. ابتدا یک واگن باید از کوره عبور کرده باشد (خروج اتوماتیک محاسبه می‌شود).</Banner>
        ) : (
          <div className="flex flex-col gap-2">
            <span className="text-sm font-medium text-slate-700">واگن‌های در انتظار تخلیه</span>
            <div className="flex flex-col gap-2">
              {awaiting.map((t) => {
                const row = selected[t.trip_id]
                return (
                  <div key={t.trip_id} className="rounded-lg border border-slate-200 p-3">
                    <label className="flex items-center gap-2">
                      <input type="checkbox" checked={!!row} onChange={() => toggle(t)} />
                      <span className="text-sm font-medium">
                        سفر {t.trip_id} — پلاک {t.plate}
                      </span>
                    </label>
                    {row && (
                      <div className="mt-3 flex flex-wrap gap-3 ps-6">
                        <Select
                          value={row.product_id}
                          onChange={(v) => patch(t.trip_id, 'product_id', v)}
                          options={products.map((p) => ({
                            value: p.product_id,
                            label: p.product_name_setting || String(p.product_id),
                          }))}
                          placeholder="محصول"
                        />
                        <input className={numClass} placeholder="کل" inputMode="numeric"
                          value={row.total_count} onChange={(e) => patch(t.trip_id, 'total_count', e.target.value)} />
                        <input className={numClass} placeholder="درجه ۱" inputMode="numeric"
                          value={row.grade1_count} onChange={(e) => patch(t.trip_id, 'grade1_count', e.target.value)} />
                        <input className={numClass} placeholder="درجه ۲" inputMode="numeric"
                          value={row.grade2_count} onChange={(e) => patch(t.trip_id, 'grade2_count', e.target.value)} />
                        <input className={numClass} placeholder="ضایعات" inputMode="numeric"
                          value={row.waste_count} onChange={(e) => patch(t.trip_id, 'waste_count', e.target.value)} />
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        <SubmitButton busy={busy}>ثبت بسته‌بندی</SubmitButton>
        {result && <Banner kind="ok">{result}</Banner>}
        {error && <Banner kind="error">{error}</Banner>}
      </form>
    </Card>
  )
}
