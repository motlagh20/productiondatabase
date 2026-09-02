/** F7: wagon journey trace — enter a plate name, see the full trip timeline. */
import { useState } from 'react'
import { Route, Search } from 'lucide-react'

import { apiErrorMessage, fetchJourney, type JourneyStage } from '../api'
import { useUI } from '../context/UIContext'
import { Banner, Field, PageHeader, Panel, SubmitButton, TextInput } from '../components/ui'
import { formatJalaliDateTime, TRIP_STATUS_FA } from '../jalali'

function Stage({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-3">
      <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{label}</span>
      <div className="text-sm text-slate-800 dark:text-slate-100">{children}</div>
    </div>
  )
}

function TripCard({ trip, t }: { trip: JourneyStage; t: Record<string, string> }) {
  return (
    <Panel className="p-4">
      <header className="mb-3 flex items-center justify-between">
        <span className="font-bold text-slate-900 dark:text-white">
          {t.trip_id} #{trip.trip_id}
        </span>
        <span className="rounded-full bg-sky-500/15 px-3 py-1 text-xs font-semibold text-sky-700 dark:text-sky-400 border border-sky-500/30">
          {TRIP_STATUS_FA[trip.status] ?? trip.status}
        </span>
      </header>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stage label={t.journey_setting}>
          {trip.setting ? (
            <>
              {formatJalaliDateTime(trip.setting.date_jalali)}
              {trip.setting.shift ? ` — ${t.shift} ${trip.setting.shift}` : ''}
            </>
          ) : (
            '—'
          )}
        </Stage>
        <Stage label={t.journey_kiln_entry}>
          {trip.kiln_entry ? (
            <>
              {t.push_seq} {trip.kiln_entry.push_seq}
              <br />
              {formatJalaliDateTime(trip.kiln_entry.push_date)}
            </>
          ) : (
            '—'
          )}
        </Stage>
        <Stage label={t.journey_kiln_exit}>
          {trip.kiln_exit ? (
            <>
              {trip.kiln_exit.entry_push_seq} → {trip.kiln_exit.exit_push_seq}
              <br />
              {trip.kiln_exit.discharged ? t.discharged : t.in_tunnel}
            </>
          ) : (
            '—'
          )}
        </Stage>
        <Stage label={t.journey_packing}>
          {trip.packing ? (
            <>
              {t.total_count} {trip.packing.total_count ?? '—'} / {t.grade1} {trip.packing.grade1_count ?? '—'}
              <br />
              {t.rejects} {trip.packing.waste_count ?? '—'}
            </>
          ) : (
            '—'
          )}
        </Stage>
      </div>
      <footer className="mt-3 text-xs text-slate-400">
        {formatJalaliDateTime(trip.started_at)} → {formatJalaliDateTime(trip.completed_at)}
      </footer>
    </Panel>
  )
}

export default function JourneyPage() {
  const { t } = useUI()
  const [plate, setPlate] = useState('')
  const [busy, setBusy] = useState(false)
  const [trips, setTrips] = useState<JourneyStage[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setTrips(null)
    if (!plate) {
      setError(t.error_msg)
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
    <div className="flex flex-col gap-5">
      <PageHeader icon={Route} title={t.journey_title} subtitle={t.app_title} color="indigo" />

      <Panel className="p-6">
        <form onSubmit={submit} className="flex items-end gap-3">
          <div className="flex-1">
            <Field label={t.journey_plate}>
              <TextInput
                value={plate}
                onChange={(e) => setPlate(e.target.value)}
                inputMode="numeric"
                placeholder={t.journey_plate}
                dir="ltr"
                className="text-left"
              />
            </Field>
          </div>
          <SubmitButton busy={busy} color="indigo" className="w-auto px-6">
            <span className="flex items-center gap-1.5">
              <Search className="w-4 h-4" />
              {t.journey_search}
            </span>
          </SubmitButton>
        </form>
      </Panel>

      {error && <Banner kind="error">{error}</Banner>}
      {trips && trips.length === 0 && <Banner kind="ok">{t.journey_empty}</Banner>}

      {trips && trips.length > 0 && (
        <div className="flex flex-col gap-4">
          {trips.map((tr) => (
            <TripCard key={tr.trip_id} trip={tr} t={t} />
          ))}
        </div>
      )}
    </div>
  )
}