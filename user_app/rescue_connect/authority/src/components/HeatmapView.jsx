import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import { supabase } from '../supabaseClient'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
// Note: 'leaflet.heat' must be installed. If not, this might throw runtime error until installed.
import 'leaflet.heat'

function HeatmapLayer({ points }) {
    const map = useMap()

    useEffect(() => {
        if (!points || points.length === 0) return

        // Create heat layer
        // Format: [lat, lon, intensity]
        // We normalize intensity based on severity? Or just density.
        // For now, simple density.
        const heat = L.heatLayer(points, {
            radius: 25,
            blur: 15,
            maxZoom: 10,
        }).addTo(map)

        return () => {
            map.removeLayer(heat)
        }
    }, [points, map])

    return null
}

export default function HeatmapView() {
    const [points, setPoints] = useState([])
    const [loading, setLoading] = useState(true)

    // Default center (Bangalore, India)
    const defaultCenter = [12.9716, 77.5946]
    const defaultZoom = 11

    useEffect(() => {
        fetchPoints()
    }, [])

    async function fetchPoints() {
        setLoading(true)
        try {
            const { data, error } = await supabase
                .from('posts')
                .select('inferred_latitude, inferred_longitude, severity, status')
                .not('inferred_latitude', 'is', null)
                .not('inferred_longitude', 'is', null)
                // You might want to filter out 'rejected'?
                .neq('status', 'rejected')

            if (error) {
                console.error('Error fetching heatmap data:', error)
            } else {
                // Transform to [lat, lon, intensity]
                // Intensity mapping: critical=1.0, high=0.8, medium=0.5, low=0.3
                const intensityMap = {
                    'critical': 1.0,
                    'high': 0.8,
                    'medium': 0.5,
                    'low': 0.3
                }

                const heatPoints = data.map(p => [
                    p.inferred_latitude,
                    p.inferred_longitude,
                    intensityMap[p.severity] || 0.5 // Default intensity
                ])
                setPoints(heatPoints)
            }
        } catch (err) {
            console.error('Failed to fetch heatmap data:', err)
        }
        setLoading(false)
    }

    return (
        <div className="flex flex-col h-full">
            <div className="mb-4">
                <h2 className="text-xl font-bold text-white">🔥 Disaster Heatmap</h2>
                <p className="text-gray-400 text-sm">
                    Visualizing density and severity of {points.length} active reports.
                </p>
            </div>

            <div className="flex-1 rounded-xl overflow-hidden border border-gray-700" style={{ minHeight: '500px' }}>
                <MapContainer
                    center={defaultCenter}
                    zoom={defaultZoom}
                    style={{ height: '100%', width: '100%' }}
                >
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />

                    {points.length > 0 && <HeatmapLayer points={points} />}
                </MapContainer>
            </div>
        </div>
    )
}
