import { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient'
import { ArrowLeft, Grid, Settings, UserPlus, UserMinus, Loader2 } from 'lucide-react'

export default function UserProfile({ userId, currentUser, onBack }) {
  const [profile, setProfile] = useState(null)
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [isFollowing, setIsFollowing] = useState(false)
  const [followLoading, setFollowLoading] = useState(false)
  const [stats, setStats] = useState({ followers: 0, following: 0, posts: 0 })

  useEffect(() => {
    fetchProfile()
    fetchPosts()
    checkFollowStatus()
    fetchStats()
  }, [userId])

  async function fetchProfile() {
    const { data, error } = await supabase
      .from('profiles')
      .select('*')
      .eq('id', userId)
      .single()
    
    if (!error && data) {
      setProfile(data)
    }
    setLoading(false)
  }

  async function fetchPosts() {
    const { data, error } = await supabase
      .from('posts')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
    
    if (!error) {
      setPosts(data || [])
    }
  }

  async function checkFollowStatus() {
    if (!currentUser) return
    
    const { data } = await supabase
      .from('followers')
      .select('id')
      .eq('follower_id', currentUser.id)
      .eq('following_id', userId)
      .single()
    
    setIsFollowing(!!data)
  }

  async function fetchStats() {
    // Followers count
    const { count: followersCount } = await supabase
      .from('followers')
      .select('*', { count: 'exact', head: true })
      .eq('following_id', userId)

    // Following count
    const { count: followingCount } = await supabase
      .from('followers')
      .select('*', { count: 'exact', head: true })
      .eq('follower_id', userId)

    // Posts count
    const { count: postsCount } = await supabase
      .from('posts')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', userId)

    setStats({
      followers: followersCount || 0,
      following: followingCount || 0,
      posts: postsCount || 0
    })
  }

  async function handleFollow() {
    if (!currentUser) return
    setFollowLoading(true)

    try {
      if (isFollowing) {
        // Unfollow
        await supabase
          .from('followers')
          .delete()
          .eq('follower_id', currentUser.id)
          .eq('following_id', userId)
        
        setIsFollowing(false)
        setStats(prev => ({ ...prev, followers: prev.followers - 1 }))
      } else {
        // Follow
        await supabase
          .from('followers')
          .insert({
            follower_id: currentUser.id,
            following_id: userId
          })
        
        setIsFollowing(true)
        setStats(prev => ({ ...prev, followers: prev.followers + 1 }))
      }
    } catch (err) {
      console.error('Follow error:', err)
    } finally {
      setFollowLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500">User not found</p>
        <button onClick={onBack} className="text-purple-500 mt-4">Go back</button>
      </div>
    )
  }

  const isOwnProfile = currentUser?.id === userId

  return (
    <div className="pb-4">
      {/* Header with back button */}
      <div className="flex items-center gap-4 px-4 py-3 border-b border-gray-800">
        <button onClick={onBack} className="text-white">
          <ArrowLeft className="w-6 h-6" />
        </button>
        <h2 className="font-semibold text-lg">@{profile.username}</h2>
      </div>

      {/* Profile Header */}
      <div className="px-4 py-6">
        <div className="flex items-start gap-6">
          {/* Avatar */}
          <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600 p-[3px]">
            {profile.avatar_url ? (
              <img 
                src={profile.avatar_url} 
                alt={profile.username}
                className="w-full h-full rounded-full object-cover"
              />
            ) : (
              <div className="w-full h-full rounded-full bg-black flex items-center justify-center">
                <span className="text-2xl font-bold">
                  {profile.username?.slice(0, 2).toUpperCase()}
                </span>
              </div>
            )}
          </div>

          {/* Stats */}
          <div className="flex-1">
            <div className="flex gap-6 mb-4">
              <div className="text-center">
                <div className="font-bold">{stats.posts}</div>
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

            {/* Follow Button */}
            {!isOwnProfile && (
              <button
                onClick={handleFollow}
                disabled={followLoading}
                className={`w-full py-2 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 transition-colors ${
                  isFollowing 
                    ? 'bg-gray-800 text-white hover:bg-gray-700' 
                    : 'bg-purple-500 text-white hover:bg-purple-600'
                }`}
              >
                {followLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : isFollowing ? (
                  <>
                    <UserMinus className="w-4 h-4" />
                    Following
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4" />
                    Follow
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Bio */}
        <div className="mt-4">
          <h3 className="font-semibold">{profile.display_name || profile.username}</h3>
          {profile.bio && (
            <p className="text-sm text-gray-400 mt-1">{profile.bio}</p>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-t border-gray-800">
        <button className="flex-1 py-3 flex items-center justify-center gap-2 border-t-2 border-white text-white">
          <Grid className="w-5 h-5" />
        </button>
      </div>

      {/* Posts Grid */}
      <div className="grid grid-cols-3 gap-0.5">
        {posts.length === 0 ? (
          <div className="col-span-3 text-center py-10">
            <p className="text-gray-500">No posts yet</p>
          </div>
        ) : (
          posts.map((post) => (
            <div key={post.id} className="relative aspect-square bg-gray-900">
              {post.media_type === 'video' ? (
                <video 
                  src={post.image_url} 
                  className="w-full h-full object-cover"
                  muted
                />
              ) : (
                <img 
                  src={post.image_url} 
                  alt="" 
                  className="w-full h-full object-cover"
                />
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
    </div>
  )
}
