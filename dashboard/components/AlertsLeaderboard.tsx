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
  const [baselineFilter, setBaselineFilter] = useState<'show_all' | 'yesterday' | 'open' | '15min' | '5min'>('yesterday')
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

  const getPercentValue = (symbolState: SymbolState, baseline: string) => {
    switch (baseline) {
      case 'yesterday': return symbolState.pct_from_yesterday
      case 'open': return symbolState.pct_from_open
      case '15min': return symbolState.pct_from_15min
      case '5min': return symbolState.pct_from_5min
      default: return symbolState.pct_from_yesterday
    }
  }

  const renderColumn = (title: string, data: SymbolState[], colorClass: string) => (
    <div className="bg-gray-950 border border-glass rounded-lg overflow-hidden flex-1">
      <div className="p-3 border-b border-glass glass-header">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h3 className="text-sm font-bold text-teal">
              {title}
            </h3>
            <p className="text-xs text-teal-dark">
              {data.length} active
            </p>
          </div>
          <select
            value={baselineFilter}
            onChange={(e) => setBaselineFilter(e.target.value as typeof baselineFilter)}
            className="bg-gray-900 text-teal text-xs border border-glass rounded px-2 py-1 cursor-pointer hover:bg-gray-800 transition-colors"
          >
            <option value="show_all">SHOW ALL</option>
            <option value="yesterday">% Yest</option>
            <option value="open">% Open</option>
            <option value="15min">% 15M</option>
            <option value="5min">% 5M</option>
          </select>
        </div>
        {baselineFilter === 'show_all' && (
          <div className="flex items-start gap-3 mt-2 pt-2 border-t border-glass">
            {/* Empty space for column 1 (ticker/price/time) */}
            <div className="w-20 flex-shrink-0"></div>

            {/* Headers for columns 2-5 */}
            <div className="grid grid-cols-4 gap-2 flex-1 text-[10px] text-teal-dark uppercase text-center">
              <div>% Yest</div>
              <div>% Open</div>
              <div>% 15M</div>
              <div>% 5M</div>
            </div>
          </div>
        )}
      </div>
      <div className="h-[500px] overflow-y-auto bg-black">
        {data.length === 0 ? (
          <div className="text-center py-12 text-green-800 text-xs">
            No alerts in this range
          </div>
        ) : baselineFilter === 'show_all' ? (
          data.map(symbolState => (
            <div
              key={symbolState.symbol}
              className="border-b border-green-900 hover:bg-green-950/30 transition-colors p-2 text-xs flex items-start gap-3"
            >
              {/* Column 1: Symbol, Price, Timestamp (stacked vertically) */}
              <div className="flex flex-col w-20 flex-shrink-0">
                <span className="font-bold text-green-300 text-sm mb-0.5">{symbolState.symbol}</span>
                <span className="text-green-700 text-xs mb-0.5">${symbolState.current_price.toFixed(2)}</span>
                <span className="text-green-700 text-[10px]">{formatTime(symbolState.last_updated)}</span>
              </div>

              {/* Columns 2-5: 4 Percentage Columns */}
              <div className="grid grid-cols-4 gap-2 flex-1 text-center items-center">
                <span className={`font-bold text-xs ${symbolState.pct_from_yesterday >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {symbolState.pct_from_yesterday > 0 ? '+' : ''}{symbolState.pct_from_yesterday.toFixed(2)}%
                </span>
                <span className={`font-bold text-xs ${symbolState.pct_from_open >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {symbolState.pct_from_open > 0 ? '+' : ''}{symbolState.pct_from_open.toFixed(2)}%
                </span>
                <span className={`font-bold text-xs ${symbolState.pct_from_15min >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {symbolState.pct_from_15min > 0 ? '+' : ''}{symbolState.pct_from_15min.toFixed(2)}%
                </span>
                <span className={`font-bold text-xs ${symbolState.pct_from_5min >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {symbolState.pct_from_5min > 0 ? '+' : ''}{symbolState.pct_from_5min.toFixed(2)}%
                </span>
              </div>
            </div>
          ))
        ) : (
          data.map(symbolState => {
            const pctValue = getPercentValue(symbolState, baselineFilter)
            return (
              <div
                key={symbolState.symbol}
                className="border-b border-green-900 hover:bg-green-950/30 transition-colors p-2 text-xs"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-green-300">{symbolState.symbol}</span>
                  <span className={`font-bold ${colorClass}`}>
                    {pctValue > 0 ? '+' : ''}{pctValue.toFixed(2)}%
                  </span>
                </div>
                <div className="flex items-center justify-between text-green-700">
                  <span>${symbolState.current_price.toFixed(2)}</span>
                  <span>{formatTime(symbolState.last_updated)}</span>
                </div>
              </div>
            )
          })
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
