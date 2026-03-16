import { useEffect, useState } from 'react'
import { supabase } from './supabaseClient'
import { 
  Home, 
  PlusSquare, 
  User, 
  Search, 
  Heart,
  LogOut,
  AlertTriangle
} from 'lucide-react'
import Feed from './components/Feed'
import CreatePost from './components/CreatePost'
import Profile from './components/Profile'
import Explore from './components/Explore'
import Notifications from './components/Notifications'
import AuthScreen from './components/AuthScreen'
import UserProfile from './components/UserProfile'

export default function App() {
  const [user, setUser] = useState(null)
  const [profile, setProfile] = useState(null)
  const [refreshSignal, setRefreshSignal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('home')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [viewingProfile, setViewingProfile] = useState(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      if (session?.user) {
        fetchProfile(session.user.id)
      }
      setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
      if (session?.user) {
        fetchProfile(session.user.id)
      } else {
        setProfile(null)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  async function fetchProfile(userId) {
    const { data, error } = await supabase
      .from('profiles')
      .select('*')
      .eq('id', userId)
      .single()
    
    if (!error && data) {
      setProfile(data)
    }
  }

  async function signOut() {
    await supabase.auth.signOut()
    setUser(null)
    setProfile(null)
  }

  function handlePosted() {
    setRefreshSignal((s) => s + 1)
    setShowCreateModal(false)
    setActiveTab('home')
  }

  function handleViewProfile(userId) {
    setViewingProfile(userId)
    setActiveTab('viewProfile')
  }

  function handleBackToFeed() {
    setViewingProfile(null)
    setActiveTab('home')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="animate-pulse">
          <AlertTriangle className="w-12 h-12 text-red-500" />
        </div>
      </div>
    )
  }

  // Auth Screen
  if (!user) {
    return <AuthScreen />
  }

  // Main App
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Top Header */}
      <header className="fixed top-0 left-0 right-0 bg-black border-b border-gray-800 z-50">
        <div className="max-w-lg mx-auto px-3 h-14 flex items-center justify-between">
          <h1 className="text-lg sm:text-xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            RescueConnect
          </h1>
          <div className="flex items-center gap-2 sm:gap-4">
            {profile && (
              <span className="text-xs sm:text-sm text-gray-400 max-w-[80px] sm:max-w-none truncate">@{profile.username}</span>
            )}
            <button 
              onClick={() => setActiveTab('notifications')}
              className={`p-1.5 sm:p-2 rounded-full transition-colors ${activeTab === 'notifications' ? 'text-white' : 'text-gray-400 hover:text-white'}`}
            >
              <Heart className="w-5 h-5 sm:w-6 sm:h-6" />
            </button>
            <button 
              onClick={signOut}
              className="p-1.5 sm:p-2 text-gray-400 hover:text-red-500 transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4 sm:w-5 sm:h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="pt-14 pb-20 min-h-screen">
        <div className="max-w-lg mx-auto">
          {activeTab === 'home' && (
            <Feed 
              refreshSignal={refreshSignal} 
              currentUser={user}
              profile={profile}
              onViewProfile={handleViewProfile}
            />
          )}
          {activeTab === 'explore' && (
            <Explore 
              currentUser={user}
              onViewProfile={handleViewProfile}
            />
          )}
          {activeTab === 'notifications' && <Notifications currentUser={user} />}
          {activeTab === 'profile' && (
            <Profile 
              user={user} 
              profile={profile}
              refreshSignal={refreshSignal}
              onProfileUpdate={(p) => setProfile(p)}
            />
          )}
          {activeTab === 'viewProfile' && viewingProfile && (
            <UserProfile 
              userId={viewingProfile}
              currentUser={user}
              onBack={handleBackToFeed}
            />
          )}
        </div>
      </main>

      {/* Create Post Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/90 z-50 overflow-y-auto py-8">
          <div className="min-h-full flex items-center justify-center px-4">
            <div className="w-full max-w-lg mb-20">
              <CreatePost 
                user={user}
                profile={profile}
                onPosted={handlePosted} 
                onClose={() => setShowCreateModal(false)} 
              />
            </div>
          </div>
        </div>
      )}

      {/* Bottom Navigation Bar */}
      <nav className="fixed bottom-0 left-0 right-0 bg-black border-t border-gray-800 z-50">
        <div className="max-w-lg mx-auto px-6 h-16 flex items-center justify-between">
          <button 
            onClick={() => { setActiveTab('home'); setViewingProfile(null); }}
            className={`flex flex-col items-center gap-1 transition-colors ${activeTab === 'home' ? 'text-white' : 'text-gray-500'}`}
          >
            <Home className={`w-6 h-6 ${activeTab === 'home' ? 'fill-current' : ''}`} />
            <span className="text-[10px]">Home</span>
          </button>

          <button 
            onClick={() => setActiveTab('explore')}
            className={`flex flex-col items-center gap-1 transition-colors ${activeTab === 'explore' ? 'text-white' : 'text-gray-500'}`}
          >
            <Search className="w-6 h-6" />
            <span className="text-[10px]">Explore</span>
          </button>

          <button 
            onClick={() => setShowCreateModal(true)}
            className="flex flex-col items-center gap-1 -mt-4"
          >
            <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center shadow-lg shadow-purple-500/30">
              <PlusSquare className="w-6 h-6 text-white" />
            </div>
            <span className="text-[10px] text-gray-500">Post</span>
          </button>

          <button 
            onClick={() => setActiveTab('notifications')}
            className={`flex flex-col items-center gap-1 transition-colors ${activeTab === 'notifications' ? 'text-white' : 'text-gray-500'}`}
          >
            <Heart className="w-6 h-6" />
            <span className="text-[10px]">Activity</span>
          </button>

          <button 
            onClick={() => setActiveTab('profile')}
            className={`flex flex-col items-center gap-1 transition-colors ${activeTab === 'profile' ? 'text-white' : 'text-gray-500'}`}
          >
            {profile?.avatar_url ? (
              <img src={profile.avatar_url} alt="" className="w-6 h-6 rounded-full object-cover border border-gray-600" />
            ) : (
              <User className="w-6 h-6" />
            )}
            <span className="text-[10px]">Profile</span>
          </button>
        </div>
      </nav>
    </div>
  )
}