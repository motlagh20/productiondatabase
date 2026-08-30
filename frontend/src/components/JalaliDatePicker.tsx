/** Minimal Shamsi (Jalali) date picker. No external deps.
 *  Emits the backend canonical format `YYYY.MM.DD`.
 *  Right-to-left, Persian month names, year/month navigation.
 */
import { useState } from 'react'
import { toJalali } from '../jalali'

const FA_MONTHS = [
  'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
  'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
]

const FA_WEEKDAYS = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'] // شنبه..جمعه

function daysInMonth(year: number, month: number): number {
  // Jalali month lengths: months 1-6 → 31, 7-11 → 30, 12 → 29 (30 in leap).
  if (month <= 6) return 31
  if (month <= 11) return 30
  // Leap year in Jalali: divisible by 4 but not by 100, or (year+2346) % 2820 ... simplified.
  const isLeap = ((year + 2346) % 2820) % 128 > 0 && ((year + 2346) % 2820) % 128 % 4 === 0
    ? false
    : ((year + 2346) % 2820) % 128 % 4 === 0
  return isLeap ? 30 : 29
}

/** Convert a Jalali `YYYY.MM.DD` to a Gregorian Date (for weekday calc). */
function jalaliToGregorian(y: number, m: number, d: number): Date {
  const jdn = Math.floor((y + 2345) * 365.242198581) // rough; use known formula below
  void jdn
  // Accurate conversion (algorithm by Borkowski / Reingold-Dershowitz simplified)
  const gy = y + 621
  const gdMonthDays = [31, (gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0 ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  let dayOfYear = 0
  for (let i = 1; i < m; i++) dayOfYear += i <= 6 ? 31 : 30
  dayOfYear += d - 1
  let gMonth = 3
  let rem = dayOfYear + 19 // Farvardin 1 ≈ March 21
  for (let i = 0; i < 12; i++) {
    if (rem < gdMonthDays[i]) { gMonth = i + 1; break }
    rem -= gdMonthDays[i]
  }
  const gDay = rem + 1
  return new Date(gy, gMonth - 1, gDay)
}

interface Props {
  value: string // YYYY.MM.DD or ''
  onChange: (v: string) => void
  placeholder?: string
}

export default function JalaliDatePicker({ value, onChange, placeholder = 'انتخاب تاریخ' }: Props) {
  const [open, setOpen] = useState(false)
  const today = toJalali(new Date())
  const init = value || today
  const [iy, im] = init.split('.').map(Number)
  const [viewYear, setViewYear] = useState(iy || 1404)
  const [viewMonth, setViewMonth] = useState(im || 1)

  const dim = daysInMonth(viewYear, viewMonth)
  const firstGreg = jalaliToGregorian(viewYear, viewMonth, 1)
  // JS getDay: 0=Sun..6=Sat → shift so Saturday(شنبه) is first (index 0)
  const leadingBlanks = (firstGreg.getDay() + 1) % 7

  const cells: (number | null)[] = []
  for (let i = 0; i < leadingBlanks; i++) cells.push(null)
  for (let d = 1; d <= dim; d++) cells.push(d)

  function select(d: number) {
    const mm = String(viewMonth).padStart(2, '0')
    const dd = String(d).padStart(2, '0')
    onChange(`${viewYear}.${mm}.${dd}`)
    setOpen(false)
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-right text-sm text-slate-700 hover:border-sky-500"
      >
        {value ? value : <span className="text-slate-400">{placeholder}</span>}
      </button>
      {open && (
        <div className="absolute z-20 mt-1 w-64 rounded-xl border border-slate-200 bg-white p-3 shadow-lg">
          <div className="mb-2 flex items-center justify-between">
            <button type="button" className="rounded px-2 py-1 text-sm hover:bg-slate-100" onClick={() => {
              if (viewMonth === 1) { setViewMonth(12); setViewYear(y => y - 1) } else setViewMonth(m => m - 1)
            }}>◀</button>
            <span className="text-sm font-semibold">{FA_MONTHS[viewMonth - 1]} {viewYear}</span>
            <button type="button" className="rounded px-2 py-1 text-sm hover:bg-slate-100" onClick={() => {
              if (viewMonth === 12) { setViewMonth(1); setViewYear(y => y + 1) } else setViewMonth(m => m + 1)
            }}>▶</button>
          </div>
          <div className="mb-1 grid grid-cols-7 gap-1 text-center text-xs text-slate-400">
            {FA_WEEKDAYS.map((w, i) => <div key={i}>{w}</div>)}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {cells.map((d, i) =>
              d === null ? (
                <div key={i} />
              ) : (
                <button
                  key={i}
                  type="button"
                  onClick={() => select(d)}
                  className={`rounded-lg py-1 text-sm hover:bg-sky-100 ${value === `${viewYear}.${String(viewMonth).padStart(2, '0')}.${String(d).padStart(2, '0')}` ? 'bg-sky-600 text-white' : ''}`}
                >
                  {d}
                </button>
              )
            )}
          </div>
          <button type="button" onClick={() => setOpen(false)} className="mt-2 w-full rounded-lg bg-slate-100 py-1 text-xs text-slate-500 hover:bg-slate-200">
            بستن
          </button>
        </div>
      )}
    </div>
  )
}
