import { NavLink, Outlet } from 'react-router-dom'
import { Trophy, Users, UserCircle, Calendar, BarChart2, LogOut } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

const NAV = [
  { to: '/matches', label: 'Partidos', icon: Calendar },
  { to: '/tournaments', label: 'Torneos', icon: Trophy },
  { to: '/teams', label: 'Equipos', icon: Users },
  { to: '/players', label: 'Plantel', icon: UserCircle },
]

export default function Layout() {
  const { user, signOut } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Top nav */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3 sticky top-0 z-30">
        <BarChart2 className="text-blue-600" size={22} />
        <span className="font-black text-gray-900 text-lg tracking-tight">SAPA Stats</span>
        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-gray-500 hidden sm:inline">{user?.email}</span>
          <button
            onClick={signOut}
            className="text-gray-400 hover:text-red-500 transition-colors p-1"
            title="Cerrar sesión"
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Bottom nav */}
      <nav className="bg-white border-t border-gray-200 flex sticky bottom-0 z-30">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center py-2 gap-0.5 text-xs font-medium transition-colors ${
                isActive ? 'text-blue-600' : 'text-gray-400 hover:text-gray-700'
              }`
            }
          >
            <Icon size={20} />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
