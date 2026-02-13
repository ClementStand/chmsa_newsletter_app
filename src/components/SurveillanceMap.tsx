'use client'

import React, { useMemo } from "react"
import { useRouter, useSearchParams } from 'next/navigation'
import {
    ComposableMap,
    Geographies,
    Geography,
    Marker,
    ZoomableGroup
} from "react-simple-maps"
import { scaleLinear } from "d3-scale"
import { Tooltip } from "react-tooltip"

// GeoJSON for the world map
const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"

// Mapping of cities to coordinates (Approximate)
const cityCoordinates: { [key: string]: [number, number] } = {
    // North America
    "new york, usa": [-74.006, 40.7128],
    "san francisco, usa": [-122.4194, 37.7749],
    "los angeles, usa": [-118.2437, 34.0522],
    "toronto, canada": [-79.3832, 43.6532],
    "vancouver, canada": [-123.1207, 49.2827],
    "austin, usa": [-97.7431, 30.2672],
    "chicago, usa": [-87.6298, 41.8781],
    // Europe
    "london, uk": [-0.1276, 51.5074],
    "paris, france": [2.3522, 48.8566],
    "berlin, germany": [13.4050, 52.5200],
    "munich, germany": [11.5820, 48.1351],
    "amsterdam, netherlands": [4.9041, 52.3676],
    "copenhagen, denmark": [12.5683, 55.6761],
    "stockholm, sweden": [18.0686, 59.3293],
    "zurich, switzerland": [8.5417, 47.3769],
    "dublin, ireland": [-6.2603, 53.3498],
    // APAC
    "singapore": [103.8198, 1.3521],
    "sydney, australia": [151.2093, -33.8688],
    "melbourne, australia": [144.9631, -37.8136],
    "tokyo, japan": [139.6917, 35.6895],
    "seoul, south korea": [126.9780, 37.5665],
    "beijing, china": [116.4074, 39.9042],
    "shanghai, china": [121.4737, 31.2304],
    "mumbai, india": [72.8777, 19.0760],
    "bengaluru, india": [77.5946, 12.9716],
    // Middle East
    "dubai, uae": [55.2708, 25.2048],
    "abu dhabi, uae": [54.3773, 24.4539],
    "riyadh, saudi arabia": [46.6753, 24.7136],
    "doha, qatar": [51.5310, 25.2854],
    "tel aviv, israel": [34.7818, 32.0853],
    "istanbul, turkey": [28.9784, 41.0082],
    // Europe (Expanded)
    "madrid, spain": [-3.7038, 40.4168],
    "barcelona, spain": [2.1734, 41.3851],
    "rome, italy": [12.4964, 41.9028],
    "milan, italy": [9.1900, 45.4642],
    "brussels, belgium": [4.3517, 50.8503],
    "vienna, austria": [16.3738, 48.2082],
    "warsaw, poland": [21.0122, 52.2297],
    "oslo, norway": [10.7522, 59.9139],
    "helsinki, finland": [24.9384, 60.1699],
    // South America
    "sao paulo, brazil": [-46.6333, -23.5505],
    "buenos aires, argentina": [-58.3816, -34.6037],
    // Africa
    "cape town, south africa": [18.4241, -33.9249],
    "johannesburg, south africa": [28.0473, -26.2041],
    "cairo, egypt": [31.2357, 30.0444],
}

// Fallback Country Centers
const countryCoordinates: { [key: string]: [number, number] } = {
    "usa": [-95.7129, 37.0902],
    "canada": [-106.3468, 56.1304],
    "uk": [-3.435, 55.378],
    "france": [2.2137, 46.2276],
    "germany": [10.4515, 51.1657],
    "australia": [133.7751, -25.2744],
    "japan": [138.2529, 36.2048],
    "china": [104.1954, 35.8617],
    "india": [78.9629, 20.5937],
    "brazil": [-51.9253, -14.2350],
    "south africa": [22.9375, -30.5595],
}

interface SurveillanceMapProps {
    news: any[]
}

const SurveillanceMap: React.FC<SurveillanceMapProps> = ({ news }) => {
    const router = useRouter()
    const searchParams = useSearchParams()

    // Aggregate news by region/location
    const { regionStats, globalCount } = useMemo(() => {
        const stats: { [key: string]: { count: number; maxThreat: number; name: string; coordinates: [number, number] } } = {}
        let global = 0

        news.forEach(item => {
            // Determine Region Grouping
            // Prioritize the standardized 'region' field from DB
            let locationName = item.region || "Global"

            // If Global/Unknown, try to fall back to specific location logic for coordinate mapping
            // But we want to group dots by region if we can, or specific cities?
            // The map shows dots at CITIES. The region field is for filtering.
            // Wait, the map needs to plot dots at cities.
            // The User wants: "Map shows dots in Europe for European competitors/news"
            // If we have a city, use it. If not, use Region center?
            // Let's keep the city logic for coordinates, but maybe use region for color/filtering?
            // Actually, the user problem was "No dots on map for Europe".
            // If the news has no specific location, we need it to plot somewhere.
            // Logic:
            // 1. If explicit location (City) -> Plot at City
            // 2. If no location but has Region -> Plot at Region Center
            // 3. Fallback to Global

            // Try to parse details for specific city
            let parsed: any = {}
            try {
                parsed = JSON.parse(item.details)
                if (parsed.details && parsed.details.location) parsed = parsed.details
            } catch (e) { }

            let finalCoords: [number, number] | null = null

            if (parsed.location) {
                const loc = parsed.location.toLowerCase().trim()
                if (cityCoordinates[loc]) {
                    locationName = parsed.location
                    finalCoords = cityCoordinates[loc]
                } else {
                    const countryMatch = Object.keys(countryCoordinates).find(c => loc.includes(c))
                    if (countryMatch) {
                        locationName = countryMatch.charAt(0).toUpperCase() + countryMatch.slice(1)
                        finalCoords = countryCoordinates[countryMatch]
                    }
                }
            }

            // If no city/country match, use Region Center
            if (!finalCoords) {
                if (locationName === 'MENA') finalCoords = [45, 25]  // Saudi/Center
                else if (locationName === 'Europe') finalCoords = [15, 50] // Central EU
                else if (locationName === 'North America') finalCoords = [-100, 40]
                else if (locationName === 'APAC') finalCoords = [100, 20]
                else if (locationName === 'South America') finalCoords = [-60, -15]
                else {
                    global++
                    return
                }
            }

            if (!stats[locationName]) {
                stats[locationName] = {
                    count: 0,
                    maxThreat: 0,
                    name: locationName,
                    coordinates: finalCoords || [0, 0]
                }
            }

            stats[locationName].count += 1
            stats[locationName].maxThreat = Math.max(stats[locationName].maxThreat, item.threatLevel)
        })

        return { regionStats: Object.values(stats), globalCount: global }
    }, [news])

    const maxCount = Math.max(...regionStats.map(s => s.count), 1)
    const popScale = scaleLinear().domain([0, maxCount]).range([8, 24])

    const handleMarkerClick = (regionName: string) => {
        const params = new URLSearchParams(searchParams.toString())
        params.set('location', regionName.toLowerCase())
        router.push(`/?${params.toString()}`)
    }

    const handleReset = () => {
        const params = new URLSearchParams(searchParams.toString())
        params.delete('location')
        router.push(`/?${params.toString()}`)
    }

    // Map Control State
    const [position, setPosition] = React.useState({ coordinates: [0, 20] as [number, number], zoom: 1 })

    const handleRegionFocus = (region: string) => {
        // 1. Zoom Map
        switch (region) {
            case 'Global':
                setPosition({ coordinates: [0, 20], zoom: 1 })
                break;
            case 'North America':
                setPosition({ coordinates: [-100, 40], zoom: 2.5 })
                break;
            case 'Europe':
                setPosition({ coordinates: [15, 50], zoom: 3 })
                break;
            case 'MENA':
                setPosition({ coordinates: [45, 25], zoom: 3.5 })
                break;
            case 'APAC':
                setPosition({ coordinates: [100, 20], zoom: 2 })
                break;
        }

        // 2. Filter Feed (Sync with Sidebar)
        const params = new URLSearchParams(searchParams.toString())
        if (region === 'Global') {
            params.delete('region')
        } else if (region === 'MENA') {
            params.set('region', 'Middle East') // Map MENA -> Middle East value
        } else {
            params.set('region', region)
        }
        router.push(`/?${params.toString()}`)
    }

    return (
        <div className="w-full bg-slate-950/50 rounded-xl border border-slate-800 overflow-hidden relative mb-8 shadow-2xl shadow-black/50 backdrop-blur-sm group/map">
            {/* Header HUD & Controls */}
            <div className="absolute top-4 left-4 z-10 flex flex-col gap-3">
                <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-widest bg-slate-950/80 px-3 py-1 rounded border border-cyan-900/50 backdrop-blur-md w-fit">
                    Global Surveillance
                </h3>

                {/* Focus Buttons */}
                <div className="flex gap-1">
                    {['Global', 'North America', 'Europe', 'MENA', 'APAC'].map(r => (
                        <button
                            key={r}
                            onClick={(e) => { e.stopPropagation(); handleRegionFocus(r); }}
                            className="text-[10px] uppercase font-bold text-slate-400 hover:text-cyan-400 bg-slate-950/80 hover:bg-slate-900/90 px-2 py-1 rounded border border-slate-700/50 transition-colors"
                        >
                            {r}
                        </button>
                    ))}
                </div>
            </div>

            {/* Global Signals HUD */}
            <div className="absolute top-4 right-4 z-10 pointer-events-none">
                <div className="flex items-center gap-2 bg-slate-950/80 px-3 py-2 rounded border border-slate-700/50 backdrop-blur-md shadow-lg">
                    <span className="text-lg">🌍</span>
                    <div>
                        <p className="text-[10px] text-slate-400 uppercase font-semibold leading-none mb-0.5">Global Signals</p>
                        <p className="text-sm font-bold text-white leading-none">{globalCount}</p>
                    </div>
                </div>
            </div>

            {/* Reset Button (Only visible if filtered) */}
            {searchParams.get('location') && (
                <div className="absolute bottom-4 right-4 z-10">
                    <button
                        onClick={(e) => { e.stopPropagation(); handleReset(); }}
                        className="bg-red-950/80 hover:bg-red-900/80 text-red-200 text-xs px-3 py-1 rounded border border-red-900/50 backdrop-blur-md transition-colors"
                    >
                        Clear Filter
                    </button>
                </div>
            )}

            <ComposableMap
                projection="geoMercator"
                projectionConfig={{
                    scale: 120,
                }}
                className="w-full h-96 bg-[#0f172a] cursor-move active:cursor-grabbing outline-none" // Added outline-none
                onClick={handleReset}
            >
                {/* Controlled ZoomableGroup */}
                <ZoomableGroup
                    zoom={position.zoom}
                    center={position.coordinates}
                    onMoveEnd={(pos) => setPosition(pos)}
                    minZoom={1}
                    maxZoom={4}
                >
                    <Geographies geography={geoUrl}>
                        {({ geographies }) =>
                            geographies.map((geo) => (
                                <Geography
                                    key={geo.rsmKey}
                                    geography={geo}
                                    fill="#1e293b"
                                    stroke="#334155"
                                    strokeWidth={0.5}
                                    style={{
                                        default: { outline: "none" },
                                        hover: { fill: "#334155", outline: "none" },
                                        pressed: { outline: "none" },
                                    }}
                                />
                            ))
                        }
                    </Geographies>

                    {regionStats.map(({ name, coordinates, count, maxThreat }) => {
                        const size = popScale(count)
                        // Determine color
                        let colorClass = "fill-cyan-500"
                        if (maxThreat >= 3) colorClass = "fill-yellow-500"
                        if (maxThreat >= 4) colorClass = "fill-red-500"

                        const isSelected = searchParams.get('location') === name.toLowerCase()

                        return (
                            <Marker key={name} coordinates={coordinates} onClick={(e) => {
                                e.stopPropagation()
                                handleMarkerClick(name)
                            }}>
                                <g
                                    data-tooltip-id="map-tooltip"
                                    data-tooltip-content={`${name}: ${count} signals`}
                                    className="group cursor-pointer hover:opacity-80 transition-opacity focus:outline-none" // focus:outline-none
                                    style={{ outline: 'none' }}
                                >
                                    {/* Selection Glow instead of pulsing rectangle */}
                                    {isSelected && (
                                        <circle
                                            r={size * 1.5}
                                            className="fill-none stroke-cyan-400 stroke-[1.5] opacity-100" // Static ring
                                        />
                                    )}

                                    {/* Pulse Animation - ONLY if NOT selected to avoid busy look? Or keep it subtle */}
                                    <circle
                                        r={size}
                                        className={`${colorClass} opacity-20 animate-ping origin-center`}
                                        style={{ animationDuration: '3s' }}
                                    />
                                    <circle
                                        r={size * 0.6}
                                        className={`${colorClass} opacity-80 stroke-white/10 stroke-1`}
                                    />
                                </g>
                            </Marker>
                        )
                    })}
                </ZoomableGroup>
            </ComposableMap>
            <Tooltip id="map-tooltip" className="z-50 !bg-slate-900 !text-slate-100 !border !border-slate-700 !opacity-100 !rounded-md !text-xs !py-1 !px-2 shadow-xl" />
        </div>
    )
}

export default SurveillanceMap
