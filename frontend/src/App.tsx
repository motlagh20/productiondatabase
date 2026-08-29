/**
 * App shell: RTL layout, auth guard, and routing for the vertical slice.
 *
 * Routes map 1:1 to the slice's five screens (F2–F5 writes + F7 journey read).
 * An unauthenticated user is redirected to /login; the token lives in
 * localStorage (see api.ts) so a refresh keeps the session.
 */
import { lazy, Suspense } from 'react'
import {
  BrowserRouter,
  Navigate,
  NavLink,
  Route,
  Routes,
  useNavigate,
} from 'react-router-dom'
import {
  Boxes,
  Flame,
  LogOut,
  PackageCheck,
  Route as RouteIcon,
  Truck,
} from 'lucide-react'
import { clearToken, getToken } from './api'

const LoginPage = lazy(() => import('./pages/LoginPage'))
const SettingLoadForm = lazy(() => import('./pages/SettingLoadForm'))
const KilnPushForm = lazy(() => import('./pages/KilnPushForm'))
const KilnExitForm = lazy(() => import('./pages/KilnExitForm'))
const PackingForm = lazy(() => import('./pages/PackingForm'))
const JourneyPage = lazy(() => import('./pages/JourneyPage'))

const NAV = [
  { to: '/setting', label: 'بارگیری ستینگ', icon: Boxes },
  { to: '/kiln-push', label: 'پوش کوره', icon: Flame },
  { to: '/kiln-exit', label: 'خروج از کوره', icon: Truck },
  { to: '/packing', label: 'بسته‌بندی', icon: PackageCheck },
  { to: '/journey', label: 'مسیر واگن', icon: RouteIcon },
]

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />
  return <>{children}</>
}

function Shell({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  function logout() {
    clearToken()
    navigate('/login', { replace: true })
  }
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-2">
            <Flame className="h-5 w-5 text-sky-600" />
            <span className="font-bold">سامانه تولید — MES</span>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
          >
            <LogOut className="h-4 w-4" />
            خروج
          </button>
        </div>
      </header>
      <div className="mx-auto flex max-w-5xl gap-6 px-6 py-6">
        <nav className="flex w-52 shrink-0 flex-col gap-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? 'bg-sky-600 text-white'
                    : 'text-slate-600 hover:bg-slate-100'
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <main className="flex-1">{children}</main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="p-10 text-center text-slate-500">در حال بارگذاری…</div>}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/*"
            element={
              <RequireAuth>
                <Shell>
                  <Routes>
                    <Route index element={<Navigate to="/setting" replace />} />
                    <Route path="setting" element={<SettingLoadForm />} />
                    <Route path="kiln-push" element={<KilnPushForm />} />
                    <Route path="kiln-exit" element={<KilnExitForm />} />
                    <Route path="packing" element={<PackingForm />} />
                    <Route path="journey" element={<JourneyPage />} />
                    <Route path="*" element={<Navigate to="/setting" replace />} />
                  </Routes>
                </Shell>
              </RequireAuth>
            }
          />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
