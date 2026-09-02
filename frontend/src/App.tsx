/**
 * App shell: auth guard, redesign navbar, routing for all shipped modules.
 *
 * Default `/` redirects to `/dryer` (the dryer dashboard). The old sidebar
 * layout is replaced by the redesign's top navbar. Pages are lazy-loaded.
 */
import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { getToken } from './api'
import { UIProvider } from './context/UIContext'
import { Navbar } from './components/Navbar'

const LoginPage = lazy(() => import('./pages/LoginPage'))

// Dryer quartet
const DryerDashboard = lazy(() => import('./pages/DryerDashboard'))
const DryerLoadForm = lazy(() => import('./pages/DryerLoadForm'))
const DryerReadingsForm = lazy(() => import('./pages/DryerReadingsForm'))
const DryerUnloadForm = lazy(() => import('./pages/DryerUnloadForm'))

// Setting pair
const SettingEntryForm = lazy(() => import('./pages/SettingEntryForm'))
const SettingLog = lazy(() => import('./pages/SettingLog'))

// Single-page modules
const KilnPushForm = lazy(() => import('./pages/KilnPushForm'))
const PackingForm = lazy(() => import('./pages/PackingForm'))
const JourneyPage = lazy(() => import('./pages/JourneyPage'))

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />
  return <>{children}</>
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">{children}</main>
    </div>
  )
}

function Spinner() {
  return <div className="p-10 text-center text-slate-500 dark:text-slate-400">در حال بارگذاری…</div>
}

export default function App() {
  return (
    <UIProvider>
      <BrowserRouter>
        <Suspense fallback={<Spinner />}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/*"
              element={
                <RequireAuth>
                  <Shell>
                    <Routes>
                      <Route index element={<Navigate to="/dryer" replace />} />
                      <Route path="dryer" element={<DryerDashboard />} />
                      <Route path="dryer/load" element={<DryerLoadForm />} />
                      <Route path="dryer/readings" element={<DryerReadingsForm />} />
                      <Route path="dryer/unload" element={<DryerUnloadForm />} />
                      <Route path="setting" element={<SettingEntryForm />} />
                      <Route path="setting/log" element={<SettingLog />} />
                      <Route path="kiln" element={<KilnPushForm />} />
                      <Route path="packing" element={<PackingForm />} />
                      <Route path="journey" element={<JourneyPage />} />
                      <Route path="*" element={<Navigate to="/dryer" replace />} />
                    </Routes>
                  </Shell>
                </RequireAuth>
              }
            />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </UIProvider>
  )
}
