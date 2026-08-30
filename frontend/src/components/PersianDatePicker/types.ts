import type { JalaliDate } from '../../utils/jalali'

export interface PersianDatePickerProps {
  /** Current value as a `YYYY.MM.DD` string (backend format), or null/'' for empty. */
  value?: string | null
  /** Called with the new `YYYY.MM.DD` string (or null when cleared). */
  onChange?: (value: string | null, meta: { jalali: JalaliDate; gregorianISO: string | null }) => void

  minDate?: string // YYYY.MM.DD
  maxDate?: string // YYYY.MM.DD
  placeholder?: string
  persianDigits?: boolean
  disabled?: boolean
  clearable?: boolean
  showToday?: boolean
  className?: string
  name?: string
  id?: string
  error?: string
  size?: 'sm' | 'md' | 'lg'
}
