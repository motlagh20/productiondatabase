/**
 * Jalali (Shamsi) calendar engine — backed by `jalaali-js` (Borkowski algorithm).
 *
 * Why a library instead of hand-rolled math:
 *   - Leap-year rule for the Iranian calendar is NOT "every 4 years". It follows a
 *     2820-year cycle; the correct rule is encoded in jalaali-js's `jalCal`.
 *   - Weekday of the 1st of a month must come from the *real* Gregorian conversion
 *     (via Date.getDay()), never from a hand-computed offset.
 *
 * All correctness-critical numbers go through jalaali-js. This file only adds
 * ergonomics (types, month names, navigation, weekday grid offset).
 */

import {
  isLeapJalaaliYear,
  isValidJalaaliDate,
  jalaaliMonthLength,
  toGregorian,
  toJalaali,
} from 'jalaali-js'

export interface JalaliDate {
  year: number
  month: number // 1..12
  day: number // 1..31
}

export const PERSIAN_MONTHS = [
  'فروردین',
  'اردیبهشت',
  'خرداد',
  'تیر',
  'مرداد',
  'شهریور',
  'مهر',
  'آبان',
  'آذر',
  'دی',
  'بهمن',
  'اسفند',
] as const

/** Index 0 = شنبه (Saturday). Matches Date.getDay() shifted so Saturday=0. */
export const PERSIAN_WEEKDAYS = [
  'شنبه',
  'یکشنبه',
  'دوشنبه',
  'سه‌شنبه',
  'چهارشنبه',
  'پنجشنبه',
  'جمعه',
] as const

export function isLeapYear(year: number): boolean {
  return isLeapJalaaliYear(year)
}

export function daysInMonth(year: number, month: number): number {
  return jalaaliMonthLength(year, month)
}

export function isValidDate(date: JalaliDate): boolean {
  return isValidJalaaliDate(date.year, date.month, date.day)
}

/** Jalali → JS Date (local midnight). Used for weekday computation. */
export function toDate(date: JalaliDate): Date {
  const g = toGregorian(date.year, date.month, date.day)
  return new Date(g.gy, g.gm - 1, g.gd)
}

/** JS Date → Jalali. */
export function fromDate(date: Date): JalaliDate {
  const j = toJalaali(date.getFullYear(), date.getMonth() + 1, date.getDate())
  return { year: j.jy, month: j.jm, day: j.jd }
}

/**
 * Weekday of the 1st of the given month, 0=شنبه .. 6=جمعه.
 * Derived from the real Gregorian weekday so it is always correct
 * (including leap-year edge cases).
 */
export function firstWeekdayOfMonth(year: number, month: number): number {
  const d = toDate({ year, month, day: 1 })
  return (d.getDay() + 1) % 7
}

export function today(): JalaliDate {
  return fromDate(new Date())
}

export function compare(a: JalaliDate, b: JalaliDate): number {
  if (a.year !== b.year) return a.year - b.year
  if (a.month !== b.month) return a.month - b.month
  return a.day - b.day
}

export function isSame(a: JalaliDate | null, b: JalaliDate | null): boolean {
  if (!a || !b) return false
  return a.year === b.year && a.month === b.month && a.day === b.day
}

/** Add (or subtract) whole months, clamping the day to the target month length. */
export function addMonths(date: JalaliDate, delta: number): JalaliDate {
  let year = date.year
  let month = date.month + delta
  while (month > 12) {
    month -= 12
    year += 1
  }
  while (month < 1) {
    month += 12
    year -= 1
  }
  const day = Math.min(date.day, daysInMonth(year, month))
  return { year, month, day }
}

export function startOfMonth(year: number, month: number): JalaliDate {
  return { year, month, day: 1 }
}

export function endOfMonth(year: number, month: number): JalaliDate {
  return { year, month, day: daysInMonth(year, month) }
}

/** Build the 6×7 grid cells (leading empties + days) for a month view. */
export function monthGrid(year: number, month: number): (JalaliDate | null)[] {
  const lead = firstWeekdayOfMonth(year, month)
  const total = daysInMonth(year, month)
  const cells: (JalaliDate | null)[] = []
  for (let i = 0; i < lead; i += 1) cells.push(null)
  for (let d = 1; d <= total; d += 1) cells.push({ year, month, day: d })
  while (cells.length % 7 !== 0) cells.push(null)
  return cells
}
