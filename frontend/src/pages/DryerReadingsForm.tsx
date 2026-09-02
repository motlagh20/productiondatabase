/**
 * Dryer readings (`/dryer/readings`) — record one temp/humidity reading against a
 * chamber's open cycle, and chart the per-hour drying curve for the selected
 * chamber. hour_offset is appended automatically when omitted (natural-key
 * idempotent on the backend).
 */
import { useEffect, useMemo, useState } from 'react'
import { Activity, History, TrendingUp } from 'lucide-react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { apiErrorMessage, fetchDryerChamberStatus, fetchDryerCycles, postDryerReading, type DryerChamberStatus, type DryerCycleData } from '../api'
import { useUI } from '../context/UIContext'
import { Banner, Field, PageHeader, Panel, PanelTitle, SelectInput, SubmitButton, TextInput, tableCls, thCls, trCls } from '../components/ui'

export default function DryerReadingsForm() {
  const { t } = useUI()
  const [chambers, setChambers] = useState<DryerChamberStatus[]>([])
  const [cycles, setCycles] = useState<DryerCycleData[]>([])

  const loadedChambers = useMemo(() => chambers.filter((c) => c.is_loaded), [chambers])
  const [chamberId, setChamberId] = useState('')
  const [temp, setTemp] = useState('')
  const [humidity, setHumidity] = useState('')

  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDryerChamberStatus()
      .then(setChambers)
      .catch(() => {})
    fetchDryerCycles()
      .then(setCycles)
      .catch(() => {})
  }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const data = await postDryerReading({
        chamber_id: Number(chamberId),
        temperature_c: temp ? Number(temp) : undefined,
        humidity_pct: humidity ? Number(humidity) : undefined,
      })
      setResult(`${t.submit_reading} ✓ (${t.hour_offset} ${data.hour_offset})`)
      reloadCycles(Number(chamberId))
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const reloadCycles = (id: number) => {
    fetchDryerCycles(id).then(setCycles).catch(() => {})
  }

  function selectChamber(id: string) {
    setChamberId(id)
    if (id) reloadCycles(Number(id))
  }

  // Chart series for the selected chamber's most recent cycle (by hour_offset)
  const chartData = useMemo(() => {
    const cycle = cycles.find((c) => c.chamber_code === chambers.find((ch) => ch.chamber_id === Number(chamberId))?.chamber_code)
    if (!cycle) return []
    return [...cycle.readings]
      .sort((a, b) => a.hour_offset - b.hour_offset)
      .map((r) => ({
        hour: `<${r.hour_offset}h>`,
        [t.temperature]: r.temperature_c === null ? null : Number(r.temperature_c),
        [t.humidity]: r.humidity_pct === null ? null : Number(r.humidity_pct),
      }))
  }, [cycles, chambers, chamberId, t])

  return (
    <div className="flex flex-col gap-5">
      <PageHeader icon={Activity} title={t.dryer_readings_title} color="cyan" />

      {result && <Banner kind="ok">{result}</Banner>}
      {error && <Banner kind="error">{error}</Banner>}

      <Panel className="p-6">
        <form onSubmit={submit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Field label={t.chamber} required>
            <SelectInput value={chamberId} onChange={(e) => selectChamber(e.target.value)} required>
              <option value="">—</option>
              {loadedChambers.map((c) => (
                <option key={c.chamber_id} value={c.chamber_id}>
                  {c.chamber_code}
                </option>
              ))}
            </SelectInput>
          </Field>
          <Field label={t.temperature} required>
            <TextInput type="number" step="0.1" value={temp} onChange={(e) => setTemp(e.target.value)} required />
          </Field>
          <Field label={t.humidity} required>
            <TextInput type="number" step="0.1" value={humidity} onChange={(e) => setHumidity(e.target.value)} required />
          </Field>
          <div className="md:col-span-3 pt-1">
            <SubmitButton busy={busy} color="cyan">
              {t.submit_reading}
            </SubmitButton>
          </div>
        </form>
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Telemetry chart */}
        <Panel className="p-5">
          <PanelTitle icon={TrendingUp} title={t.readings_chart} />
          <div className="h-64 w-full" dir="ltr">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" strokeOpacity={0.25} />
                  <XAxis dataKey="hour" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'var(--chart-bg, #0f172a)',
                      borderColor: '#334155',
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    labelStyle={{ color: '#94a3b8' }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey={t.temperature} stroke="#f59e0b" strokeWidth={2.5} dot={{ r: 4 }} activeDot={{ r: 6 }} connectNulls />
                  <Line type="monotone" dataKey={t.humidity} stroke="#38bdf8" strokeWidth={2.5} dot={{ r: 4 }} activeDot={{ r: 6 }} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-500 dark:text-slate-400">{t.no_data}</div>
            )}
          </div>
        </Panel>

        {/* Recent readings table */}
        <Panel className="p-5">
          <PanelTitle icon={History} title={t.last_readings} />
          <div className="overflow-y-auto max-h-64">
            <table className={tableCls}>
              <thead>
                <tr>
                  <th className={thCls}>{t.chamber}</th>
                  <th className={thCls}>{t.hour_offset}</th>
                  <th className={thCls}>{t.temperature}</th>
                  <th className={thCls}>{t.humidity}</th>
                </tr>
              </thead>
              <tbody>
                {cycles.slice(0, 8).flatMap((c) =>
                  c.readings.map((r) => (
                    <tr key={`${c.dryer_cycle_id}-${r.hour_offset}`} className={trCls}>
                      <td className="p-2.5 font-bold text-slate-900 dark:text-white">{c.chamber_code}</td>
                      <td className="p-2.5 text-slate-600 dark:text-slate-300 tabular-nums">H{r.hour_offset}</td>
                      <td className="p-2.5 text-amber-600 dark:text-amber-400 tabular-nums">{(r.temperature_c ?? '—') + (r.temperature_c !== null ? '°C' : '')}</td>
                      <td className="p-2.5 text-sky-600 dark:text-sky-400 tabular-nums">{(r.humidity_pct ?? '—') + (r.humidity_pct !== null ? '%' : '')}</td>
                    </tr>
                  )),
                )}
                {cycles.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-4 text-center text-slate-400">{t.no_data}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </div>
  )
}