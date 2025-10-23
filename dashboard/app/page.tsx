'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { AlertsList } from '@/components/AlertsList'
import { AlertsLeaderboard } from '@/components/AlertsLeaderboard'
import { StatsCards } from '@/components/StatsCards'
import { SettingsSidebar } from '@/components/SettingsSidebar'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Home() {
  const [stats, setStats] = useState<any>(null)
  const [alerts, setAlerts] = useState<any[]>([])
  const [leaderboardCounts, setLeaderboardCounts] = useState({ movers_20plus: 0, movers_10to20: 0, movers_1to10: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [threshold, setThreshold] = useState<number>(1.0) // Default 1%
  const [priceFilter, setPriceFilter] = useState<'all' | 'small' | 'mid' | 'large'>('all')
  const [loadingStatus, setLoadingStatus] = useState<string>('Connecting to server...')

  useEffect(() => {
    let retryCount = 0
    const maxRetries = 3
    let hasLoadedOnce = false

    // Fetch stats
    const fetchStats = async () => {
      try {
        const response = await fetch(`${API_URL}/alerts/stats`)
        if (!response.ok) throw new Error('Failed to fetch stats')
        const data = await response.json()
        setStats(data)
        if (!hasLoadedOnce) {
          setLoadingStatus('Connected')
          setLoading(false)
          hasLoadedOnce = true
        }
        retryCount = 0
      } catch (err: any) {
        console.error('Stats fetch error:', err)
        if (retryCount < maxRetries) {
          retryCount++
          setLoadingStatus(`Connection issue - retrying (${retryCount}/${maxRetries})...`)
        } else {
          setError('Could not connect to server')
          setLoadingStatus('Could not connect - servers may be down')
        }
      }
    }

    // Fetch leaderboard counts
    const fetchLeaderboardCounts = async () => {
      try {
        const response = await fetch(`${API_URL}/symbols/leaderboard?threshold=1.0&baseline=yesterday`)
        if (!response.ok) throw new Error('Failed to fetch leaderboard')
        const data = await response.json()
        setLeaderboardCounts({
          movers_20plus: data.col_20_plus?.length || 0,
          movers_10to20: data.col_10_to_20?.length || 0,
          movers_1to10: data.col_1_to_10?.length || 0
        })
        retryCount = 0
      } catch (err: any) {
        console.error('Failed to fetch leaderboard counts:', err)
      }
    }

    // Fetch alerts for recent alerts table
    const fetchAlerts = async () => {
      try {
        const response = await fetch(`${API_URL}/alerts?limit=100`)
        if (!response.ok) throw new Error('Failed to fetch alerts')
        const data = await response.json()
        setAlerts(data)
        retryCount = 0
      } catch (err: any) {
        console.error('Failed to fetch alerts:', err)
      }
    }

    // Fire all requests in parallel immediately
    Promise.all([fetchStats(), fetchLeaderboardCounts(), fetchAlerts()])

    // Refresh intervals
    const alertInterval = setInterval(fetchAlerts, 2000)
    const leaderboardInterval = setInterval(fetchLeaderboardCounts, 2000)
    const statsInterval = setInterval(fetchStats, 30000)

    return () => {
      clearInterval(alertInterval)
      clearInterval(leaderboardInterval)
      clearInterval(statsInterval)
    }
  }, [])

  return (
    <div className="min-h-screen bg-black font-mono text-green-400">
      <div className="flex">
        {/* Main Content */}
        <main className="flex-1 p-4 md:p-6 max-w-7xl mx-auto w-full">
          {/* Header */}
          <div className="mb-6 border-b border-green-800 pb-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl md:text-3xl font-bold mb-1">
                  📊 DASHBOARD
                </h1>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${
                    loadingStatus === 'Connected'
                      ? 'bg-green-500'
                      : loadingStatus.includes('could not') || loadingStatus.includes('down')
                      ? 'bg-red-500'
                      : loadingStatus.includes('retrying') || loadingStatus.includes('Partial')
                      ? 'bg-yellow-500'
                      : 'bg-green-700'
                  }`}></div>
                  <p className={`text-sm ${
                    loadingStatus === 'Connected'
                      ? 'text-green-600'
                      : loadingStatus.includes('could not') || loadingStatus.includes('down')
                      ? 'text-red-600'
                      : loadingStatus.includes('retrying') || loadingStatus.includes('Partial')
                      ? 'text-yellow-600'
                      : 'text-green-700'
                  }`}>
                    {loadingStatus}
                  </p>
                </div>
              </div>
              <div className="hidden md:flex gap-3">
                <Link
                  href="/"
                  className="px-4 py-2 bg-green-900 text-green-300 rounded font-medium transition-colors border border-green-600"
                >
                  Dashboard
                </Link>
                <Link
                  href="/live"
                  className="px-4 py-2 bg-green-900/50 hover:bg-green-900 text-green-700 hover:text-green-400 rounded font-medium transition-colors border border-green-800"
                >
                  Alert Feed
                </Link>
                <Link
                  href="/raw-feed"
                  className="px-4 py-2 bg-green-900/50 hover:bg-green-900 text-green-700 hover:text-green-400 rounded font-medium transition-colors border border-green-800"
                >
                  Raw Data
                </Link>
              </div>
            </div>
          </div>

          {/* Mobile Navigation */}
          <div className="md:hidden mb-6 flex gap-2 overflow-x-auto">
            <Link
              href="/"
              className="px-4 py-2 bg-green-900 text-green-300 rounded font-medium transition-colors border border-green-600 whitespace-nowrap"
            >
              Dashboard
            </Link>
            <Link
              href="/live"
              className="px-4 py-2 bg-green-900/50 hover:bg-green-900 text-green-700 hover:text-green-400 rounded font-medium transition-colors border border-green-800 whitespace-nowrap"
            >
              Alert Feed
            </Link>
            <Link
              href="/raw-feed"
              className="px-4 py-2 bg-green-900/50 hover:bg-green-900 text-green-700 hover:text-green-400 rounded font-medium transition-colors border border-green-800 whitespace-nowrap"
            >
              Raw Data
            </Link>
          </div>

          {/* Desktop Filters (hidden on mobile - use sidebar instead) */}
          <div className="hidden lg:block mb-6 bg-gray-900 border border-green-800 rounded p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h3 className="text-green-400 text-sm font-semibold mb-1">FILTERS</h3>
                <p className="text-green-700 text-xs mb-3">
                  Filter alerts by threshold and stock price
                </p>
                {/* Price Filter Buttons */}
                <div className="flex gap-2">
                  <button
                    onClick={() => setPriceFilter('all')}
                    className={`px-3 py-1.5 rounded text-xs font-medium transition-colors border ${
                      priceFilter === 'all'
                        ? 'bg-green-900 text-green-300 border-green-600'
                        : 'bg-gray-800 text-green-700 border-green-800 hover:bg-gray-700'
                    }`}
                  >
                    All Prices
                  </button>
                  <button
                    onClick={() => setPriceFilter('small')}
                    className={`px-3 py-1.5 rounded text-xs font-medium transition-colors border ${
                      priceFilter === 'small'
                        ? 'bg-green-900 text-green-300 border-green-600'
                        : 'bg-gray-800 text-green-700 border-green-800 hover:bg-gray-700'
                    }`}
                  >
                    Small (&lt;$20)
                  </button>
                  <button
                    onClick={() => setPriceFilter('mid')}
                    className={`px-3 py-1.5 rounded text-xs font-medium transition-colors border ${
                      priceFilter === 'mid'
                        ? 'bg-green-900 text-green-300 border-green-600'
                        : 'bg-gray-800 text-green-700 border-green-800 hover:bg-gray-700'
                    }`}
                  >
                    Mid ($20-$100)
                  </button>
                  <button
                    onClick={() => setPriceFilter('large')}
                    className={`px-3 py-1.5 rounded text-xs font-medium transition-colors border ${
                      priceFilter === 'large'
                        ? 'bg-green-900 text-green-300 border-green-600'
                        : 'bg-gray-800 text-green-700 border-green-800 hover:bg-gray-700'
                    }`}
                  >
                    Large ($100+)
                  </button>
                </div>
              </div>
              {/* Threshold Slider */}
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="text-green-600 text-xs uppercase mb-1">Threshold</div>
                  <input
                    type="range"
                    min="0.1"
                    max="5.0"
                    step="0.1"
                    value={threshold}
                    onChange={(e) => setThreshold(parseFloat(e.target.value))}
                    className="w-48 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-500"
                  />
                </div>
                <div className="bg-black border border-green-800 px-4 py-2 rounded min-w-[100px] text-center">
                  <span className="text-green-300 text-2xl font-bold">{threshold.toFixed(1)}%</span>
                </div>
              </div>
            </div>
          </div>

        {/* Stats Cards */}
        {loading && <p className="text-green-600">Loading stats...</p>}
        {error && (
          <div className="bg-red-900 border border-red-700 text-red-300 px-4 py-3 rounded mb-4">
            Error: {error}
          </div>
        )}
        {stats && <StatsCards stats={stats} leaderboardCounts={leaderboardCounts} />}

        {/* Leaderboard */}
        <AlertsLeaderboard
          threshold={threshold}
          priceFilter={priceFilter}
        />

          {/* Alerts List */}
          <div className="mt-6">
            <AlertsList
              threshold={threshold}
              priceFilter={priceFilter}
              alerts={alerts}
            />
          </div>
        </main>

        {/* Settings Sidebar - Hidden on desktop lg+, shows as slide-out on mobile/tablet */}
        <aside className="lg:hidden">
          <SettingsSidebar
            threshold={threshold}
            setThreshold={setThreshold}
            priceFilter={priceFilter}
            setPriceFilter={setPriceFilter}
          />
        </aside>
      </div>
    </div>
  )
}
