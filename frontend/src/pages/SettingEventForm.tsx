/** F2 — ثبت بچ ستینگ به‌صورت چمبر-محور (تخلیهٔ چمبر x → بارگیری ۱ تا ۴ واگن). */
import { useEffect, useState } from 'react'
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
import { Banner, Card, Field, Input, Select, SubmitButton } from '../components/Form'
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

export default function SettingEventForm() {
  const [wagons, setWagons] = useState<Wagon[]>([])
  const [chambers, setChambers] = useState<Chamber[]>([])
  const [operators, setOperators] = useState<Operator[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [glazes, setGlazes] = useState<Glaze[]>([])

  const [chamberCode, setChamberCode] = useState('')
  const [operatorId, setOperatorId] = useState('')
  const [productId, setProductId] = useState('')
  const [shift, setShift] = useState('')
  const [rows, setRows] = useState<WagonRow[]>([emptyRow()])

  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchWagons(), fetchChambers(), fetchOperators(), fetchProducts(), fetchGlazes()])
      .then(([w, c, o, p, g]) => {
        setWagons(w)
        setChambers(c)
        setOperators(o)
        setProducts(p)
        setGlazes(g)
      })
      .catch((e) => setError(apiErrorMessage(e)))
  }, [])

  function updateRow(key: number, patch: Partial<WagonRow>) {
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)))
  }
  function addRow() {
    setRows((rs) => (rs.length < 4 ? [...rs, emptyRow()] : rs))
  }
  function removeRow(key: number) {
    setRows((rs) => (rs.length > 1 ? rs.filter((r) => r.key !== key) : rs))
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
      if (wagonPayload.length === 0) throw new Error('حداقل یک واگن باید انتخاب شود.')
      const data = await postSettingEvent({
        chamber_code: chamberCode,
        operator_id: operatorId ? Number(operatorId) : undefined,
        product_id: productId ? Number(productId) : undefined,
        shift: shift ? Number(shift) : undefined,
        date_jalali: todayJalali(),
        wagons: wagonPayload,
      })
      const ids = (data.trip_ids || []).join(', ')
      setResult(`بچ ستینگ ${data.setting_event_id} ثبت شد — تریپ‌ها: [${ids}].`)
      setRows([emptyRow()])
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card
      title="ستینگ — ثبت بچ چمبر-محور"
      subtitle="چمبر خشک‌کن انتخاب شود؛ سپس واگن‌های تغذیه‌شده از آن چمبر (۱ تا ۴ عدد) ثبت گردند."
    >
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Field label="چمبر خشک‌کن (مبدأ تخلیه)">
          <Select
            value={chamberCode}
            onChange={setChamberCode}
            options={chambers.map((c) => ({ value: c.chamber_code, label: c.chamber_code }))}
          />
        </Field>
        <Field label="اپراتور">
          <Select
            value={operatorId}
            onChange={setOperatorId}
            options={operators.map((o) => ({ value: o.operator_id, label: o.full_name || o.operator_code }))}
          />
        </Field>
        <Field label="محصول">
          <Select
            value={productId}
            onChange={setProductId}
            options={products.map((p) => ({ value: p.product_id, label: p.product_name_setting || `#${p.product_id}` }))}
          />
        </Field>
        <Field label="شیفت">
          <Select value={shift} onChange={setShift} options={SHIFTS.map((s) => ({ value: s.value, label: s.label }))} />
        </Field>

        <div className="sm:col-span-2">
          <div className="mb-2 font-medium text-sm">واگن‌های بارگیری‌شده از این چمبر</div>
          <div className="flex flex-col gap-3">
            {rows.map((r, idx) => (
              <div key={r.key} className="grid gap-3 sm:grid-cols-3 items-end rounded-lg border border-border p-3">
                <Field label={`واگن #${idx + 1}`}>
                  <Select
                    value={r.wagonId}
                    onChange={(v) => updateRow(r.key, { wagonId: v })}
                    options={wagons.map((w) => ({ value: String(w.wagon_id), label: w.wagon_name }))}
                  />
                </Field>
                <Field label="لعاب">
                  <Select
                    value={r.glazeId}
                    onChange={(v) => updateRow(r.key, { glazeId: v })}
                    options={glazes.map((g) => ({ value: String(g.glaze_id), label: g.glaze_name }))}
                  />
                </Field>
                <Field label="ساعت شروع">
                  <Input type="time" value={r.startTime} onChange={(v) => updateRow(r.key, { startTime: v })} />
                </Field>
                <Field label="ساعت پایان">
                  <Input type="time" value={r.endTime} onChange={(v) => updateRow(r.key, { endTime: v })} />
                </Field>
                <Field label="تعداد بسته">
                  <Input type="number" value={r.packages} onChange={(v) => updateRow(r.key, { packages: v })} />
                </Field>
                <Field label="تعداد خشت">
                  <Input type="number" value={r.khesht} onChange={(v) => updateRow(r.key, { khesht: v })} />
                </Field>
                {rows.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeRow(r.key)}
                    className="text-xs text-red-500 underline sm:col-span-3 text-left"
                  >
                    حذف این واگن
                  </button>
                )}
              </div>
            ))}
          </div>
          {rows.length < 4 && (
            <button type="button" onClick={addRow} className="mt-2 text-sm text-accent underline">
              + افزودن واگن دیگر (حداکثر ۴)
            </button>
          )}
        </div>

        <div className="sm:col-span-2 flex flex-col gap-3">
          <SubmitButton busy={busy}>ثبت بچ ستینگ</SubmitButton>
          {result && <Banner kind="ok">{result}</Banner>}
          {error && <Banner kind="error">{error}</Banner>}
        </div>
      </form>
    </Card>
  )
}
