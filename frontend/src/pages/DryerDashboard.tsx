/**
 * Dryer chamber dashboard (`/dryer`) — live status of every DRYER chamber.
 *
 * Three derived states from the API: empty (no open cycle) / drying (loaded,
 * not yet unloaded) / dried (unloaded, awaiting Setting discharge). Quick-reading
 * modal appends to the open cycle with an auto-incremented hour.
 */
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity, ArrowDownToLine, ArrowUpFromLine, Gauge, RefreshCw, Thermometer, Wind } from 'lucide-react'

import { apiErrorMessage, fetchDryerChamberStatus, postDryerReading, type DryerChamberStatus } from '../api'
import { useUI } from '../context/UIContext'
import { Banner, PageHeader } from '../components/ui'

type Derived = 'empty' | 'drying' | 'dried'

const BADGES: Record<Derived, { key: 'chamber_status_empty' | 'chamber_status_drying' | 'chamber_status_dried'; cls: string }> = {
  empty: { key: 'chamber_status_empty', cls: 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/30' },
  drying: { key: 'chamber_status_drying', cls: 'bg-sky-500/10 text-sky-700 dark:text-sky-400 border-sky-500/30' },
  dried: { key: 'chamber_status_dried', cls: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30' },
}

export default function DryerDashboard() {
  const { t } = useUI()
  const navigate = useNavigate()
  const [chambers, setChambers] = useState<DryerChamberStatus[] | null>(null)
  const [filter, setFilter] = useState<'all' | Derived>('all')
  const [error, setError] = useState<string | null>(null)

  // Quick-reading modal
  const [qrChamber, setQrChamber] = useState<DryerChamberStatus | null>(null)
  const [qrTemp, setQrTemp] = useState('')
  const [qrHumidity, setQrHumidity] = useState('')
  const [qrBusy, setQrBusy] = useState(false)
  const [flash, setFlash] = useState<string | null>(null)

  const reload = useCallback(() => {
    fetchDryerChamberStatus()
      .then(setChambers)
      .catch((e) => setError(apiErrorMessage(e)))
  }, [])

  useEffect(() => {
    reload()
  }, [reload])

  async function submitQuickReading(e: React.FormEvent) {
    e.preventDefault()
    if (!qrChamber) return
    setQrBusy(true)
    try {
      const data = await postDryerReading({
        chamber_id: qrChamber.chamber_id,
        temperature_c: qrTemp ? Number(qrTemp) : undefined,
        humidity_pct: qrHumidity ? Number(qrHumidity) : undefined,
      })
      setFlash(`${t.quick_reading} → ${qrChamber.chamber_code} · ${t.hour_offset} ${data.hour_offset}`)
      setQrChamber(null)
      setQrTemp('')
      setQrHumidity('')
      reload()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setQrBusy(false)
    }
  }

  const counts: Record<string, number> = { all: 0, empty: 0, drying: 0, dried: 0 }
  for (const c of chambers ?? []) {
    counts.all++
    counts[c.derived_status]++
  }
  const shown = (chambers ?? []).filter((c) => filter === 'all' || c.derived_status === filter)

  const tabCls = (on: boolean, onCls: string) =>
    `px-3 py-1 rounded-lg font-semibold transition-colors ${
      on ? onCls : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-700'
    }`

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon={Wind}
        title={t.dryer_dashboard_title}
        subtitle={t.app_title}
        color="sky"
        actions={
          <>
            <button
              onClick={() => navigate('/dryer/load')}
              className="px-3 py-1.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-md shadow-sky-600/20"
            >
              <ArrowDownToLine className="w-3.5 h-3.5" />
              {t.nav_dryer_load}
            </button>
            <button
              onClick={() => navigate('/dryer/unload')}
              className="px-3 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold flex items-center gap-1.5 shadow-md shadow-amber-500/20"
            >
              <ArrowUpFromLine className="w-3.5 h-3.5" />
              {t.nav_dryer_unload}
            </button>
            <button
              onClick={() => navigate('/dryer/readings')}
              className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold flex items-center gap-1.5 border border-slate-300 dark:border-slate-700"
            >
              <Activity className="w-3.5 h-3.5 text-cyan-500" />
              {t.nav_dryer_readings}
            </button>
            <button
              onClick={reload}
              title={t.loading}
              className="px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-300 dark:border-slate-700"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </>
        }
      />

      {error && <Banner kind="error">{error}</Banner>}
      {flash && <Banner kind="ok">{flash}</Banner>}

      {/* Filter tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="text-slate-500 dark:text-slate-400 font-medium whitespace-nowrap">{t.filter_by}:</span>
        {(
          [
            ['all', t.all, 'bg-amber-500 text-slate-950'],
            ['drying', t.chamber_status_drying, 'bg-sky-500 text-slate-950'],
            ['dried', t.chamber_status_dried, 'bg-emerald-500 text-slate-950'],
            ['empty', t.chamber_status_empty, 'bg-slate-600 text-white'],
          ] as const
        ).map(([key, label, onCls]) => (
          <button key={key} onClick={() => setFilter(key as 'all' | Derived)} className={tabCls(filter === key, onCls)}>
            {label} ({counts[key]})
          </button>
        ))}
      </div>

      {/* Chamber grid */}
      {chambers === null ? (
        <Banner kind="info">{t.loading}</Banner>
      ) : shown.length === 0 ? (
        <Banner kind="info">{t.no_data}</Banner>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {shown.map((ch) => {
            const badge = BADGES[ch.derived_status]
            const cyc = ch.current_cycle
            const lr = cyc?.latest_reading
            return (
              <div
                key={ch.chamber_id}
                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl shadow-sm flex flex-col"
              >
                <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white font-extrabold text-sm flex items-center justify-center border border-slate-300 dark:border-slate-700">
                      {ch.chamber_code}
                    </div>
                    <span className="text-xs font-bold text-slate-900 dark:text-white">
                      {t.chamber} {ch.chamber_code}
                    </span>
                  </div>
                  <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${badge.cls}`}>
                    {t[badge.key]}
                  </span>
                </div>

                {/* Latest reading */}
                <div className="grid grid-cols-2 gap-2 my-3">
                  <div className="bg-slate-100 dark:bg-slate-800/60 p-2 rounded-xl border border-slate-200 dark:border-slate-700/60">
                    <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400">
                      <span>{t.temperature}</span>
                      <Thermometer className="w-3 h-3 text-amber-500" />
                    </div>
                    <div className="mt-1 text-base font-extrabold text-amber-600 dark:text-amber-400 tabular-nums">
                      {lr?.temperature_c ?? '—'}
                    </div>
                  </div>
                  <div className="bg-slate-100 dark:bg-slate-800/60 p-2 rounded-xl border border-slate-200 dark:border-slate-700/60">
                    <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400">
                      <span>{t.humidity}</span>
                      <Gauge className="w-3 h-3 text-sky-500" />
                    </div>
                    <div className="mt-1 text-base font-extrabold text-sky-600 dark:text-sky-400 tabular-nums">
                      {lr?.humidity_pct ?? '—'}
                    </div>
                  </div>
                </div>

                {/* Cycle info */}
                {cyc ? (
                  <div className="space-y-1 text-[11px] text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/30 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500 dark:text-slate-400">{t.product_select}:</span>
                      <span className="font-bold text-slate-900 dark:text-white truncate max-w-[140px]">
                        {cyc.product_name || '—'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400">
                      <span>{t.load_date}:</span>
                      <span className="tabular-nums">
                        {cyc.load_date} {cyc.load_time ?? ''}
                      </span>
                    </div>
                    {cyc.unload_date && (
                      <div className="flex items-center justify-between text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                        <span>{t.unload_date}:</span>
                        <span className="tabular-nums">
                          {cyc.unload_date} {cyc.unload_time ?? ''}
                        </span>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="py-4 text-center text-xs text-slate-400 dark:text-slate-500 bg-slate-50 dark:bg-slate-800/20 rounded-xl border border-dashed border-slate-200 dark:border-slate-800 flex-1">
                    {t.chamber_status_empty}
                  </div>
                )}

                {/* Card actions */}
                <div className="mt-3 pt-2 border-t border-slate-200 dark:border-slate-800/80 flex items-center gap-2">
                  {ch.is_loaded && (
                    <button
                      onClick={() => setQrChamber(ch)}
                      className="flex-1 py-1 px-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-cyan-700 dark:text-cyan-400 text-[11px] font-semibold flex items-center justify-center gap-1 border border-slate-300 dark:border-slate-700"
                    >
                      <Activity className="w-3 h-3" />
                      {t.quick_reading}
                    </button>
                  )}
                  {ch.derived_status === 'dried' && (
                    <button
                      onClick={() => navigate('/dryer/unload', { state: { chamberId: ch.chamber_id } })}
                      className="flex-1 py-1 px-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold flex items-center justify-center gap-1"
                    >
                      <ArrowUpFromLine className="w-3 h-3" />
                      {t.nav_dryer_unload}
                    </button>
                  )}
                  {ch.derived_status === 'empty' && (
                    <button
                      onClick={() => navigate('/dryer/load', { state: { chamberId: ch.chamber_id } })}
                      className="flex-1 py-1 px-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-[11px] font-bold flex items-center justify-center gap-1"
                    >
                      <ArrowDownToLine className="w-3 h-3" />
                      {t.nav_dryer_load}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Quick-reading modal */}
      {qrChamber && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-2xl p-5 max-w-sm w-full shadow-2xl">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-1 flex items-center gap-2">
              <Thermometer className="w-4 h-4 text-cyan-500" />
              {t.quick_reading} — {t.chamber} {qrChamber.chamber_code}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">{t.hour_offset_auto}</p>
            <form onSubmit={submitQuickReading} className="flex flex-col gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1">{t.temperature}</label>
                <input
                  type="number"
                  step="0.1"
                  value={qrTemp}
                  onChange={(e) => setQrTemp(e.target.value)}
                  className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-900 dark:text-white focus:border-cyan-400 focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1">{t.humidity}</label>
                <input
                  type="number"
                  step="0.1"
                  value={qrHumidity}
                  onChange={(e) => setQrHumidity(e.target.value)}
                  className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-900 dark:text-white focus:border-cyan-400 focus:outline-none"
                  required
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setQrChamber(null)}
                  className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-semibold"
                >
                  {t.cancel}
                </button>
                <button
                  type="submit"
                  disabled={qrBusy}
                  className="px-4 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-60 text-white text-xs font-bold shadow-md shadow-cyan-600/20"
                >
                  {qrBusy ? '…' : t.submit_reading}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
