import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap, Tooltip } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import { supabase } from '../supabaseClient'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Truck } from 'lucide-react'

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

// Custom marker icons by severity
const createIcon = (color) => new L.Icon({
  iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
})

const icons = {
  urgent: createIcon('red'),
  verified: createIcon('orange'),
  pending: createIcon('yellow'),
  default: createIcon('blue')
}

// Component to fit map bounds to markers
function FitBounds({ posts }) {
  const map = useMap()

  useEffect(() => {
    if (posts.length > 0) {
      const bounds = posts.map(p => [p.inferred_latitude, p.inferred_longitude])
      map.fitBounds(bounds, { padding: [50, 50] })
    }
  }, [posts, map])

  return null
}

// Component to center map on a specific post
function CenterOnPost({ post }) {
  const map = useMap()

  useEffect(() => {
    if (post && post.inferred_latitude && post.inferred_longitude) {
      map.setView([post.inferred_latitude, post.inferred_longitude], 15)
    }
  }, [post, map])

  return null
}

// Extract needs/requirements from caption AND AI analysis
function extractNeeds(post) {
  const needs = []
  const caption = (post.caption || '').toLowerCase()
  const aiDesc = (post.ai_description || '').toLowerCase()
  const detected = (post.detected_elements || []).map(e => e.toLowerCase())
  const combined = caption + ' ' + aiDesc + ' ' + detected.join(' ')
  
  // Food needs
  if (combined.includes('food required') || combined.includes('food needed') || combined.includes('need food') || combined.includes('hungry')) {
    needs.push('🍲 Food Required')
  }
  // Water needs
  if (combined.includes('water required') || combined.includes('water needed') || combined.includes('need water') || combined.includes('drinking water')) {
    needs.push('💧 Water Required')
  }
  // Medical help
  if (combined.includes('medical') || combined.includes('medicine') || combined.includes('doctor') || combined.includes('injured') || combined.includes('injury')) {
    needs.push('🏥 Medical Help')
  }
  // Rescue needed - from AI detection
  if (combined.includes('rescue') || combined.includes('trapped') || combined.includes('stuck') || 
      combined.includes('people wading') || combined.includes('stranded') || combined.includes('marooned')) {
    needs.push('🆘 Rescue Needed')
  }
  // Shelter
  if (combined.includes('shelter') || combined.includes('housing') || combined.includes('homeless')) {
    needs.push('🏠 Shelter Needed')
  }
  // Power outage
  if (combined.includes('electricity') || combined.includes('power') || combined.includes('blackout')) {
    needs.push('⚡ Power Outage')
  }
  // Vehicles submerged - transportation issue
  if (combined.includes('submerged') || combined.includes('vehicles') && combined.includes('water')) {
    needs.push('🚗 Vehicles Affected')
  }
  // People in danger
  if (detected.includes('people wading') || detected.includes('people') && combined.includes('flood')) {
    needs.push('👥 People in Danger')
  }
  
  return needs.length > 0 ? needs : null
}

export default function MapView({ selectedPost, onClearSelection, onDispatchTeam }) {
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  // Default center (Bangalore, India)
  const defaultCenter = [12.9716, 77.5946]
  const defaultZoom = 11

  useEffect(() => {
    fetchGeolocatedPosts()
  }, [filter])

  async function fetchGeolocatedPosts() {
    setLoading(true)
    try {
      let query = supabase
        .from('posts')
        .select('*')
        .not('inferred_latitude', 'is', null)
        .not('inferred_longitude', 'is', null)
        .order('created_at', { ascending: false })

      // Apply status filter
      if (filter !== 'all') {
        query = query.eq('status', filter)
      }

      const { data, error } = await query.limit(100)

      if (error) {
        console.error('Error fetching posts:', error)
      } else {
        setPosts(data || [])
      }
    } catch (err) {
      console.error('Failed to fetch posts:', err)
    }
    setLoading(false)
  }

  function getIcon(status) {
    return icons[status] || icons.default
  }

  function formatDate(dateStr) {
    if (!dateStr) return 'N/A'
    return new Date(dateStr).toLocaleString()
  }

  function getSeverityBadge(severity) {
    const colors = {
      critical: 'bg-red-600',
      high: 'bg-orange-500',
      medium: 'bg-yellow-500',
      low: 'bg-green-500'
    }
    return colors[severity?.toLowerCase()] || 'bg-gray-500'
  }

  return (
    <div className="flex flex-col h-full">
      {/* Selected Post Action Banner */}
      {selectedPost && (
        <div className="mb-4 p-4 bg-gradient-to-r from-blue-600/30 to-orange-600/30 border border-blue-500 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
              <div>
                <p className="text-white font-semibold text-lg">
                  📍 {selectedPost.disaster_type || 'Disaster'} - {selectedPost.extracted_locations?.[0] || 'Location'}
                </p>
                <p className="text-gray-300 text-sm">
                  Coordinates: ({selectedPost.inferred_latitude?.toFixed(4)}, {selectedPost.inferred_longitude?.toFixed(4)})
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* Dispatch Team Button */}
              {(selectedPost.status === 'urgent' || selectedPost.status === 'verified') && onDispatchTeam && (
                <button
                  onClick={() => onDispatchTeam(selectedPost)}
                  className="px-4 py-2 bg-orange-600 text-white rounded-lg flex items-center gap-2 hover:bg-orange-700 font-medium"
                >
                  <Truck className="w-5 h-5" />
                  Dispatch Team
                </button>
              )}
              <button
                onClick={onClearSelection}
                className="text-gray-300 hover:text-white text-sm px-3 py-2 bg-gray-700 rounded-lg hover:bg-gray-600"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header with filters */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">🗺️ Disaster Map</h2>
          <p className="text-gray-400 text-sm">
            {loading ? 'Loading...' : `${posts.length} geolocated reports`}
          </p>
        </div>

        <div className="flex gap-2">
          {['all', 'urgent', 'verified', 'pending'].map(status => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${filter === status
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
          <button
            onClick={fetchGeolocatedPosts}
            className="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-sm hover:bg-gray-600"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Map container */}
      <div className="flex-1 rounded-xl overflow-hidden border border-gray-700" style={{ minHeight: '500px' }}>
        <MapContainer
          center={selectedPost ? [selectedPost.inferred_latitude, selectedPost.inferred_longitude] : defaultCenter}
          zoom={selectedPost ? 15 : defaultZoom}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Center on selected post if present */}
          {selectedPost && <CenterOnPost post={selectedPost} />}
          
          {/* Fit bounds only if no selected post */}
          {!selectedPost && posts.length > 0 && <FitBounds posts={posts} />}

          <MarkerClusterGroup chunkedLoading>
            {posts.map(post => {
              const needs = extractNeeds(post)
              const isSelected = selectedPost && selectedPost.id === post.id
              
              return (
              <Marker
                key={post.id}
                position={[post.inferred_latitude, post.inferred_longitude]}
                icon={getIcon(post.status)}
              >
                {/* Permanent tooltip above marker showing needs */}
                {needs && (
                  <Tooltip 
                    permanent={isSelected} 
                    direction="top" 
                    offset={[0, -35]}
                    className="needs-tooltip"
                  >
                    <div className="text-xs font-medium text-center">
                      {needs.slice(0, 3).join(' • ')}
                    </div>
                  </Tooltip>
                )}
                <Popup>
                  <div className="max-w-xs">
                    {/* Needs/Requirements Label */}
                    {needs && (
                      <div className="mb-2 p-2 bg-yellow-100 rounded-lg border border-yellow-300">
                        <p className="font-bold text-yellow-800 text-xs">⚠️ Detected Needs:</p>
                        {needs.map((need, i) => (
                          <span key={i} className="inline-block text-xs bg-yellow-200 text-yellow-800 px-2 py-0.5 rounded mr-1 mt-1">{need}</span>
                        ))}
                      </div>
                    )}
                    
                    {/* Image */}
                    {post.image_url && (
                      <img
                        src={post.image_url}
                        alt="Disaster"
                        className="w-full h-24 object-cover rounded-lg mb-2"
                      />
                    )}

                    {/* Disaster type and severity */}
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-bold text-gray-800">
                        {post.disaster_type || 'Unknown'}
                      </span>
                      {post.severity && (
                        <span className={`px-2 py-0.5 rounded text-xs text-white ${getSeverityBadge(post.severity)}`}>
                          {post.severity}
                        </span>
                      )}
                    </div>

                    {/* Caption */}
                    {post.caption && (
                      <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                        {post.caption}
                      </p>
                    )}

                    {/* OCR Text */}
                    {post.ocr_text && (
                      <p className="text-xs text-gray-500 mb-2 italic">
                        📝 OCR: {post.ocr_text.substring(0, 50)}...
                      </p>
                    )}

                    {/* Location confidence */}
                    {post.location_confidence && (
                      <p className="text-xs text-gray-500 mb-1">
                        📍 Confidence: {(post.location_confidence * 100).toFixed(0)}%
                        {post.location_method && ` (${post.location_method})`}
                      </p>
                    )}

                    {/* Timestamp */}
                    <p className="text-xs text-gray-400 mb-2">
                      {formatDate(post.created_at)}
                    </p>

                    <a
                      href={`https://www.google.com/maps?q=${post.inferred_latitude},${post.inferred_longitude}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block w-full text-center py-1.5 px-3 bg-blue-600 hover:bg-blue-700 !text-white text-xs font-medium rounded transition-colors"
                    >
                      🌏 View on Google Maps
                    </a>
                  </div>
                </Popup>
              </Marker>
              )
            })}
          </MarkerClusterGroup>
        </MapContainer>
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center gap-6 text-sm text-gray-400">
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-red-500"></span> Urgent
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-orange-500"></span> Verified
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-yellow-500"></span> Pending
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-blue-500"></span> Other
        </div>
      </div>
    </div>
  )
}
