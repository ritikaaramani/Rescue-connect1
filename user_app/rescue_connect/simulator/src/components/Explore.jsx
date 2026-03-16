import { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient'
import { Search, TrendingUp, MapPin, AlertTriangle, User } from 'lucide-react'

const categories = [
  { id: 'all', label: 'All', emoji: '🌍' },
  { id: 'flood', label: 'Floods', emoji: '🌊' },
  { id: 'fire', label: 'Fires', emoji: '🔥' },
  { id: 'earthquake', label: 'Earthquakes', emoji: '🌍' },
  { id: 'storm', label: 'Storms', emoji: '🌀' },
  { id: 'accident', label: 'Accidents', emoji: '🚗' },
]

export default function Explore({ onViewProfile }) {
  const [posts, setPosts] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState('all')
  const [searchMode, setSearchMode] = useState('posts') // 'posts' or 'users'

  useEffect(() => {
    fetchPosts()
  }, [])

  useEffect(() => {
    if (searchQuery.length > 0) {
      const doSearch = async () => {
        try {
          const { data, error } = await supabase
            .from('profiles')
            .select('*')
            .or(`username.ilike.%${searchQuery}%,display_name.ilike.%${searchQuery}%`)
            .limit(10)

          if (error) throw error
          setUsers(data ?? [])
        } catch (err) {
          console.error('Error searching users', err)
        }
      }
      doSearch()
    } else {
      setUsers([])
    }
  }, [searchQuery])

  async function fetchPosts() {
    setLoading(true)
    try {
      const { data, error } = await supabase
        .from('posts')
        .select('*')
        .order('created_at', { ascending: false })

      if (error) throw error
      setPosts(data ?? [])
    } catch (err) {
      console.error('Error fetching posts', err)
    } finally {
      setLoading(false)
    }
  }

  const filteredPosts = posts.filter(post => {
    const matchesSearch = !searchQuery || 
      post.caption?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      post.location?.toLowerCase().includes(searchQuery.toLowerCase())
    
    const matchesCategory = activeCategory === 'all' || 
      post.caption?.toLowerCase().includes(activeCategory.toLowerCase())
    
    return matchesSearch && matchesCategory
  })

  return (
    <div className="pb-4">
      {/* Search Bar */}
      <div className="p-4">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            placeholder="Search users, disasters, locations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>
      </div>

      {/* Search Tabs - Show when searching */}
      {searchQuery && (
        <div className="px-4 pb-3">
          <div className="flex gap-2 border-b border-gray-800">
            <button
              onClick={() => setSearchMode('users')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                searchMode === 'users' 
                  ? 'border-purple-500 text-white' 
                  : 'border-transparent text-gray-500 hover:text-gray-300'
              }`}
            >
              Users ({users.length})
            </button>
            <button
              onClick={() => setSearchMode('posts')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                searchMode === 'posts' 
                  ? 'border-purple-500 text-white' 
                  : 'border-transparent text-gray-500 hover:text-gray-300'
              }`}
            >
              Posts ({filteredPosts.length})
            </button>
          </div>
        </div>
      )}

      {/* User Search Results */}
      {searchQuery && searchMode === 'users' && (
        <div className="px-4 pb-4">
          {users.length === 0 ? (
            <div className="text-center py-8">
              <User className="w-12 h-12 text-gray-700 mx-auto mb-3" />
              <p className="text-gray-500">No users found</p>
              <p className="text-gray-600 text-sm mt-1">Try searching by username</p>
            </div>
          ) : (
            <div className="space-y-2">
              {users.map((user) => (
                <button
                  key={user.id}
                  onClick={() => onViewProfile?.(user.id)}
                  className="w-full flex items-center gap-3 p-3 bg-gray-800/50 rounded-xl hover:bg-gray-800 transition-colors"
                >
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-lg">
                    {user.avatar_url ? (
                      <img src={user.avatar_url} alt="" className="w-full h-full object-cover rounded-full" />
                    ) : (
                      (user.display_name || user.username || '?')[0].toUpperCase()
                    )}
                  </div>
                  <div className="text-left">
                    <div className="font-semibold text-white">{user.display_name || user.username}</div>
                    <div className="text-sm text-gray-500">@{user.username}</div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Show posts section when not searching users */}
      {(!searchQuery || searchMode === 'posts') && (
        <>
          {/* Category Pills */}
          <div className="px-4 pb-4 overflow-x-auto">
            <div className="flex gap-2">
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(cat.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full whitespace-nowrap text-sm font-medium transition-colors ${
                activeCategory === cat.id 
                  ? 'bg-white text-black' 
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              <span>{cat.emoji}</span>
              <span>{cat.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Trending Section */}
      <div className="px-4 pb-4">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="w-5 h-5 text-orange-500" />
          <h3 className="font-semibold">Trending Emergencies</h3>
        </div>
        
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-gradient-to-br from-red-500/20 to-orange-500/20 p-4 rounded-xl border border-red-500/30">
            <span className="text-2xl mb-2 block">🔥</span>
            <div className="font-semibold text-sm">Fire Reports</div>
            <div className="text-xs text-gray-400">+15% today</div>
          </div>
          <div className="bg-gradient-to-br from-blue-500/20 to-cyan-500/20 p-4 rounded-xl border border-blue-500/30">
            <span className="text-2xl mb-2 block">🌊</span>
            <div className="font-semibold text-sm">Flood Alerts</div>
            <div className="text-xs text-gray-400">5 active zones</div>
          </div>
        </div>
      </div>

      {/* Explore Grid */}
      <div className="px-4">
        <h3 className="font-semibold mb-3">Recent Reports</h3>
        
        {loading ? (
          <div className="flex justify-center py-10">
            <div className="animate-spin w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full"></div>
          </div>
        ) : filteredPosts.length === 0 ? (
          <div className="text-center py-10">
            <AlertTriangle className="w-12 h-12 text-gray-700 mx-auto mb-3" />
            <p className="text-gray-500">No reports found</p>
            {searchQuery && (
              <p className="text-gray-600 text-sm mt-1">Try a different search term</p>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-0.5 rounded-lg overflow-hidden">
            {filteredPosts.map((post, index) => (
              <div 
                key={post.id} 
                className={`relative aspect-square bg-gray-900 ${
                  index === 0 ? 'col-span-2 row-span-2' : ''
                }`}
              >
                {post.image_url ? (
                  <img 
                    src={post.image_url} 
                    alt="" 
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-gray-800">
                    <AlertTriangle className="w-8 h-8 text-gray-600" />
                  </div>
                )}
                
                {/* Overlay with info */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 hover:opacity-100 transition-opacity flex flex-col justify-end p-2">
                  {post.location && (
                    <div className="flex items-center gap-1 text-white text-xs">
                      <MapPin className="w-3 h-3" />
                      <span className="truncate">{post.location}</span>
                    </div>
                  )}
                </div>

                {/* Status indicator */}
                <div className={`absolute top-2 right-2 w-2 h-2 rounded-full ${
                  post.status === 'pending' ? 'bg-yellow-500' :
                  post.status === 'verified' ? 'bg-green-500' :
                  post.status === 'dispatched' ? 'bg-blue-500' :
                  'bg-gray-500'
                }`} />
              </div>
            ))}
          </div>
        )}
      </div>
        </>
      )}
    </div>
  )
}
