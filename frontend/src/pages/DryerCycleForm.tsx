/** F1 — ثبت چرخه خشک‌کن (اولین گام تولید؛ بدنهٔ خشک‌شده توسط ستینگ بارگیری می‌شود). */
import { useEffect, useState } from 'react'
import {
  apiErrorMessage,
  fetchChambers,
  fetchOperators,
  fetchProducts,
  postDryerCycle,
  type Chamber,
  type Operator,
  type Product,
} from '../api'
import { Banner, Card, Field, Input, Select, SubmitButton } from '../components/Form'
import JalaliDatePicker from '../components/JalaliDatePicker'
import { todayJalali } from '../jalali'

interface ReadingRow {
  hour: string
  humidity: string
  temp: string
}

export default function DryerCycleForm() {
  const [chambers, setChambers] = useState<Chamber[]>([])
  const [operators, setOperators] = useState<Operator[]>([])
  const [products, setProducts] = useState<Product[]>([])

  const [chamberId, setChamberId] = useState('')
  const [loadDate, setLoadDate] = useState(todayJalali())
  const [loadTime, setLoadTime] = useState('')
  const [unloadDate, setUnloadDate] = useState('')
  const [unloadTime, setUnloadTime] = useState('')
  const [loadOperator, setLoadOperator] = useState('')
  const [unloadOperator, setUnloadOperator] = useState('')
  const [productId, setProductId] = useState('')
  const [fingerCount, setFingerCount] = useState('')
  const [readings, setReadings] = useState<ReadingRow[]>([{ hour: '0', humidity: '', temp: '' }])

  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchChambers(), fetchOperators(), fetchProducts()])
      .then(([c, o, p]) => { setChambers(c); setOperators(o); setProducts(p) })
      .catch((e) => setError(apiErrorMessage(e)))
  }, [])

  function updateReading(i: number, patch: Partial<ReadingRow>) {
    setReadings((rs) => rs.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))
  }
  function addReading() {
    setReadings((rs) => [...rs, { hour: String(rs.length), humidity: '', temp: '' }])
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const readingPayload = readings
        .filter((r) => r.humidity || r.temp)
        .map((r) => ({
          hour_offset: Number(r.hour),
          humidity_pct: r.humidity ? Number(r.humidity) : null,
          temperature_c: r.temp ? Number(r.temp) : null,
        }))
      const data = await postDryerCycle({
        chamber_id: Number(chamberId),
        load_date: loadDate,
        load_time: loadTime || undefined,
        unload_date: unloadDate || undefined,
        unload_time: unloadTime || undefined,
        load_operator_id: loadOperator ? Number(loadOperator) : undefined,
        unload_operator_id: unloadOperator ? Number(unloadOperator) : undefined,
        product_id: productId ? Number(productId) : undefined,
        finger_count: fingerCount ? Number(fingerCount) : undefined,
        readings: readingPayload,
      })
      setResult(`چرخه خشک‌کن ${data.dryer_cycle_id} ثبت شد (${data.readings} ردیف قرائت).`)
      setReadings([{ hour: '0', humidity: '', temp: '' }])
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card
      title="خشک‌کن — ثبت چرخه (F1)"
      subtitle="اولین گام تولید: بارگیری و تخلیهٔ چمبر، همراه با قرائت‌های ساعتی رطوبت/دما."
    >
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Field label="چمبر (۱ تا ۴۰)">
          <Select
            value={chamberId}
            onChange={setChamberId}
            options={chambers.map((c) => ({ value: String(c.chamber_id), label: c.chamber_code }))}
          />
        </Field>
        <Field label="محصول">
          <Select
            value={productId}
            onChange={setProductId}
            options={products.map((p) => ({ value: String(p.product_id), label: p.product_name_setting || `#${p.product_id}` }))}
          />
        </Field>
        <Field label="تاریخ بارگیری">
          <JalaliDatePicker value={loadDate} onChange={setLoadDate} placeholder="انتخاب تاریخ بارگیری" />
        </Field>
        <Field label="ساعت بارگیری">
          <Input type="time" value={loadTime} onChange={setLoadTime} />
        </Field>
        <Field label="تاریخ تخلیه">
          <JalaliDatePicker value={unloadDate} onChange={setUnloadDate} placeholder="انتخاب تاریخ تخلیه" />
        </Field>
        <Field label="ساعت تخلیه">
          <Input type="time" value={unloadTime} onChange={setUnloadTime} />
        </Field>
        <Field label="اپراتور بارگیری">
          <Select
            value={loadOperator}
            onChange={setLoadOperator}
            options={operators.map((o) => ({ value: String(o.operator_id), label: o.full_name || o.operator_code }))}
          />
        </Field>
        <Field label="اپراتور تخلیه">
          <Select
            value={unloadOperator}
            onChange={setUnloadOperator}
            options={operators.map((o) => ({ value: String(o.operator_id), label: o.full_name || o.operator_code }))}
          />
        </Field>
        <Field label="تعداد فینگر">
          <Input type="number" value={fingerCount} onChange={setFingerCount} />
        </Field>

        <div className="sm:col-span-2">
          <div className="mb-2 font-medium text-sm">قرائت‌های ساعتی (رطوبت / دما)</div>
          <div className="flex flex-col gap-2">
            {readings.map((r, i) => (
              <div key={i} className="grid grid-cols-4 gap-2 items-end">
                <Field label="ساعت">
                  <Input value={r.hour} onChange={(v) => updateReading(i, { hour: v })} />
                </Field>
                <Field label="رطوبت٪">
                  <Input type="number" step="0.1" value={r.humidity} onChange={(v) => updateReading(i, { humidity: v })} />
                </Field>
                <Field label="دما°C">
                  <Input type="number" step="0.1" value={r.temp} onChange={(v) => updateReading(i, { temp: v })} />
                </Field>
                {i === readings.length - 1 && (
                  <button type="button" onClick={addReading} className="text-sm text-accent underline mb-2">
                    + ساعت بعد
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="sm:col-span-2 flex flex-col gap-3">
          <SubmitButton busy={busy}>ثبت چرخه خشک‌کن</SubmitButton>
          {result && <Banner kind="ok">{result}</Banner>}
          {error && <Banner kind="error">{error}</Banner>}
        </div>
      </form>
    </Card>
  )
}
