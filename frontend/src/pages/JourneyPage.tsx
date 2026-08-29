/** F7: wagon journey trace — enter a plate name, see the full trip timeline. */
import { useState } from 'react'
import { apiErrorMessage, fetchJourney, type JourneyStage } from '../api'
import { Banner, Card, Field, SubmitButton } from '../components/Form'
import { formatJalali, formatJalaliDateTime, TRIP_STATUS_FA } from '../jalali'

function Stage({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <span className="text-xs font-semibold text-slate-500">{label}</span>
      <div className="text-sm text-slate-800">{children}</div>
    </div>
  )
}

function TripCard({ trip }: { trip: JourneyStage }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <header className="mb-3 flex items-center justify-between">
        <span className="font-bold text-slate-800">سفر #{trip.trip_id}</span>
        <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold text-sky-800">
          {TRIP_STATUS_FA[trip.status] ?? trip.status}
        </span>
      </header>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stage label="ستینگ (بارگیری)">
          {trip.setting ? (
            <>
              {formatJalali(trip.setting.date_jalali)}
              {trip.setting.shift ? ` — شیفت ${trip.setting.shift}` : ''}
            </>
          ) : (
            '—'
          )}
        </Stage>
        <Stage label="ورود به کوره">
          {trip.kiln_entry ? (
            <>
              پوش {trip.kiln_entry.push_seq}
              <br />
              {formatJalali(trip.kiln_entry.push_date)}
            </>
          ) : (
            '—'
          )}
        </Stage>
        <Stage label="خروج از کوره">
          {trip.kiln_exit ? (
            <>
              {trip.kiln_exit.entry_push_seq} → {trip.kiln_exit.exit_push_seq}
              <br />
              {trip.kiln_exit.discharged ? 'تخلیه‌شده' : 'در انتظار'}
            </>
          ) : (
            '—'
          )}
        </Stage>
        <Stage label="پکینگ">
          {trip.packing ? (
            <>
              کل {trip.packing.total_count ?? '—'} / درجه‌۱ {trip.packing.grade1_count ?? '—'}
              <br />
              ضایعات {trip.packing.waste_count ?? '—'}
            </>
          ) : (
            '—'
          )}
        </Stage>
      </div>
      <footer className="mt-3 text-xs text-slate-400">
        شروع: {formatJalaliDateTime(trip.started_at)} · پایان: {formatJalaliDateTime(trip.completed_at)}
      </footer>
    </div>
  )
}

export default function JourneyPage() {
  const [plate, setPlate] = useState('')
  const [busy, setBusy] = useState(false)
  const [trips, setTrips] = useState<JourneyStage[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setTrips(null)
    if (!plate) {
      setError('شماره پلاک واگن را وارد کنید.')
      return
    }
    setBusy(true)
    try {
      const data = await fetchJourney(plate)
      setTrips(data.trips)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card title="ردیابی سفر واگن" subtitle="شماره پلاک واگن را وارد کنید تا کل مسیر (ستینگ → کوره → پکینگ) نمایش داده شود.">
        <form onSubmit={submit} className="flex items-end gap-3">
          <div className="flex-1">
            <Field label="پلاک واگن">
              <input
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
                value={plate}
                onChange={(e) => setPlate(e.target.value)}
                inputMode="numeric"
                placeholder="مثلاً ۱۲"
              />
            </Field>
          </div>
          <SubmitButton busy={busy}>جستجو</SubmitButton>
        </form>
      </Card>

      {error && <Banner kind="error">{error}</Banner>}

      {trips && trips.length === 0 && (
        <Banner kind="ok">هیچ سفری برای این پلاک ثبت نشده است.</Banner>
      )}

      {trips && trips.length > 0 && (
        <div className="flex flex-col gap-4">
          {trips.map((t) => (
            <TripCard key={t.trip_id} trip={t} />
          ))}
        </div>
      )}
    </div>
  )
}
