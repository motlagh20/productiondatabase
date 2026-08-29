/** F4: mark a trip's wagon as discharged from the kiln tunnel (exit = entry + 43). */
import { useEffect, useState } from 'react'
import { apiErrorMessage, postKilnExit } from '../api'
import { Banner, Card, Field, Select, SubmitButton } from '../components/Form'
import { toJalali } from '../jalali'

interface InTunnelTrip {
  trip_id: number
  plate: string
}

export default function KilnExitForm() {
  const [tripId, setTripId] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  // The awaiting-discharge list is the OUTPUT of exits; the input list (in-tunnel
  // trips) is not a dedicated endpoint in this slice, so the operator types the
  // trip_id shown by the kiln push form. A dropdown of in-tunnel trips is a later
  // increment (needs a GET /api/kiln/in-tunnel/ endpoint).
  const [trips, setTrips] = useState<InTunnelTrip[]>([])

  useEffect(() => {
    // Best-effort: nothing to fetch yet in this slice. Left as a hook point.
    setTrips([])
  }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    if (!tripId) {
      setError('شناسه سفر (trip_id) لازم است.')
      return
    }
    setBusy(true)
    try {
      const data = await postKilnExit({ trip_id: Number(tripId), exit_date: toJalali(new Date()) })
      setResult(
        `خروج ثبت شد. ورود در پوش ${data.entry_push_seq} → خروج در پوش ${data.exit_push_seq} ` +
          `(وضعیت: ${data.status}).`,
      )
      setTripId('')
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card title="خروج از کوره" subtitle="واگن از تونل خارج و به لیست تخلیه اضافه می‌شود (خروج = ورود + ۴۳).">
      <form onSubmit={submit} className="flex flex-col gap-4">
        {trips.length > 0 ? (
          <Field label="سفر در تونل">
            <Select
              value={tripId}
              onChange={setTripId}
              options={trips.map((t) => ({ value: t.trip_id, label: `سفر ${t.trip_id} — پلاک ${t.plate}` }))}
            />
          </Field>
        ) : (
          <Field label="شناسه سفر (trip_id)">
            <input
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
              value={tripId}
              onChange={(e) => setTripId(e.target.value)}
              inputMode="numeric"
              placeholder="مثلاً ۲"
            />
          </Field>
        )}
        <SubmitButton busy={busy}>ثبت خروج</SubmitButton>
        {result && <Banner kind="ok">{result}</Banner>}
        {error && <Banner kind="error">{error}</Banner>}
      </form>
    </Card>
  )
}
