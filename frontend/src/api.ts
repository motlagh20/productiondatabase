/**
 * API client for the MES backend.
 *
 * Token auth (DRF). Every write carries a `client_token` UUID so a retried
 * submission is idempotent server-side (N1 groundwork — the offline queue is a
 * later increment, but the contract is already replay-safe).
 */
import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

const TOKEN_KEY = 'mes_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Token ${token}`
  return config
})

export function newClientToken(): string {
  return crypto.randomUUID()
}

export async function login(username: string, password: string): Promise<string> {
  const { data } = await axios.post('/api/token/', { username, password })
  setToken(data.token)
  return data.token
}

// --- Dimension dropdown options ---
export interface Wagon { wagon_id: number; wagon_name: string }
export interface Chamber { chamber_id: number; chamber_code: string; chamber_type: string }
export interface Operator { operator_id: number; operator_code: string; full_name: string }
export interface Product { product_id: number; product_name_setting: string }
export interface Glaze { glaze_id: number; glaze_code: string; glaze_name: string }
export interface Sensor { sensor_id: number; sensor_code: string; sensor_name: string }
export interface AwaitingTrip { trip_id: number; plate: string }

export const fetchWagons = (available = false) =>
  api.get<Wagon[]>('/dimensions/wagons/' + (available ? '?available=true' : '')).then((r) => r.data)
export const fetchChambers = (loaded = false) =>
  api.get<Chamber[]>('/dimensions/chambers/' + (loaded ? '?loaded=true' : '')).then((r) => r.data)
export const fetchOperators = () => api.get<Operator[]>('/dimensions/operators/').then((r) => r.data)
export const fetchProducts = (chamberId?: number) =>
  api.get<Product[]>('/dimensions/products/' + (chamberId != null ? `?chamber_id=${chamberId}` : '')).then((r) => r.data)
export const fetchGlazes = () => api.get<Glaze[]>('/dimensions/glazes/').then((r) => r.data)
export const fetchSensors = () => api.get<Sensor[]>('/dimensions/sensors/').then((r) => r.data)
export const fetchAwaitingDischarge = () =>
  api.get<AwaitingTrip[]>('/dashboard/awaiting-discharge/').then((r) => r.data)

/** Wagons with an active (setting/waiting-hall) trip, ready to be pushed into the kiln. */
export interface ActiveWagon { trip_id: number; wagon_id: number; plate: string }
export const fetchActiveWagons = () =>
  api.get<ActiveWagon[]>('/dashboard/active-wagons/').then((r) => r.data)

// --- Writes (F2–F5) ---
export interface SettingWagonPayload {
  wagon_id: number
  glaze_id?: number
  start_time?: string
  end_time?: string
  packages?: number
  khesht_count?: number
}

export const postSettingEvent = (payload: Record<string, unknown>) =>
  api.post('/setting/events/', { ...payload, client_token: newClientToken() }).then((r) => r.data)

export interface DryerReadingPayload {
  hour_offset?: number
  humidity_pct?: number
  temperature_c?: number
}

export const postDryerCycle = (payload: Record<string, unknown>) =>
  api.post('/dryer/cycles/', { ...payload, client_token: newClientToken() }).then((r) => r.data)

export const postKilnPush = (payload: Record<string, unknown>) =>
  api.post('/kiln/pushes/', { ...payload, client_token: newClientToken() }).then((r) => r.data)

export const postPacking = (payload: Record<string, unknown>) =>
  api.post('/packing/headers/', { ...payload, client_token: newClientToken() }).then((r) => r.data)

// --- Journey (F7) ---
export interface JourneyStage {
  trip_id: number
  status: string
  started_at: string | null
  completed_at: string | null
  setting: { date_jalali: string; shift: number | null; start_time: string | null; end_time: string | null } | null
  kiln_entry: { push_seq: number; push_date: string; push_time: string | null } | null
  kiln_exit: { entry_push_seq: number; exit_push_seq: number; discharged: boolean } | null
  packing: { total_count: number | null; grade1_count: number | null; grade2_count: number | null; waste_count: number | null } | null
}

export const fetchJourney = (plate: string) =>
  api
    .get<{ plate: string; trips: JourneyStage[] }>('/dashboard/wagon-journey/', { params: { plate } })
    .then((r) => r.data)

// --- New list/status endpoints (UI merge) ---
export interface DryerReadingData {
  hour_offset: number
  humidity_pct: string | null
  temperature_c: string | null
}

export interface DryerCycleData {
  dryer_cycle_id: number
  chamber_code: string
  load_date: string
  load_time: string | null
  unload_date: string
  unload_time: string | null
  product_name: string
  finger_count: number | null
  readings: DryerReadingData[]
  created_at: string
}

export interface DryerChamberStatus {
  chamber_id: number
  chamber_code: string
  chamber_type: string
  is_loaded: boolean
  derived_status: 'empty' | 'drying' | 'dried'
  current_cycle: {
    dryer_cycle_id: number
    load_date: string
    load_time: string | null
    product_name: string
    finger_count: number | null
    unload_date: string
    unload_time: string | null
    latest_reading: { hour_offset: number; temperature_c: string | null; humidity_pct: string | null } | null
  } | null
}

export interface SettingWagonData {
  plate: string
  glaze_code: string
  start_time: string | null
  end_time: string | null
  packages: number | null
  khesht_count: number | null
  trip_id: number
}

export interface SettingEventData {
  setting_event_id: number
  date_jalali: string
  shift: number | null
  chamber_code: string
  product_name: string
  supervisor_name: string
  operator_name: string
  personnel_count: number | null
  fingers_count: number | null
  columns_count: number | null
  dryer_waste: string | null
  wagons: SettingWagonData[]
  created_at: string
}

export interface KilnReadingData {
  sensor_code: string
  temperature_c: string | null
}

export interface KilnPushData {
  kiln_push_id: number
  push_seq: number
  plate: string
  push_date: string
  push_time: string | null
  shift: number | null
  operator_name: string
  product_name: string
  exit_push_seq: number | null
  discharged: boolean
  readings: KilnReadingData[]
  created_at: string
}

export const fetchDryerChamberStatus = () =>
  api.get<DryerChamberStatus[]>('/dryer/chambers/status/').then((r) => r.data)

export const fetchDryerCycles = (chamberId?: number) =>
  api.get<DryerCycleData[]>('/dryer/cycles/list/' + (chamberId ? `?chamber_id=${chamberId}` : '')).then((r) => r.data)

export const fetchSettingEvents = (page = 1, limit = 50) =>
  api.get<{ count: number; results: SettingEventData[] }>(
    '/setting/events/list/?page=' + page + '&limit=' + limit
  ).then((r) => r.data)

export const fetchKilnPushes = () =>
  api.get<KilnPushData[]>('/kiln/pushes/list/').then((r) => r.data)

export const postDryerReading = (payload: { chamber_id: number; temperature_c?: number; humidity_pct?: number; hour_offset?: number }) =>
  api.post('/dryer/readings/', { ...payload, client_token: newClientToken() }).then((r) => r.data)

export const postDryerUnload = (payload: { chamber_id: number; unload_date?: string; unload_time?: string; unload_operator_id?: number; finger_count?: number }) =>
  api.post('/dryer/unload/', { ...payload, client_token: newClientToken() }).then((r) => r.data)

export function apiErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as Record<string, unknown> | undefined
    if (data) {
      if (typeof data.detail === 'string') return data.detail
      const first = Object.entries(data)[0]
      if (first) return `${first[0]}: ${String(first[1])}`
    }
    return err.message
  }
  return String(err)
}
