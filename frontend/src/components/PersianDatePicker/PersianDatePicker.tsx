import { useEffect, useMemo, useRef, useState } from 'react'

import {
  addMonths,
  compare,
  endOfMonth,
  formatDotted,
  isSame,
  monthGrid,
  PERSIAN_MONTHS,
  PERSIAN_WEEKDAYS,
  parse,
  startOfMonth,
  toDate,
  toPersianDigits,
  today,
  type JalaliDate,
} from '../../utils/jalali'

import './PersianDatePicker.css'
import type { PersianDatePickerProps } from './types'

function parseStr(s?: string | null): JalaliDate | null {
  if (!s) return null
  return parse(s)
}

/** Jalali → ISO date (YYYY-MM-DD), or null. */
function gregorianISO(date: JalaliDate): string {
  const g = toDate(date)
  const m = String(g.getMonth() + 1).padStart(2, '0')
  const d = String(g.getDate()).padStart(2, '0')
  return `${g.getFullYear()}-${m}-${d}`
}

function isDisabled(date: JalaliDate, min?: JalaliDate | null, max?: JalaliDate | null): boolean {
  if (min && compare(date, min) < 0) return true
  if (max && compare(date, max) > 0) return true
  return false
}

export default function PersianDatePicker({
  value = null,
  onChange,
  minDate,
  maxDate,
  placeholder = 'انتخاب تاریخ',
  persianDigits = true,
  disabled = false,
  clearable = true,
  showToday = true,
  className = '',
  name,
  id,
  error,
  size = 'md',
}: PersianDatePickerProps) {
  const min = useMemo(() => parseStr(minDate), [minDate])
  const max = useMemo(() => parseStr(maxDate), [maxDate])

  const selected = useMemo(() => parseStr(value), [value])

  const [open, setOpen] = useState(false)
  const [yearMode, setYearMode] = useState(false)
  const [view, setView] = useState<JalaliDate>(selected ?? today())
  const [inputValue, setInputValue] = useState(value ? formatDotted(selected!) : '')
  const [inputError, setInputError] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const s = parseStr(value)
    setInputValue(value ? formatDotted(s!) : '')
    if (s) setView(s)
  }, [value])

  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
        setYearMode(false)
      }
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [])

  const grid = useMemo(() => monthGrid(view.year, view.month), [view.year, view.month])

  const years = useMemo(() => {
    const lo = Math.max(min?.year ?? view.year - 80, view.year - 50)
    const hi = Math.min(max?.year ?? view.year + 80, view.year + 50)
    const out: number[] = []
    for (let y = lo; y <= hi; y += 1) out.push(y)
    return out
  }, [view.year, min, max])

  function emit(date: JalaliDate | null) {
    if (date && isDisabled(date, min, max)) return
    onChange?.(
      date ? formatDotted(date) : null,
      date
        ? { jalali: date, gregorianISO: gregorianISO(date) }
        : { jalali: { year: 0, month: 0, day: 0 }, gregorianISO: null },
    )
  }

  function select(date: JalaliDate) {
    if (isDisabled(date, min, max)) return
    setInputValue(formatDotted(date))
    setInputError('')
    setOpen(false)
    setYearMode(false)
    emit(date)
  }

  function commitInput() {
    const raw = inputValue.trim()
    if (!raw) {
      setInputError('')
      emit(null)
      return
    }
    const parsed = parse(raw)
    if (!parsed) {
      setInputError('تاریخ وارد شده معتبر نیست.')
      return
    }
    if (isDisabled(parsed, min, max)) {
      setInputError('این تاریخ در محدوده مجاز قرار ندارد.')
      return
    }
    setInputValue(formatDotted(parsed))
    setView(parsed)
    setInputError('')
    emit(parsed)
  }

  function goToday() {
    const t = today()
    if (isDisabled(t, min, max)) return
    setView(t)
    select(t)
  }

  const prevDisabled =
    !!min && compare(endOfMonth(view.year, view.month), min) < 0
  const nextDisabled =
    !!max && compare(startOfMonth(view.year, view.month), max) > 0

  return (
    <div ref={containerRef} className={`pdp ${className}`} dir="rtl">
      <div className={`pdp-input-wrap pdp-size-${size} ${error || inputError ? 'pdp-invalid' : ''}`}>
        <input
          id={id}
          name={name}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          disabled={disabled}
          value={inputValue}
          placeholder={placeholder}
          aria-invalid={!!(error || inputError)}
          className="pdp-input"
          onFocus={() => setOpen(true)}
          onChange={(e) => setInputValue(e.target.value)}
          onBlur={commitInput}
          onKeyDown={(e) => {
            if (e.key === 'Escape') setOpen(false)
            if (e.key === 'Enter') {
              e.preventDefault()
              commitInput()
              setOpen(false)
            }
            if (e.key === 'ArrowDown') setOpen(true)
          }}
        />
        {clearable && inputValue && !disabled && (
          <button
            type="button"
            className="pdp-clear"
            aria-label="پاک کردن"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => {
              setInputValue('')
              setInputError('')
              emit(null)
            }}
          >
            ×
          </button>
        )}
        <button
          type="button"
          className="pdp-cal-btn"
          disabled={disabled}
          aria-label="باز کردن تقویم"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => setOpen((v) => !v)}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="4" width="18" height="17" rx="2" />
            <path d="M16 2v4M8 2v4M3 9h18" />
          </svg>
        </button>
      </div>

      {(error || inputError) && <div className="pdp-error">{error || inputError}</div>}

      {open && !disabled && (
        <div className="pdp-popup" role="dialog" aria-label="تقویم شمسی">
          <div className="pdp-header">
            <button
              type="button"
              className="pdp-nav"
              disabled={prevDisabled}
              onClick={() => setView(addMonths(view, -1))}
              aria-label="ماه قبل"
            >
              ›
            </button>
            <button
              type="button"
              className="pdp-title"
              onClick={() => setYearMode((v) => !v)}
            >
              <strong>{PERSIAN_MONTHS[view.month - 1]}</strong>
              <span>{persianDigits ? toPersianDigits(view.year) : view.year}</span>
            </button>
            <button
              type="button"
              className="pdp-nav"
              disabled={nextDisabled}
              onClick={() => setView(addMonths(view, 1))}
              aria-label="ماه بعد"
            >
              ‹
            </button>
          </div>

          {yearMode ? (
            <div className="pdp-year-grid">
              {years.map((y) => (
                <button
                  key={y}
                  type="button"
                  className={y === view.year ? 'pdp-year active' : 'pdp-year'}
                  onClick={() => {
                    setView({ ...view, year: y })
                    setYearMode(false)
                  }}
                >
                  {persianDigits ? toPersianDigits(y) : y}
                </button>
              ))}
            </div>
          ) : (
            <>
              <div className="pdp-weekdays">
                {PERSIAN_WEEKDAYS.map((d) => (
                  <div key={d}>{d}</div>
                ))}
              </div>
              <div className="pdp-days">
                {grid.map((cell, i) => {
                  if (!cell) return <div key={`e${i}`} className="pdp-empty" />
                  const dis = isDisabled(cell, min, max)
                  const sel = isSame(cell, selected)
                  const tdy = isSame(cell, today())
                  return (
                    <button
                      key={`d${i}`}
                      type="button"
                      disabled={dis}
                      className={[
                        'pdp-day',
                        sel ? 'selected' : '',
                        tdy ? 'today' : '',
                        dis ? 'disabled' : '',
                      ]
                        .filter(Boolean)
                        .join(' ')}
                      onClick={() => select(cell)}
                    >
                      {persianDigits ? toPersianDigits(cell.day) : cell.day}
                    </button>
                  )
                })}
              </div>
              {showToday && (
                <div className="pdp-footer">
                  <button type="button" onClick={goToday}>
                    امروز
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
