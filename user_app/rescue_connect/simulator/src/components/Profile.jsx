import { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient'
import { Settings, Grid, Bookmark, AlertTriangle, Camera, X, Loader2 } from 'lucide-react'

export default function Profile({ user, profile, refreshSignal, onProfileUpdate }) {
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('posts')
  const [showEditModal, setShowEditModal] = useState(false)
  const [stats, setStats] = useState({ followers: 0, following: 0 })

  useEffect(() => {
    fetchUserPosts()
    fetchStats()
  }, [refreshSignal, user])

  async function fetchUserPosts() {
    if (!user?.id) return
    setLoading(true)
    try {
      const { data, error } = await supabase
        .from('posts')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false })

      if (error) throw error
      setPosts(data ?? [])
    } catch (err) {
      console.error('Error fetching user posts', err)
    } finally {
      setLoading(false)
    }
  }

  async function fetchStats() {
    if (!user?.id) return

    const { count: followersCount } = await supabase
      .from('followers')
      .select('*', { count: 'exact', head: true })
      .eq('following_id', user.id)

    const { count: followingCount } = await supabase
      .from('followers')
      .select('*', { count: 'exact', head: true })
      .eq('follower_id', user.id)

    setStats({
      followers: followersCount || 0,
      following: followingCount || 0
    })
  }

  const getStatusStats = () => {
    return {
      pending: posts.filter(p => p.status === 'pending').length,
      verified: posts.filter(p => p.status === 'verified').length,
      dispatched: posts.filter(p => p.status === 'dispatched').length,
      resolved: posts.filter(p => p.status === 'resolved').length,
    }
  }

  const statusStats = getStatusStats()

  return (
    <div className="pb-4">
      {/* Edit Profile Modal */}
      {showEditModal && (
        <EditProfileModal 
          profile={profile}
          onClose={() => setShowEditModal(false)}
          onSave={(updatedProfile) => {
            onProfileUpdate?.(updatedProfile)
            setShowEditModal(false)
          }}
        />
      )}

      {/* Profile Header */}
      <div className="px-4 py-6">
        <div className="flex items-start gap-6">
          {/* Avatar */}
          <div className="relative w-20 h-20 rounded-full bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600 p-[3px]">
            {profile?.avatar_url ? (
              <img src={profile.avatar_url} alt="" className="w-full h-full rounded-full object-cover" />
            ) : (
              <div className="w-full h-full rounded-full bg-black flex items-center justify-center">
                <span className="text-2xl font-bold">
                  {profile?.username?.slice(0, 2).toUpperCase() || user?.id?.slice(0, 2).toUpperCase() || 'AN'}
                </span>
              </div>
            )}
          </div>

          {/* Stats */}
          <div className="flex-1">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">
                @{profile?.username || `user_${user?.id?.slice(0, 8)}`}
              </h2>
              <button 
                onClick={() => setShowEditModal(true)}
                className="text-gray-400 hover:text-white"
              >
                <Settings className="w-6 h-6" />
              </button>
            </div>

            <div className="flex gap-4">
              <div className="text-center">
                <div className="font-bold">{posts.length}</div>
                <div className="text-xs text-gray-500">Posts</div>
              </div>
              <div className="text-center">
                <div className="font-bold">{stats.followers}</div>
                <div className="text-xs text-gray-500">Followers</div>
              </div>
              <div className="text-center">
                <div className="font-bold">{stats.following}</div>
                <div className="text-xs text-gray-500">Following</div>
              </div>
            </div>
          </div>
        </div>

        {/* Bio */}
        <div className="mt-4">
          <h3 className="font-semibold">{profile?.display_name || profile?.username || 'User'}</h3>
          <p className="text-sm text-gray-400 mt-1">
            {profile?.bio || '🆘 Emergency Reporter • Helping communities stay safe'}
          </p>
          <p className="text-xs text-gray-600 mt-1">
            Member since {new Date(profile?.created_at || Date.now()).toLocaleDateString()}
          </p>
        </div>

        {/* Report Stats */}
        <div className="flex gap-3 mt-4">
          <div className="flex-1 bg-yellow-500/20 rounded-lg p-2 text-center">
            <div className="font-bold text-yellow-500">{statusStats.pending}</div>
            <div className="text-xs text-gray-400">Pending</div>
          </div>
          <div className="flex-1 bg-green-500/20 rounded-lg p-2 text-center">
            <div className="font-bold text-green-500">{statusStats.verified}</div>
            <div className="text-xs text-gray-400">Verified</div>
          </div>
          <div className="flex-1 bg-blue-500/20 rounded-lg p-2 text-center">
            <div className="font-bold text-blue-500">{statusStats.dispatched}</div>
            <div className="text-xs text-gray-400">Dispatched</div>
          </div>
          <div className="flex-1 bg-gray-500/20 rounded-lg p-2 text-center">
            <div className="font-bold text-gray-400">{statusStats.resolved}</div>
            <div className="text-xs text-gray-400">Resolved</div>
          </div>
        </div>

        {/* Edit Profile Button */}
        <button 
          onClick={() => setShowEditModal(true)}
          className="w-full mt-4 py-2 bg-gray-800 rounded-lg font-semibold text-sm hover:bg-gray-700 transition-colors"
        >
          Edit Profile
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-t border-gray-800">
        <button
          onClick={() => setActiveTab('posts')}
          className={`flex-1 py-3 flex items-center justify-center gap-2 border-t-2 transition-colors ${
            activeTab === 'posts' ? 'border-white text-white' : 'border-transparent text-gray-500'
          }`}
        >
          <Grid className="w-5 h-5" />
          <span className="text-xs">My Posts</span>
        </button>
        <button
          onClick={() => setActiveTab('saved')}
          className={`flex-1 py-3 flex items-center justify-center gap-2 border-t-2 transition-colors ${
            activeTab === 'saved' ? 'border-white text-white' : 'border-transparent text-gray-500'
          }`}
        >
          <Bookmark className="w-5 h-5" />
          <span className="text-xs">Saved</span>
        </button>
      </div>

      {/* Posts Grid */}
      {activeTab === 'posts' && (
        <div className="grid grid-cols-3 gap-0.5">
          {loading ? (
            <div className="col-span-3 flex justify-center py-10">
              <div className="animate-spin w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full"></div>
            </div>
          ) : posts.length === 0 ? (
            <div className="col-span-3 text-center py-10">
              <AlertTriangle className="w-12 h-12 text-gray-700 mx-auto mb-3" />
              <p className="text-gray-500">No posts yet</p>
              <p className="text-gray-600 text-sm mt-1">Start reporting emergencies</p>
            </div>
          ) : (
            posts.map((post) => (
              <div key={post.id} className="relative aspect-square bg-gray-900">
                {post.media_type === 'video' ? (
                  <video src={post.image_url} className="w-full h-full object-cover" muted />
                ) : post.image_url ? (
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
                {/* Status Badge */}
                <div className={`absolute top-1 right-1 w-3 h-3 rounded-full ${
                  post.status === 'pending' ? 'bg-yellow-500' :
                  post.status === 'verified' ? 'bg-green-500' :
                  post.status === 'dispatched' ? 'bg-blue-500' :
                  'bg-gray-500'
                }`} />
              </div>
            ))
          )}
        </div>
      )}

      {/* Saved Tab */}
      {activeTab === 'saved' && (
        <div className="flex flex-col items-center justify-center py-16">
          <Bookmark className="w-16 h-16 text-gray-700 mb-4" />
          <p className="text-gray-500">No saved posts</p>
        </div>
      )}
    </div>
  )
}

// Edit Profile Modal Component
function EditProfileModal({ profile, onClose, onSave }) {
  const [username, setUsername] = useState(profile?.username || '')
  const [displayName, setDisplayName] = useState(profile?.display_name || '')
  const [bio, setBio] = useState(profile?.bio || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSave() {
    if (!username.trim()) {
      setError('Username is required')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const { data, error: updateError } = await supabase
        .from('profiles')
        .update({
          username: username.toLowerCase().replace(/\s/g, '_'),
          display_name: displayName,
          bio: bio,
          updated_at: new Date().toISOString()
        })
        .eq('id', profile.id)
        .select()
        .single()

      if (updateError) throw updateError
      onSave(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 rounded-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <button onClick={onClose} className="text-gray-400">
            <X className="w-6 h-6" />
          </button>
          <h2 className="font-semibold">Edit Profile</h2>
          <button 
            onClick={handleSave}
            disabled={loading}
            className="text-blue-500 font-semibold disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Save'}
          </button>
        </div>

        <div className="p-4 space-y-4">
          {error && (
            <div className="bg-red-500/20 text-red-400 px-4 py-2 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="text-sm text-gray-400 block mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-gray-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="username"
            />
          </div>

          <div>
            <label className="text-sm text-gray-400 block mb-1">Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full bg-gray-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="Your Name"
            />
          </div>

          <div>
            <label className="text-sm text-gray-400 block mb-1">Bio</label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              className="w-full bg-gray-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
              placeholder="Tell us about yourself..."
              rows={3}
              maxLength={150}
            />
            <div className="text-right text-xs text-gray-500">{bio.length}/150</div>
          </div>
        </div>
      </div>
    </div>
  )
}
