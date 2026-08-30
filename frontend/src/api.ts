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

export const fetchWagons = () => api.get<Wagon[]>('/dimensions/wagons/').then((r) => r.data)
export const fetchChambers = () => api.get<Chamber[]>('/dimensions/chambers/').then((r) => r.data)
export const fetchOperators = () => api.get<Operator[]>('/dimensions/operators/').then((r) => r.data)
export const fetchProducts = () => api.get<Product[]>('/dimensions/products/').then((r) => r.data)
export const fetchGlazes = () => api.get<Glaze[]>('/dimensions/glazes/').then((r) => r.data)
export const fetchSensors = () => api.get<Sensor[]>('/dimensions/sensors/').then((r) => r.data)
export const fetchAwaitingDischarge = () =>
  api.get<AwaitingTrip[]>('/dashboard/awaiting-discharge/').then((r) => r.data)

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
