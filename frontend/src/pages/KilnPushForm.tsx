/** F3 — ثبت هل دادن به کوره (واگن وارد تونل می‌شود؛ ظرفیت ثابت ۴۴ در سمت سرور اعمال می‌شود). */
import { useEffect, useState } from 'react'
import {
  apiErrorMessage,
  fetchOperators,
  fetchSensors,
  postKilnPush,
  type Operator,
  type Sensor,
} from '../api'
import { Banner, Card, Field, Input, Select, SubmitButton } from '../components/Form'
import { SHIFTS, todayJalali } from '../jalali'

export default function KilnPushForm() {
  const [operators, setOperators] = useState<Operator[]>([])
  const [sensors, setSensors] = useState<Sensor[]>([])
  const [temps, setTemps] = useState<Record<string, string>>({})

  const [tripId, setTripId] = useState('')
  const [operatorId, setOperatorId] = useState('')
  const [shift, setShift] = useState('')

  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchOperators(), fetchSensors()])
      .then(([o, s]) => {
        setOperators(o)
        setSensors(s)
      })
      .catch((e) => setError(apiErrorMessage(e)))
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
        trip_id: Number(tripId),
        push_date: todayJalali(),
        operator_id: operatorId ? Number(operatorId) : undefined,
        shift: shift ? Number(shift) : undefined,
        readings,
      })
      setResult(`هل ${data.push_seq} ثبت شد (تریپ ${data.trip_id} → ${data.status}).`)
      setTripId('')
      setTemps({})
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card
      title="کوره — ثبت هل (Push)"
      subtitle="واگن از سالن انتظار وارد تونل می‌شود. ظرفیت تونل ۴۴ واگن است؛ سرور آن را اعمال می‌کند."
    >
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="شناسه تریپ (در انتظار)">
            <Input value={tripId} onChange={setTripId} type="number" />
          </Field>
          <Field label="اپراتور">
            <Select
              value={operatorId}
              onChange={setOperatorId}
              options={operators.map((o) => ({ value: o.operator_id, label: o.full_name || o.operator_code }))}
            />
          </Field>
          <Field label="شیفت">
            <Select value={shift} onChange={setShift} options={SHIFTS.map((s) => ({ value: s.value, label: s.label }))} />
          </Field>
        </div>

        <fieldset className="rounded-xl border border-slate-200 p-4">
          <legend className="px-2 text-sm font-semibold text-slate-600">دمای حسگرها (°C)</legend>
          <div className="grid gap-3 sm:grid-cols-3">
            {sensors.map((s) => (
              <label key={s.sensor_id} className="flex items-center gap-2 text-sm">
                <span className="w-28 truncate text-slate-600">{s.sensor_name || s.sensor_code}</span>
                <input
                  type="number"
                  step="0.1"
                  className="w-24 rounded-lg border border-slate-300 px-2 py-1 text-sm"
                  value={temps[s.sensor_code] ?? ''}
                  onChange={(e) => setTemps({ ...temps, [s.sensor_code]: e.target.value })}
                />
              </label>
            ))}
          </div>
        </fieldset>

        <div className="flex flex-col gap-3">
          <SubmitButton busy={busy}>ثبت هل</SubmitButton>
          {result && <Banner kind="ok">{result}</Banner>}
          {error && <Banner kind="error">{error}</Banner>}
        </div>
      </form>
    </Card>
  )
}
