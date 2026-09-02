/**
 * Top navigation, ported from the redesign prototype and rewired to React Router.
 *
 * Differences from the prototype: links are <Link>s driven by the real route
 * (not a `currentView` string), a Journey entry is added, and the simulator /
 * user-switcher / warehouse / master-data / admin entries are dropped — those
 * modules have no backend yet.
 */
import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ChevronDown, Factory, Flame, Layers, LogOut, Package, Route, Wind } from 'lucide-react'

import { clearToken } from '../api'
import { useUI } from '../context/UIContext'
import { ThemeToggle, LangSwitch } from './UIControls'

const ITEM_CLS =
  'w-full px-3 py-2 text-xs font-medium rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 hover:text-slate-950 dark:hover:text-white flex items-center gap-2'

function tabCls(active: boolean, activeCls: string) {
  return `px-3 py-2 rounded-lg text-xs lg:text-sm font-semibold transition-colors flex items-center gap-1.5 ${
    active
      ? activeCls
      : 'text-slate-700 dark:text-slate-300 hover:text-slate-950 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/80'
  }`
}

export function Navbar() {
  const { t, isRTL } = useUI()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [openDropdown, setOpenDropdown] = useState<string | null>(null)
  const navRef = useRef<HTMLElement>(null)

  // Route change and outside clicks both close an open dropdown.
  useEffect(() => setOpenDropdown(null), [pathname])
  useEffect(() => {
    if (!openDropdown) return
    const onDown = (e: MouseEvent) => {
      if (!navRef.current?.contains(e.target as Node)) setOpenDropdown(null)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [openDropdown])

  const toggleDropdown = (key: string) => setOpenDropdown((prev) => (prev === key ? null : key))
  const inDryer = pathname.startsWith('/dryer')
  const inSetting = pathname.startsWith('/setting')

  const logout = () => {
    clearToken()
    navigate('/login', { replace: true })
  }

  const panelCls = `absolute top-full mt-2 w-52 bg-white dark:bg-slate-900 border-2 border-slate-300 dark:border-slate-800 rounded-xl shadow-2xl p-1.5 z-50 ${
    isRTL ? 'right-0' : 'left-0'
  }`

  return (
    <header className="sticky top-0 z-50 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-300 dark:border-slate-800 text-slate-900 dark:text-slate-100 shadow-md dark:shadow-xl transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-2">
          {/* Brand */}
          <Link to="/dryer" id="navbar-brand" className="flex items-center gap-3 cursor-pointer group shrink-0">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-600 via-orange-500 to-rose-500 flex items-center justify-center shadow-lg shadow-orange-500/20 group-hover:scale-105 transition-transform duration-200">
              <Factory className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base md:text-lg tracking-tight text-slate-900 dark:text-white group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
                  {t.brand}
                </span>
                <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-bold bg-amber-500/15 text-amber-800 dark:text-amber-400 border border-amber-500/30 rounded-full">
                  MES
                </span>
              </div>
              <p className="text-[11px] text-slate-600 dark:text-slate-400 hidden lg:block font-medium">{t.brand_sub}</p>
            </div>
          </Link>

          {/* Desktop navigation */}
          <nav ref={navRef} className="hidden md:flex items-center gap-1">
            <div className="relative">
              <button
                id="nav-dryer-menu"
                onClick={() => toggleDropdown('dryer')}
                aria-expanded={openDropdown === 'dryer'}
                className={tabCls(inDryer, 'bg-sky-500/15 text-sky-800 dark:text-sky-400 border border-sky-500/40')}
              >
                <Wind className="w-4 h-4 text-sky-600 dark:text-sky-400" />
                <span>{t.nav_dryer_main}</span>
                <ChevronDown className="w-3.5 h-3.5 opacity-70" />
              </button>
              {openDropdown === 'dryer' && (
                <div className={panelCls}>
                  <Link to="/dryer" className={ITEM_CLS}>
                    <Wind className="w-3.5 h-3.5 text-sky-600 dark:text-sky-400" />
                    {t.nav_dryer_dashboard}
                  </Link>
                  <Link to="/dryer/load" className={ITEM_CLS}>
                    <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    {t.nav_dryer_load}
                  </Link>
                  <Link to="/dryer/readings" className={ITEM_CLS}>
                    <span className="w-2 h-2 rounded-full bg-cyan-500" />
                    {t.nav_dryer_readings}
                  </Link>
                  <Link to="/dryer/unload" className={ITEM_CLS}>
                    <span className="w-2 h-2 rounded-full bg-amber-500" />
                    {t.nav_dryer_unload}
                  </Link>
                </div>
              )}
            </div>

            <div className="relative">
              <button
                id="nav-setting-menu"
                onClick={() => toggleDropdown('setting')}
                aria-expanded={openDropdown === 'setting'}
                className={tabCls(inSetting, 'bg-amber-500/15 text-amber-800 dark:text-amber-400 border border-amber-500/40')}
              >
                <Layers className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <span>{t.nav_setting_main}</span>
                <ChevronDown className="w-3.5 h-3.5 opacity-70" />
              </button>
              {openDropdown === 'setting' && (
                <div className={panelCls}>
                  <Link to="/setting" className={ITEM_CLS}>
                    <span className="w-2 h-2 rounded-full bg-amber-500" />
                    {t.nav_setting_entry}
                  </Link>
                  <Link to="/setting/log" className={ITEM_CLS}>
                    <span className="w-2 h-2 rounded-full bg-slate-500" />
                    {t.nav_setting_transactions}
                  </Link>
                </div>
              )}
            </div>

            <Link
              id="nav-kiln"
              to="/kiln"
              className={tabCls(pathname.startsWith('/kiln'), 'bg-rose-500/20 text-rose-700 dark:text-rose-400 border border-rose-500/40 font-bold')}
            >
              <Flame className="w-4 h-4 text-rose-500 animate-pulse" />
              <span>{t.nav_kiln_pushing}</span>
            </Link>

            <Link
              id="nav-packing"
              to="/packing"
              className={tabCls(pathname.startsWith('/packing'), 'bg-emerald-500/20 text-emerald-800 dark:text-emerald-400 border border-emerald-500/40 font-bold')}
            >
              <Package className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span>{t.nav_packaging}</span>
            </Link>

            <Link
              id="nav-journey"
              to="/journey"
              className={tabCls(pathname.startsWith('/journey'), 'bg-indigo-500/20 text-indigo-800 dark:text-indigo-400 border border-indigo-500/40 font-bold')}
            >
              <Route className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>{t.nav_journey}</span>
            </Link>
          </nav>

          {/* Utilities */}
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <LangSwitch />
            <button
              id="btn-logout"
              onClick={logout}
              title={t.logout}
              className="px-2.5 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-rose-100 dark:hover:bg-rose-900/40 text-slate-700 dark:text-slate-300 hover:text-rose-700 dark:hover:text-rose-300 text-xs font-bold flex items-center gap-1.5 border border-slate-300 dark:border-slate-700 transition-all shadow-sm"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{t.logout}</span>
            </button>
          </div>
        </div>

        {/* Mobile strip */}
        <div className="md:hidden flex items-center gap-2 overflow-x-auto py-2 border-t border-slate-200 dark:border-slate-800/80 no-scrollbar text-xs">
          {[
            { to: '/dryer', label: t.nav_dryer_main, on: inDryer, cls: 'bg-sky-500 text-slate-950' },
            { to: '/setting', label: t.nav_setting_main, on: inSetting, cls: 'bg-amber-500 text-slate-950' },
            { to: '/kiln', label: t.nav_kiln_pushing, on: pathname.startsWith('/kiln'), cls: 'bg-rose-500 text-white' },
            { to: '/packing', label: t.nav_packaging, on: pathname.startsWith('/packing'), cls: 'bg-emerald-500 text-slate-950' },
            { to: '/journey', label: t.nav_journey, on: pathname.startsWith('/journey'), cls: 'bg-indigo-500 text-white' },
          ].map((m) => (
            <Link
              key={m.to}
              to={m.to}
              className={`px-2.5 py-1 rounded-md shrink-0 font-semibold ${
                m.on ? `${m.cls} font-bold` : 'text-slate-800 dark:text-slate-300 bg-slate-100 dark:bg-slate-800'
              }`}
            >
              {m.label}
            </Link>
          ))}
        </div>
      </div>
    </header>
  )
}
