import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const NAV_ITEMS = [
  { to: '/', label: 'Overview', end: true },
  { to: '/projects', label: 'Projects' },
  { to: '/jobs', label: 'Job Explorer' },
  { to: '/workers', label: 'Workers' },
  { to: '/dead-letter-queue', label: 'Dead Letter Queue' },
  { to: '/metrics', label: 'Metrics' },
]

export function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="relative w-64 shrink-0 border-r border-slate-200 bg-white">
        <div className="px-5 py-5 border-b border-slate-200">
          <h1 className="text-base font-semibold text-slate-900">Job Scheduler</h1>
          <p className="text-xs text-slate-500 mt-0.5">Distributed task platform</p>
        </div>
        <nav className="p-3 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="absolute bottom-0 w-64 border-t border-slate-200 p-4">
          <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          <button
            onClick={logout}
            className="mt-2 text-xs font-medium text-slate-600 hover:text-slate-900"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 p-8 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
