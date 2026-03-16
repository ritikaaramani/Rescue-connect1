import { CheckCircle, AlertTriangle, Truck, Clock, Bell, Heart, MessageCircle, UserPlus } from 'lucide-react'

const mockNotifications = [
  {
    id: 1,
    type: 'status',
    icon: CheckCircle,
    iconColor: 'text-green-500',
    iconBg: 'bg-green-500/20',
    title: 'Report Verified',
    message: 'Your flood report has been verified by authorities',
    time: '2m ago',
  },
  {
    id: 2,
    type: 'dispatch',
    icon: Truck,
    iconColor: 'text-blue-500',
    iconBg: 'bg-blue-500/20',
    title: 'Help Dispatched',
    message: 'Emergency services are on their way to your reported location',
    time: '15m ago',
  },
  {
    id: 3,
    type: 'like',
    icon: Heart,
    iconColor: 'text-red-500',
    iconBg: 'bg-red-500/20',
    title: '24 people reacted',
    message: 'to your emergency report',
    time: '1h ago',
  },
  {
    id: 4,
    type: 'comment',
    icon: MessageCircle,
    iconColor: 'text-purple-500',
    iconBg: 'bg-purple-500/20',
    title: '5 new comments',
    message: 'on your flood report',
    time: '2h ago',
  },
  {
    id: 5,
    type: 'alert',
    icon: AlertTriangle,
    iconColor: 'text-orange-500',
    iconBg: 'bg-orange-500/20',
    title: 'Emergency Alert',
    message: 'Severe weather warning in your area',
    time: '3h ago',
  },
  {
    id: 6,
    type: 'pending',
    icon: Clock,
    iconColor: 'text-yellow-500',
    iconBg: 'bg-yellow-500/20',
    title: 'Report Pending',
    message: 'Your report is being reviewed by authorities',
    time: '5h ago',
  },
  {
    id: 7,
    type: 'follow',
    icon: UserPlus,
    iconColor: 'text-cyan-500',
    iconBg: 'bg-cyan-500/20',
    title: '12 new followers',
    message: 'started following your reports',
    time: '1d ago',
  },
]

export default function Notifications() {
  return (
    <div className="pb-4">
      {/* Header */}
      <div className="px-4 py-4 border-b border-gray-800">
        <h2 className="text-xl font-bold">Activity</h2>
      </div>

      {/* Today Section */}
      <div className="px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-500 uppercase">Today</h3>
      </div>

      {/* Notifications List */}
      <div className="divide-y divide-gray-800/50">
        {mockNotifications.slice(0, 4).map((notification) => (
          <NotificationItem key={notification.id} notification={notification} />
        ))}
      </div>

      {/* This Week Section */}
      <div className="px-4 py-3 mt-2">
        <h3 className="text-sm font-semibold text-gray-500 uppercase">This Week</h3>
      </div>

      <div className="divide-y divide-gray-800/50">
        {mockNotifications.slice(4).map((notification) => (
          <NotificationItem key={notification.id} notification={notification} />
        ))}
      </div>

      {/* Empty State (if no notifications) */}
      {mockNotifications.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-20 h-20 rounded-full bg-gray-800 flex items-center justify-center mb-4">
            <Bell className="w-10 h-10 text-gray-600" />
          </div>
          <p className="text-gray-500 text-lg">No notifications yet</p>
          <p className="text-gray-600 text-sm mt-1">
            When you get notifications, they'll show up here
          </p>
        </div>
      )}
    </div>
  )
}

function NotificationItem({ notification }) {
  const Icon = notification.icon
  
  return (
    <div className="px-4 py-3 hover:bg-gray-800/50 transition-colors cursor-pointer">
      <div className="flex items-start gap-3">
        <div className={`w-10 h-10 rounded-full ${notification.iconBg} flex items-center justify-center flex-shrink-0`}>
          <Icon className={`w-5 h-5 ${notification.iconColor}`} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm">
            <span className="font-semibold">{notification.title}</span>
            <span className="text-gray-400"> {notification.message}</span>
          </p>
          <p className="text-xs text-gray-500 mt-1">{notification.time}</p>
        </div>
        {notification.type === 'dispatch' && (
          <button className="px-4 py-1.5 bg-blue-500 text-white text-sm font-semibold rounded-lg">
            Track
          </button>
        )}
        {notification.type === 'follow' && (
          <button className="px-4 py-1.5 bg-gray-700 text-white text-sm font-semibold rounded-lg">
            View
          </button>
        )}
      </div>
    </div>
  )
}
