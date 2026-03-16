import { AlertTriangle, Flame, CloudRain, Wind, Building, Car, Users } from 'lucide-react'

const storyCategories = [
  { id: 1, name: 'Your Story', icon: AlertTriangle, gradient: 'from-gray-600 to-gray-700', isAdd: true },
  { id: 2, name: 'Floods', icon: CloudRain, gradient: 'from-blue-500 to-cyan-400' },
  { id: 3, name: 'Fire', icon: Flame, gradient: 'from-orange-500 to-red-500' },
  { id: 4, name: 'Storm', icon: Wind, gradient: 'from-purple-500 to-indigo-500' },
  { id: 5, name: 'Collapse', icon: Building, gradient: 'from-gray-500 to-gray-600' },
  { id: 6, name: 'Accident', icon: Car, gradient: 'from-yellow-500 to-orange-500' },
  { id: 7, name: 'Rescue', icon: Users, gradient: 'from-green-500 to-emerald-500' },
]

export default function Stories() {
  return (
    <div className="border-b border-gray-800 py-4">
      <div className="flex gap-4 px-4 overflow-x-auto scrollbar-hide">
        {storyCategories.map((story) => (
          <button key={story.id} className="flex flex-col items-center gap-1 flex-shrink-0">
            <div className={`w-16 h-16 rounded-full p-[2px] bg-gradient-to-tr ${story.gradient}`}>
              <div className="w-full h-full rounded-full bg-black flex items-center justify-center relative">
                <story.icon className="w-6 h-6 text-white" />
                {story.isAdd && (
                  <div className="absolute -bottom-0.5 -right-0.5 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center border-2 border-black">
                    <span className="text-white text-xs font-bold">+</span>
                  </div>
                )}
              </div>
            </div>
            <span className="text-xs text-gray-400 max-w-[64px] truncate">{story.name}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
