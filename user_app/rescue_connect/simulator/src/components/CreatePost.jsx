import { useState, useRef } from 'react'
import { supabase } from '../supabaseClient'
import mlApi from '../lib/mlApi'
import { 
  X, 
  Image, 
  MapPin, 
  AlertTriangle, 
  Camera,
  ChevronDown,
  Loader2,
  Video,
  Play,
  CheckCircle,
  Info
} from 'lucide-react'

const disasterTypes = [
  { id: 'flood', label: 'Flood', emoji: '🌊' },
  { id: 'fire', label: 'Fire', emoji: '🔥' },
  { id: 'earthquake', label: 'Earthquake', emoji: '🌍' },
  { id: 'storm', label: 'Storm/Cyclone', emoji: '🌀' },
  { id: 'accident', label: 'Accident', emoji: '🚗' },
  { id: 'collapse', label: 'Building Collapse', emoji: '🏚️' },
  { id: 'medical', label: 'Medical Emergency', emoji: '🏥' },
  { id: 'other', label: 'Other', emoji: '⚠️' },
]

export default function CreatePost({ user, profile, onPosted, onClose }) {
  const [caption, setCaption] = useState('')
  const [location, setLocation] = useState('')
  const [disasterType, setDisasterType] = useState('')
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [mediaType, setMediaType] = useState('image')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showTypeDropdown, setShowTypeDropdown] = useState(false)
  const [duplicateInfo, setDuplicateInfo] = useState(null) // For duplicate detection
  const [checkingDuplicate, setCheckingDuplicate] = useState(false)
  const fileInputRef = useRef(null)

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
      setDuplicateInfo(null) // Reset duplicate info when new file selected
      
      // Check if video or image
      const isVideo = selectedFile.type.startsWith('video/')
      setMediaType(isVideo ? 'video' : 'image')
      
      if (isVideo) {
        // For video, create object URL for preview
        setPreview(URL.createObjectURL(selectedFile))
      } else {
        // For image, use FileReader
        const reader = new FileReader()
        reader.onload = (e) => setPreview(e.target.result)
        reader.readAsDataURL(selectedFile)
      }
    }
  }

  const handleGetLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation(`${position.coords.latitude.toFixed(4)}, ${position.coords.longitude.toFixed(4)}`)
        },
        () => {
          setLocation('Location unavailable')
        }
      )
    }
  }

  async function handleUpload(e) {
    e.preventDefault()
    setError(null)
    setDuplicateInfo(null)
    
    if (!file) {
      setError('Please select an image to upload')
      return
    }

    setLoading(true)
    try {
      const fileExt = file.name.split('.').pop()
      const filePath = `${user?.id ?? 'anon'}/${Date.now()}.${fileExt}`

      // First upload the file to get the URL
      const { error: uploadError } = await supabase.storage
        .from('disaster_images')
        .upload(filePath, file, { cacheControl: '3600', upsert: false })

      if (uploadError) throw uploadError

      const { data: publicData } = supabase.storage
        .from('disaster_images')
        .getPublicUrl(filePath)

      const imageUrl = publicData?.publicUrl ?? ''

      // Check for duplicates (only for images, not videos)
      if (mediaType === 'image') {
        setCheckingDuplicate(true)
        const dupCheck = await mlApi.checkDuplicate(imageUrl, 2)
        setCheckingDuplicate(false)
        
        if (dupCheck.is_duplicate) {
          // Show duplicate info but still allow posting if user confirms
          setDuplicateInfo({
            message: dupCheck.message,
            existingPost: dupCheck.existing_post,
            imageUrl: imageUrl,
            filePath: filePath
          })
          setLoading(false)
          return // Stop here, user can click "Post Anyway" to continue
        }
      }

      // If not duplicate, proceed with inserting
      await insertPost(imageUrl)

    } catch (err) {
      setError(err.message ?? String(err))
      setLoading(false)
    }
  }

  async function insertPost(imageUrl) {
    try {
      // Build insert object - only include location if provided
      const insertData = {
        user_id: user?.id ?? null,
        image_url: imageUrl,
        caption: `${disasterType ? `[${disasterTypes.find(d => d.id === disasterType)?.label}] ` : ''}${caption}`,
        status: 'pending',
        media_type: mediaType,
      }

      // Only add location if user entered it
      if (location && location.trim() !== '' && location !== 'Location unavailable') {
        insertData.location = location
      }

      const { error: insertError } = await supabase.from('posts').insert(insertData)

      if (insertError) throw insertError

      onPosted?.()
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setLoading(false)
    }
  }

  async function handlePostAnyway() {
    if (duplicateInfo?.imageUrl) {
      setLoading(true)
      setDuplicateInfo(null)
      await insertPost(duplicateInfo.imageUrl)
    }
  }

  return (
    <div className="bg-gray-900 rounded-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <button 
          onClick={onClose}
          className="text-gray-400 hover:text-white transition-colors"
        >
          <X className="w-6 h-6" />
        </button>
        <h2 className="font-semibold text-lg">New Report</h2>
        <button
          onClick={handleUpload}
          disabled={loading || !file}
          className="text-blue-500 font-semibold disabled:text-gray-600"
        >
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Share'}
        </button>
      </div>

      <form onSubmit={handleUpload} className="p-4 space-y-4 pb-6">
        {/* Media Upload Area */}
        <div 
          onClick={() => fileInputRef.current?.click()}
          className={`relative aspect-square rounded-xl overflow-hidden cursor-pointer ${
            preview ? '' : 'bg-gray-800 border-2 border-dashed border-gray-700 hover:border-gray-600'
          }`}
        >
          {preview ? (
            <>
              {mediaType === 'video' ? (
                <div className="relative w-full h-full">
                  <video 
                    src={preview} 
                    className="w-full h-full object-cover"
                    controls
                  />
                  <div className="absolute top-2 right-2 bg-black/60 px-2 py-1 rounded-full flex items-center gap-1">
                    <Video className="w-3 h-3 text-white" />
                    <span className="text-xs text-white">Video</span>
                  </div>
                </div>
              ) : (
                <img src={preview} alt="Preview" className="w-full h-full object-cover" />
              )}
              <div className="absolute inset-0 bg-black/40 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center">
                <Camera className="w-10 h-10 text-white" />
              </div>
            </>
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
              <div className="flex gap-4">
                <div className="w-14 h-14 rounded-full bg-gray-700 flex items-center justify-center">
                  <Image className="w-6 h-6 text-gray-400" />
                </div>
                <div className="w-14 h-14 rounded-full bg-gray-700 flex items-center justify-center">
                  <Video className="w-6 h-6 text-gray-400" />
                </div>
              </div>
              <div className="text-center">
                <p className="text-gray-300 font-medium">Add Photo or Video</p>
                <p className="text-gray-500 text-sm">Tap to upload disaster media</p>
              </div>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*"
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>

        {/* Disaster Type Selector */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowTypeDropdown(!showTypeDropdown)}
            className="w-full flex items-center justify-between px-4 py-3 bg-gray-800 rounded-xl text-left"
          >
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-orange-500" />
              <span className={disasterType ? 'text-white' : 'text-gray-500'}>
                {disasterType 
                  ? `${disasterTypes.find(d => d.id === disasterType)?.emoji} ${disasterTypes.find(d => d.id === disasterType)?.label}`
                  : 'Select Disaster Type'
                }
              </span>
            </div>
            <ChevronDown className={`w-5 h-5 text-gray-500 transition-transform ${showTypeDropdown ? 'rotate-180' : ''}`} />
          </button>
          
          {showTypeDropdown && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-gray-800 rounded-xl overflow-hidden z-10 border border-gray-700">
              {disasterTypes.map((type) => (
                <button
                  key={type.id}
                  type="button"
                  onClick={() => {
                    setDisasterType(type.id)
                    setShowTypeDropdown(false)
                  }}
                  className={`w-full px-4 py-3 text-left hover:bg-gray-700 transition-colors flex items-center gap-3 ${
                    disasterType === type.id ? 'bg-gray-700' : ''
                  }`}
                >
                  <span className="text-xl">{type.emoji}</span>
                  <span>{type.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Caption */}
        <div className="bg-gray-800 rounded-xl p-4">
          <textarea
            className="w-full bg-transparent text-white placeholder-gray-500 resize-none focus:outline-none"
            placeholder="Describe the situation, severity, people affected, immediate needs..."
            rows={4}
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            maxLength={500}
          />
          <div className="text-right text-xs text-gray-500 mt-2">
            {caption.length}/500
          </div>
        </div>

        {/* Location */}
        <div className="flex items-center gap-2 sm:gap-3 bg-gray-800 rounded-xl p-3 sm:p-4">
          <MapPin className="w-5 h-5 text-red-500 flex-shrink-0" />
          <input
            type="text"
            placeholder="Location (optional)"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="flex-1 min-w-0 bg-transparent text-white placeholder-gray-500 focus:outline-none text-sm sm:text-base"
          />
          <button
            type="button"
            onClick={handleGetLocation}
            className="text-blue-500 text-xs sm:text-sm font-medium hover:text-blue-400 flex-shrink-0 px-2 py-1 bg-blue-500/10 rounded-lg"
          >
            📍 Detect
          </button>
        </div>

        {/* Duplicate Detection Warning */}
        {duplicateInfo && (
          <div className="bg-green-500/20 border border-green-500/50 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <CheckCircle className="w-6 h-6 text-green-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h4 className="font-semibold text-green-400 mb-1">Area Already Reported</h4>
                <p className="text-green-300 text-sm mb-3">{duplicateInfo.message}</p>
                {duplicateInfo.existingPost && (
                  <div className="bg-gray-800/50 rounded-lg p-3 mb-3 text-xs text-gray-400">
                    <p><strong>Status:</strong> {duplicateInfo.existingPost.status}</p>
                    {duplicateInfo.existingPost.disaster_type && (
                      <p><strong>Type:</strong> {duplicateInfo.existingPost.disaster_type}</p>
                    )}
                    {duplicateInfo.existingPost.location && (
                      <p><strong>Location:</strong> {duplicateInfo.existingPost.location}</p>
                    )}
                  </div>
                )}
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setDuplicateInfo(null)
                      setFile(null)
                      setPreview(null)
                    }}
                    className="px-4 py-2 bg-gray-700 text-white text-sm rounded-lg hover:bg-gray-600"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handlePostAnyway}
                    className="px-4 py-2 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600"
                  >
                    Post Anyway (New Update)
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Checking Duplicate Status */}
        {checkingDuplicate && (
          <div className="bg-blue-500/20 border border-blue-500/50 rounded-xl p-4 flex items-center gap-3">
            <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
            <span className="text-blue-300 text-sm">Checking for similar reports...</span>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-red-500/20 border border-red-500/50 rounded-xl p-4 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Submit Button (mobile) */}
        <button
          type="submit"
          disabled={loading || !file || duplicateInfo}
          className="w-full py-4 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-semibold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Posting...
            </>
          ) : (
            <>
              <AlertTriangle className="w-5 h-5" />
              Post Emergency Report
            </>
          )}
        </button>
      </form>
    </div>
  )
}
