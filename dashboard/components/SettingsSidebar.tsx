'use client'

import { useState } from 'react'

interface SettingsSidebarProps {
  threshold: number
  setThreshold: (value: number) => void
  priceFilter: 'all' | 'small' | 'mid' | 'large'
  setPriceFilter: (value: 'all' | 'small' | 'mid' | 'large') => void
}

export function SettingsSidebar({
  threshold,
  setThreshold,
  priceFilter,
  setPriceFilter
}: SettingsSidebarProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      {/* Mobile Menu Button - Fixed at top */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-3 right-3 z-50 md:hidden lg:hidden bg-green-900 text-green-300 p-2 rounded border border-green-600 shadow-lg"
        aria-label="Settings"
      >
        {isOpen ? (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
        )}
      </button>

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div
        className={`
          fixed top-0 right-0 h-full w-80 bg-gray-950 border-l border-green-800 z-50
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
          md:relative md:translate-x-0 md:w-auto md:border-0
          overflow-y-auto
        `}
      >
        <div className="p-6">
          {/* Mobile Header */}
          <div className="flex items-center justify-between mb-6 md:hidden">
            <h2 className="text-xl font-bold text-green-400">⚙️ Settings</h2>
            <button
              onClick={() => setIsOpen(false)}
              className="text-green-600 hover:text-green-400"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Threshold Slider */}
          <div className="mb-8">
            <h3 className="text-green-400 text-sm font-semibold mb-3 uppercase tracking-wider">
              Threshold
            </h3>
            <div className="space-y-3">
              <input
                type="range"
                min="0.1"
                max="5.0"
                step="0.1"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-500"
              />
              <div className="bg-black border border-green-800 px-4 py-3 rounded text-center">
                <span className="text-green-300 text-2xl font-bold">{threshold.toFixed(1)}%</span>
              </div>
            </div>
          </div>

          {/* Price Filter */}
          <div>
            <h3 className="text-green-400 text-sm font-semibold mb-3 uppercase tracking-wider">
              Price Range
            </h3>
            <div className="space-y-2">
              <button
                onClick={() => setPriceFilter('all')}
                className={`w-full px-4 py-3 rounded text-sm font-medium transition-colors border ${
                  priceFilter === 'all'
                    ? 'bg-green-900 text-green-300 border-green-600'
                    : 'bg-gray-800 text-green-700 border-green-800 hover:bg-gray-700'
                }`}
              >
                All Prices
              </button>
              <button
                onClick={() => setPriceFilter('small')}
                className={`w-full px-4 py-3 rounded text-sm font-medium transition-colors border ${
                  priceFilter === 'small'
                    ? 'bg-green-900 text-green-300 border-green-600'
                    : 'bg-gray-800 text-green-700 border-green-800 hover:bg-gray-700'
                }`}
              >
                Small Caps (&lt;$20)
              </button>
              <button
                onClick={() => setPriceFilter('mid')}
                className={`w-full px-4 py-3 rounded text-sm font-medium transition-colors border ${
                  priceFilter === 'mid'
                    ? 'bg-green-900 text-green-300 border-green-600'
                    : 'bg-gray-800 text-green-700 border-green-800 hover:bg-gray-700'
                }`}
              >
                Mid Caps ($20-$100)
              </button>
              <button
                onClick={() => setPriceFilter('large')}
                className={`w-full px-4 py-3 rounded text-sm font-medium transition-colors border ${
                  priceFilter === 'large'
                    ? 'bg-green-900 text-green-300 border-green-600'
                    : 'bg-gray-800 text-green-700 border-green-800 hover:bg-gray-700'
                }`}
              >
                Large Caps ($100+)
              </button>
            </div>
          </div>

          {/* Info Section */}
          <div className="mt-8 p-4 bg-gray-900 border border-green-900 rounded">
            <p className="text-xs text-green-700">
              Filters apply to both the leaderboard and recent alerts table.
            </p>
          </div>
        </div>
      </div>
    </>
  )
}
