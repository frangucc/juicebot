'use client'

import { useEffect, useState } from 'react'

interface SymbolState {
  symbol: string
  current_price: number
  pct_from_yesterday: number
  pct_from_open: number
  pct_from_15min: number
  pct_from_5min: number
  hod_pct: number
  last_updated: string
}

interface AlertsLeaderboardProps {
  threshold: number
  priceFilter: 'all' | 'small' | 'mid' | 'large'
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function AlertsLeaderboard({ threshold, priceFilter }: AlertsLeaderboardProps) {
  const [leaderboardData, setLeaderboardData] = useState<{
    col_20_plus: SymbolState[]
    col_10_to_20: SymbolState[]
    col_1_to_10: SymbolState[]
  }>({
    col_20_plus: [],
    col_10_to_20: [],
    col_1_to_10: []
  })

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        // Convert price filter to query param
        const priceParam = priceFilter !== 'all' ? `&price_filter=${priceFilter}` : ''
        const response = await fetch(
          `${API_URL}/symbols/leaderboard?threshold=${threshold}&baseline=yesterday${priceParam}`
        )
        if (response.ok) {
          const data = await response.json()
          setLeaderboardData({
            col_20_plus: data.col_20_plus || [],
            col_10_to_20: data.col_10_to_20 || [],
            col_1_to_10: data.col_1_to_10 || []
          })
        }
      } catch (error) {
        console.error('Failed to fetch leaderboard:', error)
      }
    }

    fetchLeaderboard()
    const interval = setInterval(fetchLeaderboard, 2000)
    return () => clearInterval(interval)
  }, [threshold, priceFilter])

  const col20Plus = leaderboardData.col_20_plus
  const col10To20 = leaderboardData.col_10_to_20
  const col1To10 = leaderboardData.col_1_to_10

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMin = Math.floor(diffMs / 60000)

    if (diffMin < 1) return '1 min ago'
    if (diffMin < 60) return `${diffMin} min ago`
    const diffHours = Math.floor(diffMin / 60)
    return `${diffHours}h ago`
  }

  const renderColumn = (title: string, data: SymbolState[], colorClass: string) => (
    <div className="bg-gray-950 border border-glass rounded-lg overflow-hidden flex-1">
      <div className="p-3 border-b border-glass glass-header">
        <h3 className="text-sm font-bold text-teal">
          {title}
        </h3>
        <p className="text-xs text-teal-dark">
          {data.length} active
        </p>
      </div>
      <div className="h-[500px] overflow-y-auto bg-black">
        {data.length === 0 ? (
          <div className="text-center py-12 text-green-800 text-xs">
            No alerts in this range
          </div>
        ) : (
          data.map(symbolState => (
            <div
              key={symbolState.symbol}
              className="border-b border-green-900 hover:bg-green-950/30 transition-colors p-2 text-xs"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-green-300">{symbolState.symbol}</span>
                <span className={`font-bold ${colorClass}`}>
                  {symbolState.pct_from_yesterday > 0 ? '+' : ''}{symbolState.pct_from_yesterday.toFixed(2)}%
                </span>
              </div>
              <div className="flex items-center justify-between text-green-700">
                <span>${symbolState.current_price.toFixed(2)}</span>
                <span>{formatTime(symbolState.last_updated)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )

  return (
    <div className="mb-6">
      {/* Desktop: 3 columns side by side */}
      <div className="hidden md:grid md:grid-cols-3 gap-4">
        {renderColumn('20%+', col20Plus, 'text-red-400')}
        {renderColumn('10-20%', col10To20, 'text-yellow-400')}
        {renderColumn('1-10%', col1To10, 'text-green-400')}
      </div>

      {/* Mobile: Single column view with hint */}
      <div className="md:hidden">
        <div className="overflow-hidden">
          <div className="snap-start shrink-0 w-full">
            {renderColumn('20%+', col20Plus, 'text-red-400')}
          </div>
        </div>
        <p className="text-center text-xs text-green-700 mt-2">
          Swipe right on table below to see 10-20% and 1-10% segments
        </p>
      </div>
    </div>
  )
}
