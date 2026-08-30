/** Formatting + parsing helpers for the Jalali date picker.
 * Backend contract for date fields is the dotted string `YYYY.MM.DD` (Jalali). */

import { PERSIAN_MONTHS, isValidDate, type JalaliDate } from './calendar'

const FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
const EN_DIGITS = '0123456789'

export function toPersianDigits(value: string | number): string {
  const s = String(value)
  let out = ''
  for (const ch of s) {
    const i = EN_DIGITS.indexOf(ch)
    out += i >= 0 ? FA_DIGITS[i] : ch
  }
  return out
}

export function toEnglishDigits(value: string): string {
  let out = ''
  for (const ch of value) {
    const i = FA_DIGITS.indexOf(ch)
    out += i >= 0 ? EN_DIGITS[i] : ch
  }
  return out
}

/** `YYYY.MM.DD` (dotted, English digits) — the backend payload format. */
export function formatDotted(date: JalaliDate): string {
  const m = String(date.month).padStart(2, '0')
  const d = String(date.day).padStart(2, '0')
  return `${date.year}.${m}.${d}`
}

/** `YYYY/MM/DD` (slash, optionally Persian digits) — for display / input. */
export function formatSlash(date: JalaliDate, persianDigits = true): string {
  const base = `${date.year}/${String(date.month).padStart(2, '0')}/${String(date.day).padStart(2, '0')}`
  return persianDigits ? toPersianDigits(base) : base
}

/** `۸ شهریور ۱۴۰۴` style long display. */
export function formatLong(date: JalaliDate): string {
  const monthName = PERSIAN_MONTHS[date.month - 1] ?? ''
  return `${toPersianDigits(date.day)} ${monthName} ${toPersianDigits(date.year)}`
}

/** Parse a dotted or slashed string into a JalaliDate, or null if invalid. */
export function parse(value: string): JalaliDate | null {
  const normalized = toEnglishDigits(value.trim()).replace(/[\/\-ِ\s]/g, '.')
  const match = normalized.match(/^(\d{4})\.(\d{1,2})\.(\d{1,2})$/)
  if (!match) return null
  const date: JalaliDate = {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
  }
  return isValidDate(date) ? date : null
}
