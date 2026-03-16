/**
 * ML Backend API client
 */

const ML_BACKEND_URL = import.meta.env.VITE_ML_BACKEND_URL || 'http://localhost:8000'

export const mlApi = {
  /**
   * Check if ML backend is healthy
   */
  async health() {
    const res = await fetch(`${ML_BACKEND_URL}/health`)
    return res.json()
  },

  /**
   * Analyze a single image without updating database
   */
  async analyzeImage(imageUrl) {
    const res = await fetch(`${ML_BACKEND_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_url: imageUrl })
    })
    if (!res.ok) throw new Error('Analysis failed')
    return res.json()
  },

  /**
   * Process a single post (analyze + update in database)
   */
  async processPost(postId) {
    const res = await fetch(`${ML_BACKEND_URL}/process-post`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: postId })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Processing failed')
    }
    return res.json()
  },

  /**
   * Process a single post with full pipeline (OCR + text analysis + geolocation)
   */
  async processPostFull(postId) {
    const res = await fetch(`${ML_BACKEND_URL}/process-full`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: postId })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Full processing failed')
    }
    return res.json()
  },

  /**
   * Process all pending posts
   */
  async processAllPending() {
    const res = await fetch(`${ML_BACKEND_URL}/process-all-pending`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    if (!res.ok) throw new Error('Batch processing failed')
    return res.json()
  },

  /**
   * Update post status (uses service key to bypass RLS)
   */
  async updateStatus(postId, status) {
    const res = await fetch(`${ML_BACKEND_URL}/update-status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: postId, status })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Update status failed')
    }
    return res.json()
  },

  /**
   * Reset AI analysis for a post
   */
  async resetAI(postId) {
    const res = await fetch(`${ML_BACKEND_URL}/reset-ai`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: postId })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Reset AI failed')
    }
    return res.json()
  },

  /**
   * Check for duplicate images before processing
   */
  async checkDuplicate(imageUrl, hoursWindow = 2) {
    const res = await fetch(`${ML_BACKEND_URL}/check-duplicate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        image_url: imageUrl,
        hours_window: hoursWindow
      })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Duplicate check failed')
    }
    return res.json()
  },

  /**
   * Update dispatch status and assigned team
   */
  async updateDispatch(postId, dispatchStatus, assignedTeam, resolutionNotes = null) {
    const body = {
      post_id: postId,
      dispatch_status: dispatchStatus,
      assigned_team: assignedTeam
    }
    if (resolutionNotes !== null) {
      body.resolution_notes = resolutionNotes
    }
    const res = await fetch(`${ML_BACKEND_URL}/update-dispatch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Update dispatch failed')
    }
    return res.json()
  }
}

export default mlApi
