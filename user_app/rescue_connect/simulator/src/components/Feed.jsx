import { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient'
import { Heart, MessageCircle, Share2, Bookmark, MoreHorizontal, MapPin, AlertTriangle, Play } from 'lucide-react'
import Stories from './Stories'

export default function Feed({ refreshSignal = 0, currentUser, profile, onViewProfile }) {
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(false)
  const [likedPosts, setLikedPosts] = useState(new Set())
  const [profiles, setProfiles] = useState({})

  async function fetchPosts() {
    setLoading(true)
    try {
      const { data, error } = await supabase
        .from('posts')
        .select('*')
        .order('created_at', { ascending: false })

      if (error) throw error
      setPosts(data ?? [])

      // Fetch profiles for all unique user_ids
      const userIds = [...new Set(data?.map(p => p.user_id).filter(Boolean))]
      if (userIds.length > 0) {
        const { data: profilesData } = await supabase
          .from('profiles')
          .select('*')
          .in('id', userIds)
        
        if (profilesData) {
          const profilesMap = {}
          profilesData.forEach(p => { profilesMap[p.id] = p })
          setProfiles(profilesMap)
        }
      }

      // Fetch user's likes
      if (currentUser) {
        const { data: likesData } = await supabase
          .from('likes')
          .select('post_id')
          .eq('user_id', currentUser.id)
        
        if (likesData) {
          setLikedPosts(new Set(likesData.map(l => l.post_id)))
        }
      }
    } catch (err) {
      console.error('Error fetching posts', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPosts()
  }, [refreshSignal])

  const toggleLike = async (postId) => {
    if (!currentUser) return

    const isLiked = likedPosts.has(postId)
    
    // Optimistic update
    setLikedPosts(prev => {
      const newSet = new Set(prev)
      if (isLiked) {
        newSet.delete(postId)
      } else {
        newSet.add(postId)
      }
      return newSet
    })

    try {
      if (isLiked) {
        await supabase
          .from('likes')
          .delete()
          .eq('user_id', currentUser.id)
          .eq('post_id', postId)
      } else {
        await supabase
          .from('likes')
          .insert({ user_id: currentUser.id, post_id: postId })
      }
    } catch (err) {
      // Revert on error
      setLikedPosts(prev => {
        const newSet = new Set(prev)
        if (isLiked) {
          newSet.add(postId)
        } else {
          newSet.delete(postId)
        }
        return newSet
      })
    }
  }

  const getStatusColor = (status) => {
    switch(status?.toLowerCase()) {
      case 'pending': return 'bg-yellow-500'
      case 'verified': return 'bg-green-500'
      case 'dispatched': return 'bg-blue-500'
      case 'resolved': return 'bg-gray-500'
      default: return 'bg-orange-500'
    }
  }

  const getTimeAgo = (dateString) => {
    if (!dateString) return ''
    const now = new Date()
    const date = new Date(dateString)
    const seconds = Math.floor((now - date) / 1000)
    
    if (seconds < 60) return 'Just now'
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
    return `${Math.floor(seconds / 86400)}d ago`
  }

  if (loading && posts.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full"></div>
      </div>
    )
  }

  return (
    <div className="pb-4">
      {/* Stories Section */}
      <Stories />

      {/* Posts */}
      <div className="space-y-6">
        {posts.length === 0 && !loading && (
          <div className="text-center py-20">
            <AlertTriangle className="w-16 h-16 text-gray-700 mx-auto mb-4" />
            <p className="text-gray-500 text-lg">No reports yet</p>
            <p className="text-gray-600 text-sm mt-2">Be the first to report a situation</p>
          </div>
        )}

        {posts.map((post) => {
          const postProfile = profiles[post.user_id]
          const username = postProfile?.username || `user_${post.user_id?.slice(0, 8) || 'anonymous'}`
          const avatarInitials = postProfile?.username?.slice(0, 2).toUpperCase() || post.user_id?.slice(0, 2).toUpperCase() || 'AN'
          
          return (
          <article key={post.id} className="bg-black border-b border-gray-800">
            {/* Post Header */}
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <button 
                  onClick={() => post.user_id && onViewProfile?.(post.user_id)}
                  className="w-10 h-10 rounded-full bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600 p-[2px]"
                >
                  {postProfile?.avatar_url ? (
                    <img src={postProfile.avatar_url} alt="" className="w-full h-full rounded-full object-cover" />
                  ) : (
                    <div className="w-full h-full rounded-full bg-black flex items-center justify-center">
                      <span className="text-sm font-bold">{avatarInitials}</span>
                    </div>
                  )}
                </button>
                <div>
                  <div className="flex items-center gap-2">
                    <button 
                      onClick={() => post.user_id && onViewProfile?.(post.user_id)}
                      className="font-semibold text-sm hover:underline"
                    >
                      @{username}
                    </button>
                    <span className={`${getStatusColor(post.status)} text-[10px] px-2 py-0.5 rounded-full text-white font-medium`}>
                      {post.status?.toUpperCase() || 'PENDING'}
                    </span>
                  </div>
                  {post.location && (
                    <div className="flex items-center gap-1 text-gray-500 text-xs">
                      <MapPin className="w-3 h-3" />
                      <span>{post.location}</span>
                    </div>
                  )}
                </div>
              </div>
              <button className="text-gray-400 hover:text-white">
                <MoreHorizontal className="w-5 h-5" />
              </button>
            </div>

            {/* Post Image/Video */}
            {post.image_url && (
              <div className="relative aspect-square bg-gray-900">
                {post.media_type === 'video' ? (
                  <>
                    <video 
                      src={post.image_url} 
                      className="w-full h-full object-cover"
                      controls
                      playsInline
                    />
                    <div className="absolute top-2 right-2 bg-black/50 rounded-full p-1">
                      <Play className="w-4 h-4 text-white fill-white" />
                    </div>
                  </>
                ) : (
                  <img 
                    src={post.image_url} 
                    alt={post.caption ?? 'Disaster report'} 
                    className="w-full h-full object-cover"
                    onDoubleClick={() => toggleLike(post.id)}
                  />
                )}
              </div>
            )}

            {/* Action Buttons */}
            <div className="px-4 py-3">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-4">
                  <button 
                    onClick={() => toggleLike(post.id)}
                    className="transform active:scale-125 transition-transform"
                  >
                    <Heart 
                      className={`w-7 h-7 ${likedPosts.has(post.id) ? 'fill-red-500 text-red-500' : 'text-white hover:text-gray-400'}`} 
                    />
                  </button>
                  <button className="hover:text-gray-400 transition-colors">
                    <MessageCircle className="w-7 h-7" />
                  </button>
                  <button className="hover:text-gray-400 transition-colors">
                    <Share2 className="w-7 h-7" />
                  </button>
                </div>
                <button className="hover:text-gray-400 transition-colors">
                  <Bookmark className="w-7 h-7" />
                </button>
              </div>

              {/* Likes Count */}
              <div className="text-sm font-semibold mb-2">
                {Math.floor(Math.random() * 100) + (likedPosts.has(post.id) ? 1 : 0)} likes
              </div>

              {/* Caption */}
              {post.caption && (
                <div className="text-sm">
                  <button 
                    onClick={() => post.user_id && onViewProfile?.(post.user_id)}
                    className="font-semibold mr-2 hover:underline"
                  >
                    @{username}
                  </button>
                  <span className="text-gray-300">{post.caption}</span>
                </div>
              )}

              {/* Timestamp */}
              <div className="text-xs text-gray-500 mt-2">
                {getTimeAgo(post.created_at)}
              </div>
            </div>
          </article>
        )})}
      </div>

      {/* Loading more indicator */}
      {loading && posts.length > 0 && (
        <div className="flex justify-center py-8">
          <div className="animate-spin w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full"></div>
        </div>
      )}
    </div>
  )
}
