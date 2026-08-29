/** Jalali (Shamsi) date helpers — display + `YYYY.MM.DD` payload format. */

const FA_MONTHS = [
  'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
  'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
]

/** Any Date → the backend's canonical Jalali string `YYYY.MM.DD`. */
export function toJalali(date: Date): string {
  const parts = new Intl.DateTimeFormat('en-u-ca-persian', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? ''
  // The Persian calendar year comes back as e.g. "1404" (sometimes with an era suffix).
  const year = get('year').replace(/[^0-9]/g, '')
  return `${year}.${get('month')}.${get('day')}`
}

/** Today as the backend's canonical Jalali string, e.g. `1404.06.08`. */
export function todayJalali(): string {
  return toJalali(new Date())
}

/** `1404.06.08` → `۸ شهریور ۱۴۰۴` for display. */
export function formatJalali(value: string | null | undefined): string {
  if (!value) return '—'
  const [y, m, d] = value.split('.')
  const monthName = FA_MONTHS[Number(m) - 1]
  if (!monthName) return value
  return `${Number(d)} ${monthName} ${y}`
}

/** An ISO timestamp from the API → Jalali date + HH:MM. */
export function formatJalaliDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const dt = new Date(iso)
  const date = new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium' }).format(dt)
  const time = new Intl.DateTimeFormat('fa-IR', { hour: '2-digit', minute: '2-digit', hour12: false }).format(dt)
  return `${date} — ${time}`
}

export const SHIFTS = [
  { value: 1, label: 'صبح' },
  { value: 2, label: 'عصر' },
  { value: 3, label: 'شب' },
]

export const TRIP_STATUS_FA: Record<string, string> = {
  body_dried: 'خشک‌شده',
  in_progress: 'در جریان (ستینگ)',
  waiting_hall: 'سالن انتظار',
  in_tunnel: 'داخل کوره',
  awaiting_discharge: 'در انتظار تخلیه',
  completed: 'تکمیل‌شده',
  abandoned: 'رهاشده',
  incomplete: 'ناقص',
}
