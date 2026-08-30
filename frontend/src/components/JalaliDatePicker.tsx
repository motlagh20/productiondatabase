// Thin re-export: the real implementation lives in components/PersianDatePicker.
// Kept so existing form imports (`.../components/JalaliDatePicker`) keep working.
export { default } from './PersianDatePicker/PersianDatePicker'
export type { PersianDatePickerProps as JalaliDatePickerProps } from './PersianDatePicker'
