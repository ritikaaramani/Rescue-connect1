/**
 * ML Backend API client for Simulator
 */

const ML_BACKEND_URL = import.meta.env.VITE_ML_BACKEND_URL || 'http://localhost:8000'

export const mlApi = {
  /**
   * Check for duplicate images before uploading
   * Returns info about existing similar posts within the time window
   */
  async checkDuplicate(imageUrl, hoursWindow = 2) {
    try {
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
    } catch (err) {
      console.error('ML API duplicate check error:', err)
      // Fail-open: allow upload if check fails
      return {
        is_duplicate: false,
        message: 'Could not check for duplicates',
        error: err.message
      }
    }
  },

  /**
   * Analyze an image and check if it's flood-related
   */
  async analyzeImage(imageUrl) {
    try {
      const res = await fetch(`${ML_BACKEND_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_url: imageUrl })
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Analysis failed')
      }
      return res.json()
    } catch (err) {
      console.error('ML API error:', err)
      // Return a default that allows posting (fail-open for now)
      return {
        is_disaster: true,
        disaster_type: 'unknown',
        error: err.message
      }
    }
  }
}

export default mlApi
