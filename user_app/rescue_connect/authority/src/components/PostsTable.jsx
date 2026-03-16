// PostsTable Component - Disaster Reports Management
// Updated: Feb 2026 - Added ML backend notice dialog and processing indicators
import { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient'
import { RefreshCw, MapPin, Clock, User, CheckCircle, XCircle, Zap, Brain, AlertTriangle, Copy, X, Navigation } from 'lucide-react'
import mlApi from '../lib/mlApi'

// Major Indian cities
const INDIAN_CITIES = [
  'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 'Pune', 'Ahmedabad',
  'Jaipur', 'Lucknow', 'Chandigarh', 'Indore', 'Thane', 'Bhopal', 'Visakhapatnam',
  'Pimpri-Chinchwad', 'Patna', 'Vadodara', 'Ghaziabad', 'Ludhiana', 'Agra', 'Nashik',
  'Aurangabad', 'Dhanbad', 'Amritsar', 'Navi Mumbai', 'Ranchi', 'Howrah', 'Coimbatore',
  'Jabalpur', 'Srinagar', 'Kochi', 'Vijaywada', 'Jodhpur', 'Madurai', 'Raipur', 'Kota',
  'Guwahati', 'Gurgaon', 'Noida', 'Greater Noida', 'Faridabad', 'Ghaziabad', 'Varanasi',
  'Surat', 'Nagpur', 'Indore', 'Kanpur', 'Meerut', 'Prayagraj', 'Aligarh', 'Kota',
  'Rajkot', 'Salem', 'Thiruvananthapuram', 'Calicut', 'Mangalore', 'Mysore', 'Nashik'
]

// Quick lookup for common landmarks (for fast path filtering)
const LANDMARKS_TO_CITY = {
  'kempegowda international airport': 'Bangalore',
  'kempegowda': 'Bangalore',
  'indira gandhi international airport': 'Delhi',
  'indira gandhi': 'Delhi',
  'marine drive': 'Mumbai',
  'gateway of india': 'Mumbai',
  'taj mahal': 'Agra',
  'hawa mahal': 'Jaipur',
  'charminar': 'Hyderabad',
  'victoria terminus': 'Mumbai',
  'christ church': 'Bangalore',
  'rajiv gandhi international airport': 'Hyderabad',
  'meenakshi temple': 'Madurai',
  'minakshi': 'Madurai',
  'vidhana soudha': 'Bangalore',
  'vidhan soudha': 'Bangalore',
  'vidhan bhavan': 'Bangalore',
  'bangalore palace': 'Bangalore',
  'cubbon park': 'Bangalore',
  'lal bagh': 'Bangalore'
}

export default function PostsTable({ onViewOnMap }) {
  const [posts, setPosts] = useState([])
  const [allPosts, setAllPosts] = useState([]) // Store all posts for client-side filtering
  const [loading, setLoading] = useState(false)
  const [processing, setProcessing] = useState({}) // Track processing state per post
  const [processingType, setProcessingType] = useState({}) // Track which type of processing (ai or full)
  const [batchProcessing, setBatchProcessing] = useState(false)
  const [filter, setFilter] = useState('all')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [duplicateAlerts, setDuplicateAlerts] = useState({})
  const [cityInput, setCityInput] = useState('')
  const [citySuggestions, setCitySuggestions] = useState([])
  const [selectedCity, setSelectedCity] = useState('')
  const [locationCache, setLocationCache] = useState({}) // Cache for AI location lookups
  const [profiles, setProfiles] = useState({}) // Cache for user profiles
  const [showMLNotice, setShowMLNotice] = useState(true) // Show ML backend notice on first load

  // Smart location check using AI - checks if a location belongs to a city
  const checkLocationBelongsToCity = async (location, city) => {
    if (!location || !city) return false
    
    // Create cache key
    const cacheKey = `${location.toLowerCase()}|${city.toLowerCase()}`
    
    // Check cache first
    if (locationCache[cacheKey] !== undefined) {
      return locationCache[cacheKey]
    }

    try {
      // Check if API key is available
      const apiKey = import.meta.env.VITE_GEMINI_API_KEY
      if (!apiKey) {
        console.warn('Gemini API key not configured, skipping AI location check')
        setLocationCache(prev => ({ ...prev, [cacheKey]: false }))
        return false
      }

      // Use the Gemini API to intelligently check if location belongs to city
      const response = await fetch('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + apiKey, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          contents: [{
            parts: [{
              text: `Is the location or landmark "${location}" located in or near the city of "${city}" in India? Answer with only "yes" or "no".`
            }]
          }],
          generationConfig: {
            maxOutputTokens: 10,
            temperature: 0
          }
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.warn('Gemini API error:', response.status, errorText)
        setLocationCache(prev => ({ ...prev, [cacheKey]: false }))
        return false
      }

      const data = await response.json()
      const answer = data?.candidates?.[0]?.content?.parts?.[0]?.text?.toLowerCase() || 'no'
      const result = answer.includes('yes')
      
      // Cache the result
      setLocationCache(prev => ({ ...prev, [cacheKey]: result }))
      
      return result
    } catch (error) {
      console.warn('Error checking location with AI:', error)
      setLocationCache(prev => ({ ...prev, [cacheKey]: false }))
      return false
    }
  }

  async function fetchPosts() {
    setLoading(true)
    try {
      let query = supabase
        .from('posts')
        .select('*')
        .order('created_at', { ascending: false })

      // Filter by status
      if (filter === 'manual_review') {
        query = query.eq('status', 'rejected')
      } else if (filter === 'urgent') {
        query = query.eq('status', 'urgent')
      } else if (filter === 'unprocessed') {
        query = query.eq('ai_processed', false)
      } else if (filter === 'filtered') {
        query = query.neq('status', 'rejected')
      } else if (filter === 'dispatched') {
        query = query.in('dispatch_status', ['assigned', 'in-progress'])
      } else if (filter === 'resolved') {
        query = query.eq('dispatch_status', 'resolved')
      } else if (filter !== 'all') {
        query = query.eq('status', filter)
      }

      // Apply date filters
      if (startDate) {
        query = query.gte('created_at', startDate + 'T00:00:00')
      }
      if (endDate) {
        query = query.lte('created_at', endDate + 'T23:59:59')
      }

      // Note: Flood filtering is disabled temporarily
      // When OpenAI quota is available, uncomment this to filter non-flood images:
      // if (filter !== 'unprocessed' && filter !== 'all' && filter !== 'manual_review') {
      //   query = query.or('ai_processed.eq.false,disaster_type.eq.flood,disaster_type.is.null')
      // }

      const { data, error } = await query
      if (error) throw error
      const postsData = data ?? []
      setAllPosts(postsData)
      
      // Fetch profiles for all unique user_ids
      const userIds = [...new Set(postsData.map(p => p.user_id).filter(Boolean))]
      if (userIds.length > 0) {
        const { data: profilesData } = await supabase
          .from('profiles')
          .select('id, username, display_name, avatar_url')
          .in('id', userIds)
        
        const profilesMap = {}
        profilesData?.forEach(p => { profilesMap[p.id] = p })
        setProfiles(profilesMap)
      }
      
      // Apply all filters to the fetched data
      if (selectedCity || startDate || endDate) {
        await applyAllFilters(postsData, selectedCity, startDate, endDate)
      } else {
        setPosts(postsData)
      }
    } catch (err) {
      console.error('Error fetching posts', err)
    } finally {
      setLoading(false)
    }
  }

  // Apply all filters together
  async function applyAllFilters(dataToFilter, city, startD, endD) {
    try {
      let filtered = dataToFilter || []

      // Apply city filter
      if (city && city.length > 0) {
        const cityLower = city.toLowerCase()
        filtered = await Promise.all(filtered.map(async (post) => {
          if (!post) return null
          
          const location = (post.location || '').toLowerCase()
          
          // Handle extracted_locations - ensure it's an array
          const extractedLocsArray = Array.isArray(post.extracted_locations) ? post.extracted_locations : []
          const extractedLocs = extractedLocsArray.map(l => (l || '').toLowerCase()).join(' ')
          
          // Handle location_hints - could be string or array
          let locationHints = ''
          if (Array.isArray(post.location_hints)) {
            locationHints = post.location_hints.map(l => (l || '').toLowerCase()).join(' ')
          } else if (typeof post.location_hints === 'string') {
            locationHints = post.location_hints.toLowerCase()
          }
          
          const caption = (post.caption || '').toLowerCase()
          const ocrText = (post.ocr_text || '').toLowerCase()
          
          const allText = `${location} ${extractedLocs} ${locationHints} ${caption} ${ocrText}`
          
          // Direct city match
          if (allText.includes(cityLower)) {
            return post
          }
          
          // Check for hardcoded landmarks first (fast path)
          for (const [landmark, landmarkCity] of Object.entries(LANDMARKS_TO_CITY)) {
            if (landmarkCity.toLowerCase() === cityLower && allText.includes(landmark)) {
              return post
            }
          }
          
          // Smart AI check for any location that might belong to this city
          // Extract potential locations (words capitalized or common landmark patterns)
          const potentialLocations = [location, ...extractedLocsArray, locationHints]
            .filter(l => l && l.trim().length > 0 && l.trim().split(' ').length <= 4)
          
          for (const potentialLocation of potentialLocations) {
            if (potentialLocation && potentialLocation.trim()) {
              const belongs = await checkLocationBelongsToCity(potentialLocation.trim(), city)
              if (belongs) {
                return post
              }
            }
          }
          
          return null
        }))
        
        filtered = filtered.filter(p => p !== null)
      }

      // Apply date filters
      if (startD) {
        try {
          const startDateObj = new Date(startD + 'T00:00:00')
          filtered = filtered.filter(p => p && new Date(p.created_at) >= startDateObj)
        } catch (e) {
          console.error('Start date filter error:', e)
        }
      }
      if (endD) {
        try {
          const endDateObj = new Date(endD + 'T23:59:59')
          filtered = filtered.filter(p => p && new Date(p.created_at) <= endDateObj)
        } catch (e) {
          console.error('End date filter error:', e)
        }
      }

      setPosts(filtered)
    } catch (err) {
      console.error('Error applying filters:', err)
      setPosts(dataToFilter || [])
    }
  }

  // Handle city input and show suggestions
  function handleCityInput(value) {
    setCityInput(value)
    
    if (value.length === 0) {
      setCitySuggestions([])
      return
    }

    const lowercase = value.toLowerCase()
    const suggestions = INDIAN_CITIES.filter(city =>
      city.toLowerCase().startsWith(lowercase)
    ).slice(0, 8) // Show max 8 suggestions

    setCitySuggestions(suggestions)
  }

  // Select a city from suggestions
  async function selectCity(city) {
    setCityInput('')
    setCitySuggestions([])
    setSelectedCity(city)
    // Apply filter immediately with current data
    const dataToFilter = allPosts && allPosts.length > 0 ? allPosts : posts
    await applyAllFilters(dataToFilter, city, startDate, endDate)
  }

  // Clear city filter
  async function clearCityFilter() {
    setSelectedCity('')
    setCityInput('')
    setCitySuggestions([])
    await applyAllFilters(allPosts && allPosts.length > 0 ? allPosts : posts, '', startDate, endDate)
  }

  // Apply city filter button handler
  async function handleApplyCityFilter() {
    console.log('Apply filter clicked. selectedCity:', selectedCity, 'allPosts length:', allPosts.length, 'posts length:', posts.length)
    const dataToFilter = allPosts && allPosts.length > 0 ? allPosts : posts
    console.log('Data to filter:', dataToFilter.length)
    await applyAllFilters(dataToFilter, selectedCity, startDate, endDate)
  }

  useEffect(() => {
    fetchPosts()
  }, [filter])

  useEffect(() => {
    // Initial fetch when component mounts
    fetchPosts()
  }, [])

  useEffect(() => {
    // Re-apply filters when date or city changes
    const applyFilters = async () => {
      const dataToFilter = allPosts && allPosts.length > 0 ? allPosts : posts
      await applyAllFilters(dataToFilter, selectedCity, startDate, endDate)
    }
    applyFilters()
  }, [selectedCity, startDate, endDate])

  async function updateStatus(id, newStatus) {
    try {
      // Use ML backend API to bypass RLS restrictions
      await mlApi.updateStatus(id, newStatus)
      fetchPosts()
    } catch (err) {
      console.error('Error updating status', err)
      alert('Failed to update status: ' + err.message)
    }
  }

  async function processWithAI(postId, imageUrl, skipDupCheck = false) {
    setProcessing(prev => ({ ...prev, [postId]: true }))
    setDuplicateAlerts(prev => ({ ...prev, [postId]: null }))
    try {
      // Check for duplicates first (unless skipped)
      if (!skipDupCheck && imageUrl) {
        const dupCheck = await mlApi.checkDuplicate(imageUrl, 2)
        if (dupCheck.is_duplicate && dupCheck.existing_post) {
          setDuplicateAlerts(prev => ({
            ...prev,
            [postId]: {
              message: dupCheck.message,
              existingPost: dupCheck.existing_post,
              processType: 'ai' // Track which button was clicked
            }
          }))
          setProcessing(prev => ({ ...prev, [postId]: false }))
          return
        }
      }
      
      const result = await mlApi.processPost(postId)
      console.log('AI Processing result:', result)
      fetchPosts() // Refresh to show updated data
    } catch (err) {
      console.error('AI Processing failed:', err)
      alert('AI Processing failed: ' + err.message)
    } finally {
      setProcessing(prev => ({ ...prev, [postId]: false }))
    }
  }

  async function processAllWithAI() {
    setBatchProcessing(true)
    try {
      const result = await mlApi.processAllPending()
      console.log('Batch processing result:', result)
      alert(`Processed ${result.total_processed} posts`)
      fetchPosts()
    } catch (err) {
      console.error('Batch processing failed:', err)
      alert('Batch processing failed: ' + err.message)
    } finally {
      setBatchProcessing(false)
    }
  }

  function getBadgeClass(status) {
    switch (status) {
      case 'verified':
        return 'badge-verified'
      case 'rejected':
        return 'badge-rejected'
      case 'urgent':
        return 'bg-red-600 text-white'
      default:
        return 'badge-pending'
    }
  }

  function getSeverityColor(severity) {
    switch (severity) {
      case 'critical': return 'text-red-600'
      case 'high': return 'text-orange-600'
      case 'medium': return 'text-yellow-600'
      case 'low': return 'text-green-600'
      default: return 'text-gray-500'
    }
  }

  return (
    <div>
      {/* ML Backend Notice Dialog */}
      {showMLNotice && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-bold text-gray-900">ML Backend Notice</h3>
            </div>
            <p className="text-gray-600 mb-4">
              The ML backend on Google Cloud Run may take some time to connect with the frontend on first load.
            </p>
            <p className="text-gray-600 mb-6">
              <strong>Please try 2-3 times</strong> if the AI analysis doesn't respond immediately. The service needs to "wake up" after being idle.
            </p>
            <button
              onClick={() => setShowMLNotice(false)}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
            >
              Got it!
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Disaster Reports</h1>
        <div className="flex gap-2">
          <button
            onClick={processAllWithAI}
            disabled={batchProcessing}
            className="px-4 py-2 bg-purple-600 text-white rounded flex items-center gap-2 hover:bg-purple-700 disabled:opacity-60"
          >
            <Brain className={`w-4 h-4 ${batchProcessing ? 'animate-pulse' : ''}`} />
            {batchProcessing ? 'Processing...' : 'AI Process All Pending'}
          </button>
          <button
            onClick={fetchPosts}
            disabled={loading}
            className="btn btn-primary flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-4">
        {[
          { id: 'all', label: 'All Reports' },
          { id: 'filtered', label: 'Filtered Reports' },
          { id: 'urgent', label: 'Urgent' },
          { id: 'verified', label: 'Verified' },
          { id: 'pending', label: 'Pending' },
          { id: 'unprocessed', label: 'Unprocessed' },
          { id: 'dispatched', label: 'Dispatched' },
          { id: 'resolved', label: 'Resolved' },
          { id: 'manual_review', label: 'Manual Review' }
        ].map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-3 py-1 rounded text-sm font-medium ${filter === f.id
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Date Filter */}
      <div className="flex gap-4 mb-4 items-center bg-gray-50 p-3 rounded-lg">
        <span className="text-sm font-medium text-gray-600">Date Filter:</span>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="px-3 py-1 border rounded text-sm"
          />
          <span className="text-gray-400">to</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="px-3 py-1 border rounded text-sm"
          />
        </div>
        <button
          onClick={() => { setStartDate(''); setEndDate(''); }}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Clear
        </button>
      </div>

      {/* City Filter */}
      <div className="flex gap-4 mb-4 items-center bg-blue-50 p-3 rounded-lg flex-wrap">
        <span className="text-sm font-medium text-gray-600">City Filter:</span>
        <div className="relative flex-1 min-w-xs">
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Search Indian cities..."
              value={cityInput}
              onChange={(e) => handleCityInput(e.target.value)}
              onFocus={(e) => {
                if (e.target.value.length > 0) {
                  handleCityInput(e.target.value)
                }
              }}
              className="w-full px-3 py-1 border rounded text-sm"
            />
            {citySuggestions.length === 0 && selectedCity && (
              <button
                onClick={clearCityFilter}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
          
          {/* Autocomplete suggestions */}
          {citySuggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-white border rounded shadow-lg z-10">
              {citySuggestions.map((city) => (
                <button
                  key={city}
                  onClick={() => selectCity(city)}
                  className="w-full text-left px-3 py-2 hover:bg-blue-100 text-sm border-b last:border-b-0"
                >
                  <MapPin className="w-3 h-3 inline mr-2 text-blue-600" />
                  {city}
                </button>
              ))}
            </div>
          )}
        </div>
        
        {selectedCity && (
          <>
            <div className="text-sm">
              <span className="bg-blue-200 text-blue-800 px-2 py-1 rounded">
                {selectedCity}
              </span>
            </div>
            <button
              onClick={handleApplyCityFilter}
              className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
            >
              Apply Filter
            </button>
            <button
              onClick={clearCityFilter}
              className="px-3 py-1 bg-gray-300 text-gray-700 rounded text-sm hover:bg-gray-400"
            >
              Clear
            </button>
          </>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        <div className="card text-center">
          <div className="text-3xl font-bold text-blue-600">{posts.length}</div>
          <div className="text-sm text-gray-500">Visible Posts</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-yellow-600">
            {posts.filter((p) => p.status === 'pending').length}
          </div>
          <div className="text-sm text-gray-500">Pending</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-red-600">
            {posts.filter((p) => p.status === 'urgent').length}
          </div>
          <div className="text-sm text-gray-500">Urgent</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-green-600">
            {posts.filter((p) => p.status === 'verified').length}
          </div>
          <div className="text-sm text-gray-500">Verified</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-gray-600">
            {posts.filter((p) => p.status === 'rejected').length}
          </div>
          <div className="text-sm text-gray-500">Manual Review</div>
        </div>
      </div>

      {/* Loading */}
      {loading && <div className="text-center text-gray-500 py-8">Loading posts...</div>}

      {/* Posts Grid */}
      {!loading && posts.length === 0 && (
        <div className="text-center text-gray-500 py-8">No posts found</div>
      )}

      <div className="grid gap-4">
        {posts.map((post) => (
          <div key={post.id} className={`card flex gap-4 ${post.status === 'urgent' ? 'border-2 border-red-500' : ''}`}>
            {/* Media (Image or Video) */}
            {post.image_url && (
              <div className="flex-shrink-0">
                {post.media_type === 'video' ? (
                  <video
                    src={post.image_url}
                    className="w-32 h-32 object-cover rounded"
                    controls
                    muted
                  />
                ) : (
                  <img
                    src={post.image_url}
                    alt="Report"
                    className="w-32 h-32 object-cover rounded"
                  />
                )}
              </div>
            )}

            {/* Content */}
            <div className="flex-1">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`badge ${getBadgeClass(post.status)}`}>
                    {post.status}
                  </span>
                  {post.disaster_type && post.disaster_type !== 'unknown' && (
                    <span className="badge bg-blue-100 text-blue-800">
                      {post.disaster_type}
                    </span>
                  )}
                  {post.severity && (
                    <span className={`text-xs font-medium ${getSeverityColor(post.severity)}`}>
                      {post.severity}
                    </span>
                  )}
                  {post.urgency_score > 0 && (
                    <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                      Urgency: {post.urgency_score}/10
                    </span>
                  )}
                  {post.image_hash && (
                    <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded" title="Image fingerprinted for deduplication">
                      🔍 Fingerprinted
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(post.created_at).toLocaleString()}
                </div>
              </div>

              <p className="mt-2 text-gray-700">{post.caption || 'No caption'}</p>

              {/* Resolution Notes - show when resolved */}
              {post.dispatch_status === 'resolved' && post.resolution_notes && (
                <div className="mt-2 p-2 bg-green-50 rounded text-sm border border-green-200">
                  <div className="flex items-center gap-1 text-green-700 font-medium">
                    <CheckCircle className="w-4 h-4" />
                    Resolution Notes
                  </div>
                  <p className="text-gray-700 mt-1">{post.resolution_notes}</p>
                </div>
              )}

              {/* AI Analysis Results */}
              {post.ai_processed && (
                <div className="mt-2 p-2 bg-purple-50 rounded text-sm">
                  <div className="flex items-center gap-1 text-purple-700 font-medium">
                    <Brain className="w-3 h-3" />
                    AI Analysis
                  </div>
                  {post.ai_description && (
                    <p className="text-gray-600 mt-1">{post.ai_description}</p>
                  )}
                  {post.detected_elements && post.detected_elements.length > 0 && (
                    <p className="text-gray-500 text-xs mt-1">
                      Detected: {post.detected_elements.join(', ')}
                    </p>
                  )}
                  {post.location_hints && (
                    <p className="text-gray-500 text-xs flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {post.location_hints}
                    </p>
                  )}

                  {/* OCR Extracted Text */}
                  {post.ocr_text && (
                    <div className="mt-2 p-2 bg-blue-50 rounded">
                      <span className="text-xs font-medium text-blue-700">📝 OCR Text:</span>
                      <p className="text-gray-600 text-xs mt-1">{post.ocr_text}</p>
                    </div>
                  )}

                  {/* Geolocation Info */}
                  {post.inferred_latitude && post.inferred_longitude && (
                    <div className="mt-2 p-2 bg-green-50 rounded">
                      <span className="text-xs font-medium text-green-700">📍 Inferred Location:</span>
                      <div className="text-xs text-gray-600 mt-1">
                        <p>Coordinates: ({post.inferred_latitude.toFixed(4)}, {post.inferred_longitude.toFixed(4)})</p>
                        {post.location_confidence && (
                          <p>Confidence: {(post.location_confidence * 100).toFixed(0)}%</p>
                        )}
                        {post.location_method && (
                          <p>Method: {post.location_method}</p>
                        )}
                        {post.scene_type && (
                          <p>Scene: {post.scene_type}</p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Extracted Locations */}
                  {post.extracted_locations && post.extracted_locations.length > 0 && (
                    <p className="text-gray-500 text-xs mt-1">
                      Locations mentioned: {post.extracted_locations.join(', ')}
                    </p>
                  )}
                </div>
              )}

              <div className="mt-2 text-xs text-gray-500 flex items-center gap-1">
                <User className="w-3 h-3" />
                {profiles[post.user_id]?.display_name || profiles[post.user_id]?.username || 'Anonymous'}
                {profiles[post.user_id]?.username && (
                  <span className="text-gray-400">@{profiles[post.user_id].username}</span>
                )}
              </div>

              {/* Actions */}
              <div className="mt-3 flex flex-wrap gap-2">
                {/* AI Process Buttons */}
                {!post.ai_processed && (
                  <>
                    <button
                      onClick={() => {
                        setProcessingType(prev => ({ ...prev, [post.id]: 'ai' }))
                        processWithAI(post.id, post.image_url)
                      }}
                      disabled={processing[post.id]}
                      className="px-3 py-1 bg-purple-600 text-white rounded text-sm flex items-center gap-1 hover:bg-purple-700 disabled:opacity-60"
                    >
                      <Zap className={`w-4 h-4 ${processing[post.id] ? 'animate-pulse' : ''}`} />
                      {processing[post.id] && processingType[post.id] === 'ai' ? 'Analyzing...' : 'AI Analyze'}
                    </button>
                    <button
                      onClick={async () => {
                        setProcessing(prev => ({ ...prev, [post.id]: true }))
                        setProcessingType(prev => ({ ...prev, [post.id]: 'full' }))
                        setDuplicateAlerts(prev => ({ ...prev, [post.id]: null }))
                        try {
                          // First check for duplicates
                          if (post.image_url) {
                            const dupCheck = await mlApi.checkDuplicate(post.image_url, 2)
                            if (dupCheck.is_duplicate && dupCheck.existing_post) {
                              // Found a duplicate - show alert instead of processing
                              setDuplicateAlerts(prev => ({
                                ...prev,
                                [post.id]: {
                                  message: dupCheck.message,
                                  existingPost: dupCheck.existing_post,
                                  processType: 'full' // Track which button was clicked
                                }
                              }))
                              setProcessing(prev => ({ ...prev, [post.id]: false }))
                              return
                            }
                          }
                          // No duplicate found, proceed with processing
                          await mlApi.processPostFull(post.id)
                          fetchPosts()
                        } catch (err) {
                          alert('Full processing failed: ' + err.message)
                        }
                        setProcessing(prev => ({ ...prev, [post.id]: false }))
                      }}
                      disabled={processing[post.id]}
                      className="px-3 py-1 bg-green-600 text-white rounded text-sm flex items-center gap-1 hover:bg-green-700 disabled:opacity-60"
                    >
                      <MapPin className={`w-4 h-4 ${processing[post.id] && processingType[post.id] === 'full' ? 'animate-spin' : ''}`} />
                      {processing[post.id] && processingType[post.id] === 'full' ? 'Processing...' : 'Full AI + Geo'}
                    </button>
                  </>
                )}
                
                {/* Processing Notice - shows below buttons when Full AI + Geo is running */}
                {processing[post.id] && processingType[post.id] === 'full' && (
                  <div className="w-full mt-2 p-3 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center gap-2 text-green-700">
                      <div className="animate-spin w-4 h-4 border-2 border-green-600 border-t-transparent rounded-full"></div>
                      <span className="text-sm font-medium">Processing with AI + Geo...</span>
                    </div>
                    <p className="text-sm text-green-600 mt-1">⏱️ This may take up to 2 minutes. Please wait while AI analyzes the image and extracts location.</p>
                  </div>
                )}

                {/* Duplicate Alert Display */}
                {duplicateAlerts[post.id] && (
                  <div className="w-full mt-2 p-3 bg-yellow-50 border border-yellow-300 rounded-lg">
                    <div className="flex items-start gap-2">
                      <Copy className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <p className="font-semibold text-yellow-800">Area Already Reported</p>
                        <p className="text-sm text-yellow-700">{duplicateAlerts[post.id].message}</p>
                        {duplicateAlerts[post.id].existingPost && (
                          <div className="mt-2 text-xs text-yellow-600">
                            <p>Original Status: <strong>{duplicateAlerts[post.id].existingPost.status}</strong></p>
                            {duplicateAlerts[post.id].existingPost.disaster_type && (
                              <p>Type: {duplicateAlerts[post.id].existingPost.disaster_type}</p>
                            )}
                          </div>
                        )}
                        <div className="mt-2 flex gap-2">
                          <button
                            onClick={() => setDuplicateAlerts(prev => ({ ...prev, [post.id]: null }))}
                            className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                          >
                            Dismiss
                          </button>
                          <button
                            onClick={async () => {
                              const processType = duplicateAlerts[post.id]?.processType
                              setDuplicateAlerts(prev => ({ ...prev, [post.id]: null }))
                              setProcessing(prev => ({ ...prev, [post.id]: true }))
                              try {
                                if (processType === 'ai') {
                                  await mlApi.processPost(post.id)
                                } else {
                                  await mlApi.processPostFull(post.id)
                                }
                                fetchPosts()
                              } catch (err) {
                                alert('Processing failed: ' + err.message)
                              }
                              setProcessing(prev => ({ ...prev, [post.id]: false }))
                            }}
                            className="text-xs px-2 py-1 bg-orange-500 text-white rounded hover:bg-orange-600"
                          >
                            Process Anyway
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {post.status !== 'verified' && (
                  <button
                    onClick={() => updateStatus(post.id, 'verified')}
                    className="btn btn-success text-sm flex items-center gap-1"
                  >
                    <CheckCircle className="w-4 h-4" />
                    Verify
                  </button>
                )}
                {post.status !== 'rejected' && (
                  <button
                    onClick={() => updateStatus(post.id, 'rejected')}
                    className="btn btn-danger text-sm flex items-center gap-1"
                  >
                    <XCircle className="w-4 h-4" />
                    Reject
                  </button>
                )}
                {post.status !== 'pending' && (
                  <button
                    onClick={async () => {
                      await updateStatus(post.id, 'pending')
                      await mlApi.resetAI(post.id)
                      fetchPosts()
                    }}
                    className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
                  >
                    Reset to Pending
                  </button>
                )}
                {/* View on Map button - only show if post has coordinates */}
                {post.inferred_latitude && post.inferred_longitude && onViewOnMap && (
                  <button
                    onClick={() => onViewOnMap(post)}
                    className="px-3 py-1 bg-blue-600 text-white rounded text-sm flex items-center gap-1 hover:bg-blue-700"
                  >
                    <Navigation className="w-4 h-4" />
                    View on Map
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
