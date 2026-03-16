import { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient'
import { Truck, Save, MapPin, X, AlertTriangle, Mail, CheckCircle } from 'lucide-react'
import mlApi from '../lib/mlApi'

// Valid status transitions (matching backend)
const VALID_TRANSITIONS = {
    pending: ['assigned'],
    assigned: ['in-progress', 'pending'],
    'in-progress': ['resolved', 'assigned'],
    resolved: []
}

const STATUS_COLORS = {
    pending: 'bg-gray-100 text-gray-800',
    assigned: 'bg-blue-100 text-blue-800',
    'in-progress': 'bg-yellow-100 text-yellow-800',
    resolved: 'bg-green-100 text-green-800'
}

export default function DispatchView({ selectedPost, onClearSelection }) {
    const [posts, setPosts] = useState([])
    const [loading, setLoading] = useState(false)
    const [edits, setEdits] = useState({})
    const [resolveModal, setResolveModal] = useState(null) // Post being resolved
    const [resolutionNotes, setResolutionNotes] = useState('')
    const [highlightedPostId, setHighlightedPostId] = useState(null)
    const [notificationModal, setNotificationModal] = useState(null) // For showing notification sent confirmation
    const [sendingEmail, setSendingEmail] = useState(false)
    const [profiles, setProfiles] = useState({}) // Cache for user profiles

    useEffect(() => {
        fetchDispatchablePosts()
    }, [])

    // Handle selected post from navigation - auto set to in-progress
    useEffect(() => {
        if (selectedPost && posts.length > 0) {
            const postInList = posts.find(p => p.id === selectedPost.id)
            if (postInList) {
                setHighlightedPostId(selectedPost.id)
                // Auto-set to in-progress if currently pending
                const currentStatus = postInList.dispatch_status || 'pending'
                if (currentStatus === 'pending') {
                    handleEditChange(selectedPost.id, 'dispatch_status', 'assigned')
                }
                // Scroll to the post
                setTimeout(() => {
                    const element = document.getElementById(`dispatch-row-${selectedPost.id}`)
                    if (element) {
                        element.scrollIntoView({ behavior: 'smooth', block: 'center' })
                    }
                }, 100)
            }
        }
    }, [selectedPost, posts])

    async function fetchDispatchablePosts() {
        setLoading(true)
        try {
            // Only fetch urgent/verified posts that are NOT resolved
            const { data, error } = await supabase
                .from('posts')
                .select('*')
                .in('status', ['urgent', 'verified'])
                .neq('dispatch_status', 'resolved')
                .order('created_at', { ascending: false })

            if (error) throw error
            const postsData = data || []
            setPosts(postsData)
            
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
        } catch (err) {
            console.error('Error fetching dispatch posts:', err)
        }
        setLoading(false)
    }

    const handleEditChange = (id, field, value) => {
        setEdits(prev => ({
            ...prev,
            [id]: { ...prev[id], [field]: value }
        }))
    }

    const getNextStatuses = (currentStatus) => {
        const s = currentStatus || 'pending'
        return [s, ...VALID_TRANSITIONS[s] || []]
    }

    const saveDispatchUpdate = async (post) => {
        const changes = edits[post.id]
        if (!changes) return

        const currentStatus = post.dispatch_status || 'pending'
        const newStatus = changes.dispatch_status || currentStatus
        const newTeam = changes.assigned_team !== undefined ? changes.assigned_team : post.assigned_team

        // If transitioning to resolved, show modal for notes
        if (newStatus === 'resolved' && currentStatus !== 'resolved') {
            setResolveModal(post)
            return
        }

        try {
            await mlApi.updateDispatch(post.id, newStatus, newTeam)
            
            // Send email notification to user
            await sendNotificationEmail(post, newStatus, newTeam)
            
            setEdits(prev => { const n = { ...prev }; delete n[post.id]; return n })
            fetchDispatchablePosts()
        } catch (err) {
            alert('Error: ' + err.message)
        }
    }

    // Send notification email to user
    const sendNotificationEmail = async (post, status, team) => {
        setSendingEmail(true)
        try {
            // Get user name from profiles map
            const userName = profiles[post.user_id]?.display_name || profiles[post.user_id]?.username || 'User'
            
            // Call backend to send email
            const response = await fetch(`${import.meta.env.VITE_ML_BACKEND_URL || 'http://localhost:8000'}/send-notification`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    post_id: post.id,
                    user_id: post.user_id,
                    status: status,
                    team_name: team || 'Rescue Team',
                    disaster_type: post.disaster_type || 'Emergency',
                    location: post.extracted_locations?.[0] || post.location || 'your reported location'
                })
            })
            
            if (response.ok) {
                setNotificationModal({
                    userName: userName,
                    status: status,
                    team: team
                })
            }
        } catch (err) {
            console.error('Failed to send notification:', err)
            // Still show confirmation even if email fails
            setNotificationModal({
                userName: profiles[post.user_id]?.display_name || profiles[post.user_id]?.username || 'User',
                status: status,
                team: team,
                emailFailed: true
            })
        }
        setSendingEmail(false)
    }

    const confirmResolve = async () => {
        if (!resolveModal) return
        try {
            await mlApi.updateDispatch(
                resolveModal.id,
                'resolved',
                edits[resolveModal.id]?.assigned_team || resolveModal.assigned_team,
                resolutionNotes
            )
            setResolveModal(null)
            setResolutionNotes('')
            setEdits(prev => { const n = { ...prev }; delete n[resolveModal.id]; return n })
            fetchDispatchablePosts()
        } catch (err) {
            alert('Error: ' + err.message)
        }
    }

    const openInMaps = (post) => {
        if (post.inferred_latitude && post.inferred_longitude) {
            window.open(`https://www.google.com/maps?q=${post.inferred_latitude},${post.inferred_longitude}`, '_blank')
        } else {
            alert('No GPS coordinates available for this report.')
        }
    }

    return (
        <div className="p-6">
            {/* Selected Post Banner */}
            {selectedPost && (
                <div className="mb-4 p-3 bg-orange-100 border border-orange-400 rounded-lg flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse"></div>
                        <div>
                            <p className="text-orange-800 font-medium">
                                Dispatching: {selectedPost.disaster_type || 'Incident'} 
                                {selectedPost.extracted_locations?.[0] && ` at ${selectedPost.extracted_locations[0]}`}
                            </p>
                            <p className="text-orange-600 text-sm">Status auto-set to "Assigned" - enter team name and save</p>
                        </div>
                    </div>
                    <button
                        onClick={() => {
                            setHighlightedPostId(null)
                            onClearSelection?.()
                        }}
                        className="text-orange-700 hover:text-orange-900 text-sm px-3 py-1 bg-orange-200 rounded hover:bg-orange-300"
                    >
                        Clear Selection
                    </button>
                </div>
            )}

            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        <Truck className="w-8 h-8 text-blue-600" />
                        Dispatch Operations
                    </h1>
                    <p className="text-gray-500">Assign teams and track response status for active incidents.</p>
                </div>
                <button onClick={fetchDispatchablePosts} className="btn btn-secondary">Refresh</button>
            </div>

            {loading ? (
                <div className="text-center py-8">Loading operations...</div>
            ) : posts.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-xl shadow">
                    <AlertTriangle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-500">No active incidents require dispatch.</p>
                </div>
            ) : (
                <div className="overflow-x-auto bg-white rounded-xl shadow border border-gray-200">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Disaster Info</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">GPS Status</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Dispatch Status</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assigned Team</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {posts.map((post) => {
                                const draft = edits[post.id] || {}
                                const currentStatus = post.dispatch_status || 'pending'
                                const displayStatus = draft.dispatch_status || currentStatus
                                const currentTeam = draft.assigned_team !== undefined ? draft.assigned_team : (post.assigned_team || '')
                                const hasChanges = Object.keys(draft).length > 0
                                const isHighlighted = highlightedPostId === post.id

                                return (
                                    <tr 
                                        key={post.id} 
                                        id={`dispatch-row-${post.id}`}
                                        className={`hover:bg-gray-50 ${isHighlighted ? 'bg-yellow-50 ring-2 ring-yellow-400' : ''}`}
                                    >
                                        <td className="px-6 py-4">
                                            <div className="flex items-center">
                                                {post.image_url && <img className="h-10 w-10 rounded object-cover mr-3" src={post.image_url} alt="" />}
                                                <div>
                                                    <div className="text-sm font-medium text-gray-900 capitalize">{post.disaster_type || 'Unknown'}</div>
                                                    <div className="text-xs text-gray-500">{new Date(post.created_at).toLocaleDateString()}</div>
                                                    <div className="text-xs text-blue-600">
                                                        {post.profiles?.display_name || post.profiles?.username || 'Anonymous'}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="text-sm text-gray-900 max-w-xs truncate">
                                                {post.extracted_locations?.[0] || post.location || 'Unknown'}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 text-xs rounded-full ${post.inferred_latitude ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                                                {post.inferred_latitude ? 'Has Coordinates' : 'No GPS'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${post.status === 'urgent' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                                                {post.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <select
                                                value={displayStatus}
                                                onChange={(e) => handleEditChange(post.id, 'dispatch_status', e.target.value)}
                                                className={`block w-full px-3 py-2 text-sm border rounded-md ${STATUS_COLORS[displayStatus]}`}
                                            >
                                                {getNextStatuses(currentStatus).map(s => (
                                                    <option key={s} value={s}>{s.replace('-', ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                                                ))}
                                            </select>
                                        </td>
                                        <td className="px-6 py-4">
                                            <input
                                                type="text"
                                                value={currentTeam}
                                                onChange={(e) => handleEditChange(post.id, 'assigned_team', e.target.value)}
                                                placeholder="Enter team name..."
                                                className="w-full px-3 py-2 text-sm border rounded-md focus:ring-blue-500 focus:border-blue-500"
                                            />
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex gap-2">
                                                {hasChanges && (
                                                    <button onClick={() => saveDispatchUpdate(post)} className="text-blue-600 hover:text-blue-900 flex items-center gap-1 bg-blue-50 px-3 py-1 rounded text-sm">
                                                        <Save className="w-4 h-4" /> Save
                                                    </button>
                                                )}
                                                <button onClick={() => openInMaps(post)} className="text-gray-600 hover:text-gray-900 bg-gray-100 px-3 py-1 rounded text-sm flex items-center gap-1">
                                                    <MapPin className="w-4 h-4" /> Map
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Resolution Notes Modal */}
            {resolveModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-lg font-bold">Resolve Incident</h2>
                            <button onClick={() => setResolveModal(null)} className="text-gray-400 hover:text-gray-600">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <p className="text-sm text-gray-600 mb-4">Add resolution notes before closing this incident.</p>
                        <textarea
                            value={resolutionNotes}
                            onChange={(e) => setResolutionNotes(e.target.value)}
                            placeholder="Describe how the incident was resolved..."
                            className="w-full border rounded-lg p-3 text-sm h-32 focus:ring-blue-500 focus:border-blue-500"
                        />
                        <div className="flex justify-end gap-3 mt-4">
                            <button onClick={() => setResolveModal(null)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
                            <button onClick={confirmResolve} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">Confirm Resolution</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Notification Sent Modal */}
            {notificationModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4 text-center">
                        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            {notificationModal.emailFailed ? (
                                <AlertTriangle className="w-8 h-8 text-yellow-600" />
                            ) : (
                                <Mail className="w-8 h-8 text-green-600" />
                            )}
                        </div>
                        <h2 className="text-xl font-bold text-gray-800 mb-2">
                            {notificationModal.emailFailed ? 'Dispatch Updated' : 'Notification Sent!'}
                        </h2>
                        <p className="text-gray-600 mb-4">
                            {notificationModal.emailFailed ? (
                                <>Dispatch status updated for <strong>{notificationModal.userName}</strong>. Email notification could not be sent.</>
                            ) : (
                                <>Email notification sent to <strong>{notificationModal.userName}</strong>!</>
                            )}
                        </p>
                        <div className="bg-gray-50 rounded-lg p-4 text-left text-sm mb-4">
                            <p className="text-gray-600">
                                <strong>Status:</strong> {notificationModal.status?.replace('-', ' ').replace(/\b\w/g, c => c.toUpperCase())}
                            </p>
                            {notificationModal.team && (
                                <p className="text-gray-600">
                                    <strong>Assigned Team:</strong> {notificationModal.team}
                                </p>
                            )}
                            <p className="text-gray-500 text-xs mt-2 italic">
                                "Rescue team is on its way and will reach you as quickly as possible. Stay safe!"
                            </p>
                        </div>
                        <button 
                            onClick={() => setNotificationModal(null)} 
                            className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                        >
                            Done
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
