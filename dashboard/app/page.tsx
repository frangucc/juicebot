'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { AlertsList } from '@/components/AlertsList'
import { AlertsLeaderboard } from '@/components/AlertsLeaderboard'
import { StatsCards } from '@/components/StatsCards'
import { SettingsSidebar } from '@/components/SettingsSidebar'
import { useData } from '@/contexts/DataContext'

export default function Home() {
  const { stats, alerts, leaderboardCounts, loadingStatus, isLoading } = useData()
  const [threshold, setThreshold] = useState<number>(1.0) // Default 1%
  const [priceFilter, setPriceFilter] = useState<'all' | 'small' | 'mid' | 'large'>('all')
  const [error, setError] = useState<string | null>(null)

  return (
    <div className="min-h-screen bg-black font-mono text-green-400">
      <div className="flex">
        {/* Main Content */}
        <main className="flex-1 p-4 md:p-6 max-w-7xl mx-auto w-full">
          {/* Header */}
          <div className="mb-6 pb-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-1 mb-1">
                  <Image
                    src="/images/juicebot-logo-filled.png"
                    alt="Juicebot Logo"
                    width={48}
                    height={48}
                    className="object-contain"
                  />
                  <Image
                    src="/images/juicebot-text-logo.png"
                    alt="Juicebot"
                    width={180}
                    height={32}
                    className="object-contain pt-2"
                  />
                </div>
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
          <div className="hidden lg:block mb-6 glass-section rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h3 className="text-teal text-sm font-semibold mb-1">FILTERS</h3>
                <p className="text-teal-dark text-xs mb-3">
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
        {error && (
          <div className="bg-red-900 border border-red-700 text-red-300 px-4 py-3 rounded mb-4">
            Error: {error}
          </div>
        )}
        {stats && <StatsCards stats={stats} leaderboardCounts={leaderboardCounts} />}
        {isLoading && !stats && <p className="text-green-600">{loadingStatus}</p>}

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
