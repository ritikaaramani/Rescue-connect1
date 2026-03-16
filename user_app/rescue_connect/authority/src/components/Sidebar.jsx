import { LayoutDashboard, FileText, MapPin, Settings, LogOut, Radio, Flame } from 'lucide-react'

export default function Sidebar({ currentPage, onNavigate, onLogout }) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'posts', label: 'All Reports', icon: FileText },
    { id: 'dispatch', label: 'Dispatch', icon: Radio },
    { id: 'map', label: 'Map View', icon: MapPin },
    { id: 'heatmap', label: 'Heatmap', icon: Flame },
    { id: 'settings', label: 'Settings', icon: Settings },
  ]

  return (
    <div className="sidebar">
      <div className="mb-8">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <span className="text-2xl">🚨</span>
          <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">RescueConnect</span>
        </h1>
        <p className="text-sm text-gray-400 mt-1">Authority Dashboard</p>
      </div>

      <nav className="space-y-2">
        {menuItems.map((item) => {
          const Icon = item.icon
          const isActive = currentPage === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left transition-all ${isActive
                  ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg shadow-blue-500/30'
                  : 'text-gray-300 hover:bg-gray-800/50 hover:text-white'
                }`}
            >
              <Icon className="w-5 h-5" />
              {item.label}
            </button>
          )
        })}
      </nav>

      <div className="mt-auto pt-8">
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-gray-400 hover:bg-red-500/10 hover:text-red-400 transition-all"
        >
          <LogOut className="w-5 h-5" />
          Sign Out
        </button>
      </div>
    </div>
  )
}
