/** F2 — ثبت بارگذاری واگن در ستینگ (تریپ اینجا ساخته می‌شود). */
import { useEffect, useState } from 'react'
import {
  apiErrorMessage,
  fetchChambers,
  fetchGlazes,
  fetchOperators,
  fetchProducts,
  fetchWagons,
  postSettingLoad,
  type Chamber,
  type Glaze,
  type Operator,
  type Product,
  type Wagon,
} from '../api'
import { Banner, Card, Field, Input, Select, SubmitButton } from '../components/Form'
import { SHIFTS, todayJalali } from '../jalali'

export default function SettingLoadForm() {
  const [wagons, setWagons] = useState<Wagon[]>([])
  const [chambers, setChambers] = useState<Chamber[]>([])
  const [operators, setOperators] = useState<Operator[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [glazes, setGlazes] = useState<Glaze[]>([])

  const [plate, setPlate] = useState('')
  const [chamberCode, setChamberCode] = useState('')
  const [operatorId, setOperatorId] = useState('')
  const [productId, setProductId] = useState('')
  const [glazeId, setGlazeId] = useState('')
  const [shift, setShift] = useState('')
  const [packages, setPackages] = useState('')
  const [khesht, setKhesht] = useState('')
  const [startTime, setStartTime] = useState('')

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

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const data = await postSettingLoad({
        plate,
        chamber_code: chamberCode || undefined,
        operator_id: operatorId ? Number(operatorId) : undefined,
        product_id: productId ? Number(productId) : undefined,
        glaze_id: glazeId ? Number(glazeId) : undefined,
        shift: shift ? Number(shift) : undefined,
        date_jalali: todayJalali(),
        start_time: startTime || undefined,
        packages: packages ? Number(packages) : undefined,
        khesht_count: khesht ? Number(khesht) : undefined,
      })
      setResult(`تریپ ${data.trip_id} ساخته شد (بارگذاری ${data.setting_load_id}).`)
      setPlate('')
      setPackages('')
      setKhesht('')
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card
      title="ستینگ — ثبت بارگذاری واگن"
      subtitle="چمبر، ارجاع به چمبر خشک‌کن مبدأ است. شناسه تریپ توسط سیستم اختصاص می‌یابد."
    >
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Field label="پلاک واگن (۱ تا ۸۰)">
          <Select
            value={plate}
            onChange={setPlate}
            options={wagons.map((w) => ({ value: w.wagon_name, label: w.wagon_name }))}
          />
        </Field>
        <Field label="چمبر خشک‌کن (مبدأ)">
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
        <Field label="لعاب">
          <Select
            value={glazeId}
            onChange={setGlazeId}
            options={glazes.map((g) => ({ value: g.glaze_id, label: g.glaze_name }))}
          />
        </Field>
        <Field label="شیفت">
          <Select value={shift} onChange={setShift} options={SHIFTS.map((s) => ({ value: s.value, label: s.label }))} />
        </Field>
        <Field label="ساعت شروع">
          <Input type="time" value={startTime} onChange={setStartTime} />
        </Field>
        <Field label="تعداد بسته">
          <Input type="number" value={packages} onChange={setPackages} />
        </Field>
        <Field label="تعداد خشت">
          <Input type="number" value={khesht} onChange={setKhesht} />
        </Field>

        <div className="sm:col-span-2 flex flex-col gap-3">
          <SubmitButton busy={busy}>ثبت بارگذاری</SubmitButton>
          {result && <Banner kind="ok">{result}</Banner>}
          {error && <Banner kind="error">{error}</Banner>}
        </div>
      </form>
    </Card>
  )
}
