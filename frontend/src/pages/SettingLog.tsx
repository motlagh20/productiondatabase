/** * Setting transactions (`/setting/log`) — read-only log of Setting batches with * nested wagons: client-side search (chamber/date/product), shift filter, and * paginated display (10/20/50/100 per page) with CSV export. */
import { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, ChevronLeft, ChevronRight } from 'lucide-react'

import { apiErrorMessage, fetchSettingEvents, type SettingEventData } from '../api'
import { useUI } from '../context/UIContext'
import { Banner, PageHeader, Panel, tableCls, thCls, trCls } from '../components/ui'
import { SHIFTS } from '../jalali'

type PageSize = 10 | 20 | 50 | 100

const PAGE_SIZE_OPTIONS: { label: string; value: PageSize }[] = [
  { label: '10', value: 10 },
  { label: '20', value: 20 },
  { label: '50', value: 50 },
  { label: '100', value: 100 },
]

export default function SettingLog() {
  const { t } = useUI()
  const navigate = useNavigate()
  const [events, setEvents] = useState<SettingEventData[] | null>(null)
  const [totalCount, setTotalCount] = useState(0)
  const [search, setSearch] = useState('')
  const [shiftFilter, setShiftFilter] = useState('')
  const [expanded, setExpanded] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Pagination state
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState<PageSize>(20)
  const totalPagesRef = useRef(1)

  const reload = useCallback(() => {
    const p = Math.max(1, page)
    fetchSettingEvents(p, pageSize)
      .then((data) => {
        if (data && typeof data === 'object' && 'results' in data) {
          setEvents(data.results as SettingEventData[])
          setTotalCount(data.count as number)
          totalPagesRef.current = Math.ceil((data.count as number) / pageSize) || 1
        } else if (Array.isArray(data)) {
          // Fallback: old non-paginated response
          setEvents(data as SettingEventData[])
          setTotalCount(data.length)
          totalPagesRef.current = Math.ceil(data.length / pageSize) || 1
        } else {
          setEvents([])
          setTotalCount(0)
          totalPagesRef.current = 1
        }
      })
      .catch((e: unknown) => setError(apiErrorMessage(e)))
  }, [page, pageSize])

  useEffect(() => {
    reload()
  }, [reload])

  // Recalculate total pages when page size changes
  useEffect(() => {
    totalPagesRef.current = Math.ceil(totalCount / pageSize) || 1
    if (page > totalPagesRef.current) setPage(1)
  }, [pageSize, totalCount])

  const totalPages = totalPagesRef.current

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return (events ?? []).filter((ev) => {
      if (shiftFilter !== '' && String(ev.shift) !== shiftFilter) return false
      if (!q) return true
      return (
        ev.chamber_code.toLowerCase().includes(q) ||
        ev.date_jalali.includes(q) ||
        ev.product_name.toLowerCase().includes(q) ||
        ev.supervisor_name.toLowerCase().includes(q) ||
        ev.wagons.some((w) => w.plate.toLowerCase().includes(q))
      )
    })
  }, [events, search, shiftFilter])

  const shiftLabel = (v: number) =>
    v === 1 ? t.shift_morning : v === 2 ? t.shift_evening : t.shift_night

  const goToPage = (p: number) => {
    setPage(Math.max(1, Math.min(p, totalPages)))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const exportCSV = () => {
    // Show a warning if showing only a page
    const rows = [
      ['ID', t.date_jalali, t.chamber, t.shift, t.product_select, t.supervisor, t.wagons_count, t.dryer_waste],
      ...filtered.map((ev) => [
        ev.setting_event_id,
        ev.date_jalali,
        ev.chamber_code,
        ev.shift ? shiftLabel(ev.shift) : '',
        ev.product_name,
        ev.supervisor_name,
        ev.wagons.length,
        ev.dryer_waste ?? '',
      ]),
    ]
    const csvContent = '\uFEFF' + rows.map((r) => r.join(',')).join('\n')
    const link = document.createElement('a')
    link.setAttribute('href', 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvContent))
    link.setAttribute('download', `setting_transactions_${Date.now()}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // Reset to page 1 when filters change
  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value)
    setPage(1)
  }
  const handleShiftChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setShiftFilter(e.target.value)
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon={Search}
        title={t.setting_log_title}
        color="amber"
        actions={
          <>
            <button
              onClick={exportCSV}
              className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold border border-slate-300 dark:border-slate-700"
            >
              {t.export_csv}
            </button>
            <button
              onClick={() => navigate('/setting')}
              className="px-3 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold flex items-center gap-1.5 shadow-md shadow-amber-500/20"
            >
              <Plus className="w-4 h-4" />
              {t.nav_setting_entry}
            </button>
          </>
        }
      />

      {error && <Banner kind="error">{error}</Banner>}

      {/* Filter + search */}
      <Panel className="p-4 flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute right-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={handleSearch}
            placeholder={t.search}
            className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 pr-9 pl-3 py-2 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-amber-400"
          />
        </div>
        <select
          value={shiftFilter}
          onChange={handleShiftChange}
          className="rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none"
        >
          <option value="">{t.all}</option>
          {SHIFTS.map((s) => (
            <option key={s.value} value={s.value}>
              {shiftLabel(s.value)}
            </option>
          ))}
        </select>
      </Panel>

      {/* Pagination controls */}
      <Panel className="p-4 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 dark:text-slate-400">تعداد در صفحه:</span>
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value) as PageSize)
              setPage(1)
            }}
            className="rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none"
          >
            {PAGE_SIZE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <span>صفحه {page} از {totalPages}</span>
          <span>·</span>
          <span>{totalCount} رکورد کل</span>
        </div>

        <div className="flex items-center gap-2 ml-auto">
          <button
            onClick={() => goToPage(page - 1)}
            disabled={page <= 1}
            className="p-2 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300"
            title="صفحه قبلی"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          {/* Page number quick-jump */}
          <input
            type="number"
            min={1}
            max={totalPages}
            value={page}
            onChange={(e) => {
              const v = Number(e.target.value)
              if (v >= 1 && v <= totalPages) goToPage(v)
            }}
            className="w-14 text-center rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-amber-400"
          />

          <button
            onClick={() => goToPage(page + 1)}
            disabled={page >= totalPages}
            className="p-2 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300"
            title="صفحه بعدی"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </Panel>

      {/* Table */}
      <Panel className="overflow-x-auto">
        <table className={tableCls}>
          <thead>
            <tr>
              <th className={thCls}>{t.setting_date}</th>
              <th className={thCls}>{t.chamber}</th>
              <th className={thCls}>{t.shift}</th>
              <th className={thCls}>{t.product_select}</th>
              <th className={thCls}>{t.supervisor}</th>
              <th className={thCls}>{t.wagons_count}</th>
              <th className={thCls}>{t.dryer_waste}</th>
              <th className={thCls}>{t.actions}</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((ev) => {
              const isOpen = expanded === ev.setting_event_id
              return (
                <>
                  <tr key={ev.setting_event_id} className={trCls}>
                    <td className="p-3 font-mono text-slate-600 dark:text-slate-300 tabular-nums">{ev.date_jalali}</td>
                    <td className="p-3 font-bold text-amber-600 dark:text-amber-400">{ev.chamber_code}</td>
                    <td className="p-3 text-slate-600 dark:text-slate-300">{ev.shift ? shiftLabel(ev.shift) : '—'}</td>
                    <td className="p-3 text-slate-600 dark:text-slate-300">{ev.product_name || '—'}</td>
                    <td className="p-3 text-slate-600 dark:text-slate-300">{ev.supervisor_name || ev.operator_name || '—'}</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-700 dark:text-amber-400 font-bold border border-amber-500/30">
                        {ev.wagons.length}
                      </span>
                    </td>
                    <td className="p-3 text-rose-600 dark:text-rose-400 tabular-nums">{ev.dryer_waste ?? '—'}</td>
                    <td className="p-3">
                      <button
                        onClick={() => setExpanded(isOpen ? null : ev.setting_event_id)}
                        className="text-xs font-semibold text-sky-600 dark:text-sky-400 hover:underline"
                      >
                        {isOpen ? t.close : t.actions}
                      </button>
                    </td>
                  </tr>
                  {isOpen && (
                    <tr key={`${ev.setting_event_id}-w`}>
                      <td colSpan={8} className="p-4 bg-slate-50 dark:bg-slate-800/40">
                        <div className="flex flex-wrap gap-3">
                          {ev.wagons.map((w, j) => (
                            <div key={j} className="p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-xs space-y-1">
                              <div className="flex gap-2 font-bold text-slate-900 dark:text-white">
                                <span>{t.wagon_no}: {w.plate}</span>
                              </div>
                              {w.glaze_code && <div className="text-slate-500 dark:text-slate-400">{t.glaze_override}: {w.glaze_code}</div>}
                              {(w.start_time || w.end_time) && (
                                <div className="text-slate-500 dark:text-slate-400 tabular-nums">
                                  {w.start_time} – {w.end_time}
                                </div>
                              )}
                              <div className="text-slate-500 dark:text-slate-400 tabular-nums">
                                {w.packages ? `${w.packages} ${t.packages_count}` : ''} · {w.khesht_count ? `${w.khesht_count} ${t.khesht_count}` : ''}
                              </div>
                              <div className="text-[10px] text-slate-400">{t.trip_id}: {w.trip_id}</div>
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              )
            })}
            {!events && (
              <tr>
                <td colSpan={8} className="p-4 text-center text-slate-400">{t.loading}</td>
              </tr>
            )}
            {events && events.length === 0 && (
              <tr>
                <td colSpan={8} className="p-4 text-center text-slate-400">{t.no_data}</td>
              </tr>
            )}
          </tbody>
        </table>
      </Panel>
    </div>
  )
}
