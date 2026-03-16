import { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient'
import { AlertTriangle, CheckCircle, Clock, TrendingUp } from 'lucide-react'

export default function Dashboard() {
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    verified: 0,
    rejected: 0,
  })
  const [recentPosts, setRecentPosts] = useState([])

  async function fetchStats() {
    try {
      const { data, error } = await supabase.from('posts').select('status')
      if (error) throw error

      const posts = data ?? []
      setStats({
        total: posts.length,
        pending: posts.filter((p) => p.status === 'pending').length,
        verified: posts.filter((p) => p.status === 'verified').length,
        rejected: posts.filter((p) => p.status === 'rejected').length,
      })
    } catch (err) {
      console.error('Error fetching stats', err)
    }
  }

  async function fetchRecentPosts() {
    try {
      const { data, error } = await supabase
        .from('posts')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(5)

      if (error) throw error
      setRecentPosts(data ?? [])
    } catch (err) {
      console.error('Error fetching recent posts', err)
    }
  }

  useEffect(() => {
    fetchStats()
    fetchRecentPosts()
  }, [])

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-gray-800">Dashboard Overview</h1>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-100 rounded-xl">
              <TrendingUp className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-800">{stats.total}</div>
              <div className="text-sm text-gray-500">Total Reports</div>
            </div>
          </div>
        </div>

        <div className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-yellow-100 rounded-xl">
              <Clock className="w-6 h-6 text-yellow-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-800">{stats.pending}</div>
              <div className="text-sm text-gray-500">Pending Review</div>
            </div>
          </div>
        </div>

        <div className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-green-100 rounded-xl">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-800">{stats.verified}</div>
              <div className="text-sm text-gray-500">Verified</div>
            </div>
          </div>
        </div>

        <div className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-red-100 rounded-xl">
              <AlertTriangle className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-800">{stats.rejected}</div>
              <div className="text-sm text-gray-500">Rejected</div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Reports */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 text-gray-800">Recent Reports</h2>
        {recentPosts.length === 0 ? (
          <p className="text-gray-500">No reports yet</p>
        ) : (
          <div className="space-y-3">
            {recentPosts.map((post) => (
              <div
                key={post.id}
                className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl border border-gray-100 hover:border-blue-200 transition-all"
              >
                {post.image_url && (
                  <img
                    src={post.image_url}
                    alt=""
                    className="w-12 h-12 object-cover rounded-lg"
                  />
                )}
                <div className="flex-1">
                  <p className="text-sm text-gray-700 truncate">
                    {post.caption || 'No caption'}
                  </p>
                  <p className="text-xs text-gray-400">
                    {new Date(post.created_at).toLocaleString()}
                  </p>
                </div>
                <span
                  className={`badge ${
                    post.status === 'verified'
                      ? 'badge-verified'
                      : post.status === 'rejected'
                      ? 'badge-rejected'
                      : 'badge-pending'
                  }`}
                >
                  {post.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
