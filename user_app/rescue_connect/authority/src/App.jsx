import { useEffect, useState } from 'react'
import { supabase } from './supabaseClient'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'
import PostsTable from './components/PostsTable'
import MapView from './components/MapView'
import DispatchView from './components/DispatchView'
import HeatmapView from './components/HeatmapView'
import './index.css'

export default function App() {
  const [user, setUser] = useState(null)
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [selectedPost, setSelectedPost] = useState(null) // For viewing a specific post on map
  const [dispatchPost, setDispatchPost] = useState(null) // For dispatching a specific post

  useEffect(() => {
    let mounted = true

    async function init() {
      const { data } = await supabase.auth.getSession()
      if (!mounted) return
      setUser(data?.session?.user ?? null)
    }
    init()

    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })

    return () => {
      mounted = false
      try {
        sub?.subscription?.unsubscribe?.()
      } catch (e) {
        // noop
      }
    }
  }, [])

  async function signIn() {
    // Use anonymous sign-in (no OAuth setup required)
    try {
      const { error } = await supabase.auth.signInAnonymously()
      if (error) {
        console.error('Sign in failed', error)
        alert('Sign in failed: ' + error.message)
      }
    } catch (e) {
      console.error('Sign in error', e)
    }
  }

  async function signOut() {
    await supabase.auth.signOut()
    setUser(null)
  }

  // Login screen with landing page
  if (!user) {
    return (
      <div className="min-h-screen bg-gray-900 text-white overflow-x-hidden">
        {/* Hero Section - Clean & Impactful */}
        <div className="relative min-h-screen flex flex-col">
          {/* Hero Background Image */}
          <div 
            className="absolute inset-0 bg-cover bg-center bg-no-repeat"
            style={{ backgroundImage: "url('/images/hero-rescue.png')" }}
          >
            {/* Gradient overlay - darker on left for text readability */}
            <div className="absolute inset-0 bg-gradient-to-r from-gray-900 via-gray-900/80 to-transparent"></div>
            <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-transparent to-gray-900/50"></div>
          </div>

          {/* Navigation */}
          <nav className="relative z-20 flex items-center justify-between px-6 md:px-16 lg:px-24 py-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clipRule="evenodd" />
                </svg>
              </div>
              <span className="text-2xl font-bold tracking-tight">RescueConnect</span>
            </div>
            <div className="flex items-center gap-6">
              <a href="#how-it-works" className="hidden md:block text-gray-300 hover:text-white transition-colors">How It Works</a>
              <a href="#impact" className="hidden md:block text-gray-300 hover:text-white transition-colors">Impact</a>
              <button
                onClick={signIn}
                className="px-6 py-2.5 bg-white text-gray-900 rounded-full font-semibold hover:bg-gray-100 transition-all"
              >
                Authority Login
              </button>
            </div>
          </nav>

          {/* Hero Content - Left aligned, spacious */}
          <div className="relative z-10 flex-1 flex items-center">
            <div className="w-full max-w-7xl mx-auto px-6 md:px-16 lg:px-24 py-12">
              <div className="max-w-2xl">
                {/* Simple tag */}
                <div className="inline-flex items-center gap-2 mb-8">
                  <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                  <span className="text-red-400 font-medium text-sm tracking-wide uppercase">Live Disaster Response</span>
                </div>
                
                {/* Main headline - bigger, cleaner */}
                <h1 className="text-5xl md:text-6xl lg:text-7xl font-black leading-[1.1] mb-8 tracking-tight">
                  Every Second
                  <br />
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-red-500">
                    Saves Lives
                  </span>
                </h1>
                
                {/* Subtitle - one clear message */}
                <p className="text-xl md:text-2xl text-gray-300 mb-12 leading-relaxed max-w-xl font-light">
                  AI-powered platform that turns social media posts into coordinated rescue operations.
                </p>

                {/* Single prominent CTA */}
                <div className="flex flex-col sm:flex-row gap-4">
                  <button
                    onClick={signIn}
                    className="group px-10 py-5 bg-white text-gray-900 rounded-full font-bold text-lg hover:bg-gray-100 transition-all flex items-center justify-center gap-3 shadow-2xl"
                  >
                    <span>Access Command Center</span>
                    <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                    </svg>
                  </button>
                  <button className="px-8 py-5 text-white font-semibold hover:bg-white/10 rounded-full transition-all flex items-center justify-center gap-2">
                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                    </svg>
                    Watch Demo
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom stats bar - separate from hero content */}
          <div className="relative z-10 border-t border-white/10 bg-gray-900/80 backdrop-blur-md">
            <div className="max-w-7xl mx-auto px-6 md:px-16 lg:px-24 py-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
                <div className="text-center md:text-left">
                  <div className="text-3xl md:text-4xl font-black text-white">847+</div>
                  <div className="text-gray-400 text-sm mt-1">Lives Saved</div>
                </div>
                <div className="text-center md:text-left">
                  <div className="text-3xl md:text-4xl font-black text-white">&lt;3 min</div>
                  <div className="text-gray-400 text-sm mt-1">Avg Response</div>
                </div>
                <div className="text-center md:text-left">
                  <div className="text-3xl md:text-4xl font-black text-white">98%</div>
                  <div className="text-gray-400 text-sm mt-1">AI Accuracy</div>
                </div>
                <div className="text-center md:text-left">
                  <div className="text-3xl md:text-4xl font-black text-white">24/7</div>
                  <div className="text-gray-400 text-sm mt-1">Active Monitoring</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* How It Works Section */}
        <div id="how-it-works" className="py-24 md:py-32 px-6 md:px-16 lg:px-24 bg-gray-900">
          <div className="max-w-7xl mx-auto">
            {/* Section header */}
            <div className="max-w-3xl mb-20">
              <span className="text-orange-500 font-semibold text-sm tracking-widest uppercase">How It Works</span>
              <h2 className="text-4xl md:text-5xl lg:text-6xl font-black mt-4 mb-6 leading-tight">
                From Post to Rescue<br />in Minutes
              </h2>
              <p className="text-xl text-gray-400 leading-relaxed">
                Our AI monitors social media in real-time, detects disasters from images, 
                and coordinates rescue teams — all automatically.
              </p>
            </div>
            
            {/* Step 1 */}
            <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center mb-32">
              <div>
                <div className="flex items-center gap-4 mb-6">
                  <span className="w-14 h-14 bg-orange-500 rounded-2xl flex items-center justify-center font-black text-2xl">1</span>
                  <span className="text-orange-500 font-bold tracking-widest text-sm">DETECT</span>
                </div>
                <h3 className="text-3xl md:text-4xl font-black mb-6">Citizens Post, AI Listens</h3>
                <p className="text-gray-400 text-lg leading-relaxed mb-8">
                  When disaster strikes, citizens share photos and location on social media. Our AI instantly 
                  detects flood images, extracts text from signs using OCR, and pinpoints exact GPS coordinates 
                  from visual landmarks.
                </p>
                <div className="flex flex-wrap gap-3">
                  <span className="px-4 py-2 bg-gray-800 border border-gray-700 text-gray-300 rounded-full text-sm font-medium">Gemini Vision AI</span>
                  <span className="px-4 py-2 bg-gray-800 border border-gray-700 text-gray-300 rounded-full text-sm font-medium">Custom OCR</span>
                  <span className="px-4 py-2 bg-gray-800 border border-gray-700 text-gray-300 rounded-full text-sm font-medium">Geo-Location</span>
                </div>
              </div>
              <div className="relative">
                <div className="relative rounded-3xl overflow-hidden shadow-2xl shadow-orange-500/10">
                  <img 
                    src="/images/control-room.png" 
                    alt="Control room monitoring" 
                    className="w-full"
                  />
                </div>
                <div className="absolute -bottom-6 right-8 bg-gray-800 border border-gray-700 rounded-2xl px-6 py-4 shadow-xl">
                  <div className="flex items-center gap-3">
                    <span className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></span>
                    <span className="text-white font-semibold">Analyzing 24 posts/min</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Step 2 */}
            <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center mb-32">
              <div className="order-2 lg:order-1 relative">
                <div className="relative rounded-3xl overflow-hidden shadow-2xl shadow-blue-500/10">
                  <img 
                    src="/images/planning-room.png" 
                    alt="Authority planning" 
                    className="w-full"
                  />
                </div>
                <div className="absolute -bottom-6 left-8 bg-blue-600 rounded-2xl px-6 py-4 shadow-xl">
                  <div className="flex items-center gap-3 text-white">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    <span className="font-semibold">Verified & Prioritized</span>
                  </div>
                </div>
              </div>
              <div className="order-1 lg:order-2">
                <div className="flex items-center gap-4 mb-6">
                  <span className="w-14 h-14 bg-blue-500 rounded-2xl flex items-center justify-center font-black text-2xl">2</span>
                  <span className="text-blue-500 font-bold tracking-widest text-sm">COORDINATE</span>
                </div>
                <h3 className="text-3xl md:text-4xl font-black mb-6">Authorities Take Command</h3>
                <p className="text-gray-400 text-lg leading-relaxed mb-8">
                  District officials see all incidents on a real-time heatmap. AI filters duplicates, ranks by 
                  severity, and suggests optimal resource allocation. One-click verification triggers the dispatch.
                </p>
                <div className="flex flex-wrap gap-3">
                  <span className="px-4 py-2 bg-gray-800 border border-gray-700 text-gray-300 rounded-full text-sm font-medium">Severity Scoring</span>
                  <span className="px-4 py-2 bg-gray-800 border border-gray-700 text-gray-300 rounded-full text-sm font-medium">Deduplication</span>
                  <span className="px-4 py-2 bg-gray-800 border border-gray-700 text-gray-300 rounded-full text-sm font-medium">Heatmap</span>
                </div>
              </div>
            </div>

            {/* Step 3 */}
            <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
              <div>
                <div className="flex items-center gap-4 mb-6">
                  <span className="w-14 h-14 bg-green-500 rounded-2xl flex items-center justify-center font-black text-2xl">3</span>
                  <span className="text-green-500 font-bold tracking-widest text-sm">RESCUE</span>
                </div>
                <h3 className="text-3xl md:text-4xl font-black mb-6">Teams Reach in Minutes</h3>
                <p className="text-gray-400 text-lg leading-relaxed mb-8">
                  Rescue teams receive precise coordinates on rugged tablets. Citizens get instant email 
                  notifications that help is on the way. Real-time tracking ensures no one is left behind.
                </p>
                <div className="flex flex-wrap gap-3">
                  <span className="px-4 py-2 bg-gray-800 border border-gray-700 text-gray-300 rounded-full text-sm font-medium">GPS Navigation</span>
                  <span className="px-4 py-2 bg-gray-800 border border-gray-700 text-gray-300 rounded-full text-sm font-medium">Email Alerts</span>
                  <span className="px-4 py-2 bg-gray-800 border border-gray-700 text-gray-300 rounded-full text-sm font-medium">Live Tracking</span>
                </div>
              </div>
              <div className="relative">
                <div className="relative rounded-3xl overflow-hidden shadow-2xl shadow-green-500/10">
                  <img 
                    src="/images/field-tablet.png" 
                    alt="Field rescue with tablet" 
                    className="w-full"
                  />
                </div>
                <div className="absolute -bottom-6 right-8 bg-green-600 rounded-2xl px-6 py-4 shadow-xl">
                  <div className="flex items-center gap-3 text-white">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                    </svg>
                    <span className="font-semibold">Team 2km away</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Impact Section */}
        <div id="impact" className="relative py-32">
          <div 
            className="absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: "url('/images/base-camp.png')" }}
          >
            <div className="absolute inset-0 bg-gray-900/90"></div>
          </div>
          <div className="relative z-10 max-w-7xl mx-auto px-6 md:px-16 lg:px-24">
            <div className="text-center mb-16">
              <span className="text-orange-500 font-semibold text-sm tracking-widest uppercase">Our Impact</span>
              <h2 className="text-4xl md:text-5xl lg:text-6xl font-black mt-4">Every Number is a Life</h2>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 md:gap-8">
              <div className="bg-gray-800/60 backdrop-blur-sm rounded-3xl p-8 text-center border border-gray-700/50">
                <div className="text-5xl md:text-6xl font-black text-orange-500 mb-3">847</div>
                <div className="text-gray-300 font-medium">People Rescued</div>
              </div>
              <div className="bg-gray-800/60 backdrop-blur-sm rounded-3xl p-8 text-center border border-gray-700/50">
                <div className="text-5xl md:text-6xl font-black text-blue-500 mb-3">2.8</div>
                <div className="text-gray-300 font-medium">Min Avg Response</div>
              </div>
              <div className="bg-gray-800/60 backdrop-blur-sm rounded-3xl p-8 text-center border border-gray-700/50">
                <div className="text-5xl md:text-6xl font-black text-green-500 mb-3">98%</div>
                <div className="text-gray-300 font-medium">Accuracy Rate</div>
              </div>
              <div className="bg-gray-800/60 backdrop-blur-sm rounded-3xl p-8 text-center border border-gray-700/50">
                <div className="text-5xl md:text-6xl font-black text-purple-500 mb-3">24/7</div>
                <div className="text-gray-300 font-medium">Always Active</div>
              </div>
            </div>
          </div>
        </div>

        {/* Testimonials - Cleaner */}
        <div className="py-24 md:py-32 px-6 md:px-16 lg:px-24 bg-gray-900">
          <div className="max-w-7xl mx-auto">
            <div className="max-w-3xl mb-16">
              <span className="text-cyan-500 font-semibold text-sm tracking-widest uppercase">Testimonials</span>
              <h2 className="text-4xl md:text-5xl font-black mt-4">Stories of Survival</h2>
            </div>
            <div className="grid md:grid-cols-3 gap-8">
              <div className="bg-gray-800/50 rounded-3xl p-8 border border-gray-700/50">
                <div className="flex items-center gap-1 text-orange-400 mb-6 text-xl">
                  {"★★★★★".split("").map((s, i) => <span key={i}>{s}</span>)}
                </div>
                <p className="text-gray-300 text-lg mb-8 leading-relaxed">
                  "The water was rising fast. I posted a photo hoping someone would see. Within 10 minutes, 
                  I got an email saying rescue was coming. They found us by the shop sign in my photo."
                </p>
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-red-500 rounded-full flex items-center justify-center font-bold text-lg">R</div>
                  <div>
                    <div className="font-bold text-lg">Ramesh Kumar</div>
                    <div className="text-gray-500">Rescued from Jayanagar</div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-800/50 rounded-3xl p-8 border border-gray-700/50">
                <div className="flex items-center gap-1 text-orange-400 mb-6 text-xl">
                  {"★★★★★".split("").map((s, i) => <span key={i}>{s}</span>)}
                </div>
                <p className="text-gray-300 text-lg mb-8 leading-relaxed">
                  "As a district officer, I used to spend hours verifying reports. Now the AI 
                  does it instantly. We've cut response time by 70% and saved more lives than ever."
                </p>
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-full flex items-center justify-center font-bold text-lg">S</div>
                  <div>
                    <div className="font-bold text-lg">Suresh Patil, IAS</div>
                    <div className="text-gray-500">District Collector</div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-800/50 rounded-3xl p-8 border border-gray-700/50">
                <div className="flex items-center gap-1 text-orange-400 mb-6 text-xl">
                  {"★★★★★".split("").map((s, i) => <span key={i}>{s}</span>)}
                </div>
                <p className="text-gray-300 text-lg mb-8 leading-relaxed">
                  "My elderly parents were trapped. I was 500km away, helpless. 
                  RescueConnect got to them before I could even book a flight. Technology saved my family."
                </p>
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-emerald-500 rounded-full flex items-center justify-center font-bold text-lg">P</div>
                  <div>
                    <div className="font-bold text-lg">Priya Sharma</div>
                    <div className="text-gray-500">IT Professional, Bengaluru</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* CTA Section - Simplified */}
        <div className="py-24 md:py-32 px-6 md:px-16 lg:px-24 bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-4xl md:text-5xl lg:text-6xl font-black mb-8 leading-tight">
              Ready to Save Lives?
            </h2>
            <p className="text-xl text-gray-400 mb-12 max-w-2xl mx-auto">
              Whether you're a government official, NDRF personnel, or emergency responder — 
              join the platform that's transforming disaster response.
            </p>
            <button
              onClick={signIn}
              className="group px-12 py-6 bg-white text-gray-900 rounded-full font-bold text-xl hover:bg-gray-100 transition-all shadow-2xl inline-flex items-center gap-4"
            >
              <span>Enter Command Center</span>
              <svg className="w-6 h-6 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            </button>
          </div>
        </div>

        {/* Footer - Minimal */}
        <footer className="border-t border-gray-800 py-12 px-6 md:px-16 lg:px-24 bg-gray-900">
          <div className="max-w-7xl mx-auto">
            <div className="flex flex-col md:flex-row justify-between items-center gap-8">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clipRule="evenodd" />
                  </svg>
                </div>
                <span className="text-xl font-bold">RescueConnect</span>
              </div>
              <div className="text-center">
                <p className="text-gray-500 text-sm mb-1">Built with ❤️ by</p>
                <p className="text-lg font-semibold text-white">
                  RV College of Engineering, Bengaluru
                </p>
              </div>
              <div className="text-gray-600 text-sm">
                © 2026 RescueConnect
              </div>
            </div>
          </div>
        </footer>
      </div>
    )
  }

  // Navigate to map with a specific post
  function viewPostOnMap(post) {
    setSelectedPost(post)
    setCurrentPage('map')
  }

  // Navigate to dispatch with a specific post
  function dispatchTeam(post) {
    setDispatchPost(post)
    setCurrentPage('dispatch')
  }

  // Render current page
  function renderPage() {
    switch (currentPage) {
      case 'posts':
        return <PostsTable onViewOnMap={viewPostOnMap} />
      case 'map':
        return <MapView selectedPost={selectedPost} onClearSelection={() => setSelectedPost(null)} onDispatchTeam={dispatchTeam} />
      case 'dispatch':
        return <DispatchView selectedPost={dispatchPost} onClearSelection={() => setDispatchPost(null)} />
      case 'heatmap':
        return <HeatmapView />
      case 'settings':
        return (
          <div className="card">
            <h2 className="text-lg font-semibold">Settings</h2>
            <p className="text-gray-500 mt-2">Settings page coming soon.</p>
          </div>
        )
      default:
        return <Dashboard />
    }
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar
        currentPage={currentPage}
        onNavigate={setCurrentPage}
        onLogout={signOut}
      />
      <main className="main-content">{renderPage()}</main>
    </div>
  )
}
