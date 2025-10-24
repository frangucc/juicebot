'use client'

import { useEffect, useState } from 'react'
import { useData } from '@/contexts/DataContext'

interface SymbolState {
  symbol: string
  current_price: number
  pct_from_yesterday: number
  pct_from_pre: number | null
  pct_from_open: number
  pct_from_post: number | null
  pct_from_15min: number
  pct_from_5min: number
  pct_from_1min: number
  hod_pct: number
  last_updated: string
}

interface AlertsLeaderboardProps {
  threshold: number
  priceFilter: 'all' | 'small' | 'mid' | 'large'
  baselineFilter: 'show_all' | 'yesterday' | 'pre' | 'open' | 'post' | '15min' | '5min'
  setBaselineFilter: (value: 'show_all' | 'yesterday' | 'pre' | 'open' | 'post' | '15min' | '5min') => void
  gapDirection: 'up' | 'down'
  setGapDirection: (value: 'up' | 'down') => void
  searchQuery: string
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function AlertsLeaderboard({ threshold, priceFilter, baselineFilter, setBaselineFilter, gapDirection, setGapDirection, searchQuery }: AlertsLeaderboardProps) {
  const { realtimePrices } = useData()
  const [leaderboardData, setLeaderboardData] = useState<{
    col_20_plus: SymbolState[]
    col_10_to_20: SymbolState[]
    col_1_to_10: SymbolState[]
  }>({
    col_20_plus: [],
    col_10_to_20: [],
    col_1_to_10: []
  })
  const [flashingRows, setFlashingRows] = useState<Map<string, 'up' | 'down'>>(new Map())
  const [previousData, setPreviousData] = useState<{
    col_20_plus: SymbolState[]
    col_10_to_20: SymbolState[]
    col_1_to_10: SymbolState[]
  }>({
    col_20_plus: [],
    col_10_to_20: [],
    col_1_to_10: []
  })
  const [discordJuiceBoxes, setDiscordJuiceBoxes] = useState<Record<string, number>>({})

  // Update leaderboard data with real-time WebSocket prices
  useEffect(() => {
    if (realtimePrices.size === 0) return

    setLeaderboardData(prevData => {
      const updateColumn = (column: SymbolState[]) => {
        return column.map(symbolState => {
          const rtPrice = realtimePrices.get(symbolState.symbol)
          if (rtPrice && rtPrice.pct_from_yesterday !== null) {
            // Update with real-time data
            return {
              ...symbolState,
              current_price: rtPrice.price,
              pct_from_yesterday: rtPrice.pct_from_yesterday,
              last_updated: rtPrice.timestamp
            }
          }
          return symbolState
        })
      }

      return {
        col_20_plus: updateColumn(prevData.col_20_plus),
        col_10_to_20: updateColumn(prevData.col_10_to_20),
        col_1_to_10: updateColumn(prevData.col_1_to_10)
      }
    })
  }, [realtimePrices])

  // Helper function to detect if a row has been updated and determine direction
  const detectUpdates = (newData: SymbolState[], oldData: SymbolState[], column: string) => {
    const updatedSymbols = new Map<string, 'up' | 'down'>()

    newData.forEach(newSymbol => {
      const oldSymbol = oldData.find(s => s.symbol === newSymbol.symbol)
      if (oldSymbol) {
        // Check if the primary percentage value (current_price) has changed
        // Determine direction based on price change
        const priceChanged = newSymbol.current_price !== oldSymbol.current_price

        if (priceChanged) {
          const direction = newSymbol.current_price > oldSymbol.current_price ? 'up' : 'down'
          updatedSymbols.set(`${column}-${newSymbol.symbol}`, direction)
        } else if (
          // Also check if percentage values changed without price change
          newSymbol.pct_from_yesterday !== oldSymbol.pct_from_yesterday ||
          newSymbol.pct_from_pre !== oldSymbol.pct_from_pre ||
          newSymbol.pct_from_open !== oldSymbol.pct_from_open ||
          newSymbol.pct_from_post !== oldSymbol.pct_from_post ||
          newSymbol.pct_from_15min !== oldSymbol.pct_from_15min ||
          newSymbol.pct_from_5min !== oldSymbol.pct_from_5min
        ) {
          // Use yesterday's percentage change as the primary indicator
          const direction = newSymbol.pct_from_yesterday > oldSymbol.pct_from_yesterday ? 'up' : 'down'
          updatedSymbols.set(`${column}-${newSymbol.symbol}`, direction)
        }
      }
    })

    return updatedSymbols
  }

  // Fetch Discord juice box data
  useEffect(() => {
    const fetchDiscordJuice = async () => {
      try {
        const response = await fetch(`${API_URL}/discord/juice-boxes`)
        if (response.ok) {
          const data = await response.json()
          setDiscordJuiceBoxes(data)
        }
      } catch (error) {
        console.error('Failed to fetch Discord juice boxes:', error)
      }
    }

    fetchDiscordJuice()
    const interval = setInterval(fetchDiscordJuice, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        // Convert price filter to query param
        const priceParam = priceFilter !== 'all' ? `&price_filter=${priceFilter}` : ''

        // Map baseline filter to API parameter (skip "show_all" - use yesterday as default)
        const baselineParam = baselineFilter === 'show_all' ? 'yesterday' : baselineFilter

        const response = await fetch(
          `${API_URL}/symbols/leaderboard?threshold=${threshold}&baseline=${baselineParam}&direction=${gapDirection}${priceParam}`
        )
        if (response.ok) {
          const data = await response.json()
          const newData = {
            col_20_plus: data.col_20_plus || [],
            col_10_to_20: data.col_10_to_20 || [],
            col_1_to_10: data.col_1_to_10 || []
          }

          // Detect updates and trigger flash
          const updates = new Map<string, 'up' | 'down'>()
          detectUpdates(newData.col_20_plus, previousData.col_20_plus, 'col_20_plus').forEach((direction, key) => updates.set(key, direction))
          detectUpdates(newData.col_10_to_20, previousData.col_10_to_20, 'col_10_to_20').forEach((direction, key) => updates.set(key, direction))
          detectUpdates(newData.col_1_to_10, previousData.col_1_to_10, 'col_1_to_10').forEach((direction, key) => updates.set(key, direction))

          if (updates.size > 0) {
            setFlashingRows(updates)
            // Clear flashing state after animation completes
            setTimeout(() => setFlashingRows(new Map()), 2500)
          }

          setPreviousData(newData)
          setLeaderboardData(newData)
        }
      } catch (error) {
        console.error('Failed to fetch leaderboard:', error)
      }
    }

    fetchLeaderboard()
    const interval = setInterval(fetchLeaderboard, 2000)
    return () => clearInterval(interval)
  }, [threshold, priceFilter, baselineFilter, gapDirection, previousData])

  // Filter data based on search query
  const filterBySearch = (data: SymbolState[]) => {
    if (!searchQuery.trim()) return data
    const query = searchQuery.toUpperCase().trim()
    return data.filter(item => item.symbol.toUpperCase().includes(query))
  }

  const col20Plus = filterBySearch(leaderboardData.col_20_plus)
  const col10To20 = filterBySearch(leaderboardData.col_10_to_20)
  const col1To10 = filterBySearch(leaderboardData.col_1_to_10)

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
      case 'pre': return symbolState.pct_from_pre
      case 'open': return symbolState.pct_from_open
      case 'post': return symbolState.pct_from_post
      case '15min': return symbolState.pct_from_15min
      case '5min': return symbolState.pct_from_5min
      default: return symbolState.pct_from_yesterday
    }
  }

  // Format percentage in shortened format for SHOW ALL view
  const formatShortPct = (value: number | null) => {
    if (value === null) return '--'

    const absValue = Math.abs(value)

    // For values >= 1.0, show one decimal (42.52% -> 42.5)
    // For values < 1.0, drop leading zero (0.45% -> .45)
    if (absValue >= 1.0) {
      return absValue.toFixed(1)
    } else {
      // Remove leading zero: 0.45 -> .45
      return absValue.toFixed(2).replace(/^0\./, '.')
    }
  }

  // Sort function for "SHOW ALL" view - prioritize symbols with most positive columns
  const sortForShowAll = (data: SymbolState[]) => {
    return [...data].sort((a, b) => {
      // Count positive columns for each symbol (including PRE, POST, and 1min)
      const aPositive = [
        a.pct_from_yesterday,
        a.pct_from_pre,
        a.pct_from_open,
        a.pct_from_post,
        a.pct_from_15min,
        a.pct_from_5min,
        a.pct_from_1min
      ].filter(v => v !== null && v > 0).length

      const bPositive = [
        b.pct_from_yesterday,
        b.pct_from_pre,
        b.pct_from_open,
        b.pct_from_post,
        b.pct_from_15min,
        b.pct_from_5min,
        b.pct_from_1min
      ].filter(v => v !== null && v > 0).length

      // First priority: most positive columns
      if (aPositive !== bPositive) {
        return bPositive - aPositive
      }

      // Second priority: sum of all percentage moves (highest first)
      const aSum = (a.pct_from_yesterday || 0) + (a.pct_from_pre || 0) + (a.pct_from_open || 0) + (a.pct_from_post || 0) + (a.pct_from_15min || 0) + (a.pct_from_5min || 0) + (a.pct_from_1min || 0)
      const bSum = (b.pct_from_yesterday || 0) + (b.pct_from_pre || 0) + (b.pct_from_open || 0) + (b.pct_from_post || 0) + (b.pct_from_15min || 0) + (b.pct_from_5min || 0) + (b.pct_from_1min || 0)
      return bSum - aSum
    })
  }

  const renderColumn = (title: string, data: SymbolState[], colorClass: string, columnId: string) => {
    // Apply smart sorting based on current filter
    let sortedData = data

    if (baselineFilter === 'show_all') {
      // "SHOW ALL": Sort by most positive columns
      sortedData = sortForShowAll(data)
    } else {
      // Single timeframe: Sort by that specific timeframe's percentage
      // Descending order: +100% → +50% → +0.05% → 0.00% → -0.23% → -50%
      sortedData = [...data].sort((a, b) => {
        const aValue = getPercentValue(a, baselineFilter)
        const bValue = getPercentValue(b, baselineFilter)
        return bValue - aValue
      })
    }

    return (
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
          <div className="flex gap-2">
            <select
              value={gapDirection}
              onChange={(e) => setGapDirection(e.target.value as 'up' | 'down')}
              className="bg-gray-900 text-teal text-xs border border-glass rounded px-2 py-1 cursor-pointer hover:bg-gray-800 transition-colors"
            >
              <option value="up">GAP UPS</option>
              <option value="down">GAP DOWNS</option>
            </select>
            <select
              value={baselineFilter}
              onChange={(e) => setBaselineFilter(e.target.value as typeof baselineFilter)}
              className="bg-gray-900 text-teal text-xs border border-glass rounded px-2 py-1 cursor-pointer hover:bg-gray-800 transition-colors"
            >
              <option value="show_all">SHOW ALL</option>
              <option value="yesterday">% Yest</option>
              <option value="pre">% PRE</option>
              <option value="open">% OPEN</option>
              <option value="post">% POST</option>
              <option value="15min">% 15M</option>
              <option value="5min">% 5M</option>
            </select>
          </div>
        </div>
        {baselineFilter === 'show_all' && (
          <div className="flex items-start gap-3 mt-2 pt-2 border-t border-glass">
            {/* Empty space for column 1 (ticker/price/time) */}
            <div className="w-20 flex-shrink-0"></div>

            {/* Empty space for column 2 (icon) */}
            <div className="w-6 flex-shrink-0"></div>

            {/* Headers for columns 3-9 (added PRE, POST, and 1M) */}
            <div className="grid grid-cols-7 gap-2 flex-1 text-[10px] text-teal-dark uppercase text-center">
              <div>Yest</div>
              <div>PRE</div>
              <div>OPEN</div>
              <div>POST</div>
              <div>15M</div>
              <div>5M</div>
              <div>1M</div>
            </div>
          </div>
        )}
      </div>
      <div className="h-[500px] overflow-y-auto bg-black">
        {sortedData.length === 0 ? (
          <div className="text-center py-12 text-green-800 text-xs">
            No alerts in this range
          </div>
        ) : baselineFilter === 'show_all' ? (
          sortedData.map(symbolState => {
            const rowKey = `${columnId}-${symbolState.symbol}`
            const flashDirection = flashingRows.get(rowKey)
            const flashClass = flashDirection === 'up' ? 'row-flash-green' : flashDirection === 'down' ? 'row-flash-red' : ''
            return (
              <div
                key={symbolState.symbol}
                className={`border-b border-green-900 hover:bg-green-950/30 transition-colors p-2 text-xs flex items-start gap-3 ${flashClass}`}
              >
              {/* Column 1: Symbol, Price, Timestamp (stacked vertically) */}
              <div className="flex flex-col w-20 flex-shrink-0">
                <span className="font-bold text-green-300 text-sm mb-0.5">{symbolState.symbol}</span>
                <span className="text-green-700 text-xs mb-0.5">${symbolState.current_price.toFixed(2)}</span>
                <span className="text-green-700 text-[10px]">{formatTime(symbolState.last_updated)}</span>
              </div>

              {/* Column 2: Discord Icon (if applicable) */}
              <div className="w-6 flex-shrink-0 flex items-center justify-center">
                {discordJuiceBoxes[symbolState.symbol] >= 3 && (
                  <img
                    src="/images/icon-discord.png"
                    alt="Discord"
                    className="w-4 h-4 opacity-80"
                    title={`${discordJuiceBoxes[symbolState.symbol]} juice boxes on Discord`}
                  />
                )}
              </div>

              {/* Columns 3-9: 7 Percentage Columns (added PRE, POST, and 1M) */}
              <div className="grid grid-cols-7 gap-2 flex-1 text-center items-center">
                <span className={`font-bold text-xs ${symbolState.pct_from_yesterday >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatShortPct(symbolState.pct_from_yesterday)}
                </span>
                <span className={`font-bold text-xs ${symbolState.pct_from_pre !== null ? (symbolState.pct_from_pre >= 0 ? 'text-green-400' : 'text-red-400') : 'text-gray-600'}`}>
                  {formatShortPct(symbolState.pct_from_pre)}
                </span>
                <span className={`font-bold text-xs ${symbolState.pct_from_open >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatShortPct(symbolState.pct_from_open)}
                </span>
                <span className={`font-bold text-xs ${symbolState.pct_from_post !== null ? (symbolState.pct_from_post >= 0 ? 'text-green-400' : 'text-red-400') : 'text-gray-600'}`}>
                  {formatShortPct(symbolState.pct_from_post)}
                </span>
                <span className={`font-bold text-xs ${symbolState.pct_from_15min >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatShortPct(symbolState.pct_from_15min)}
                </span>
                <span className={`font-bold text-xs ${symbolState.pct_from_5min >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatShortPct(symbolState.pct_from_5min)}
                </span>
                <span className={`font-bold text-xs ${symbolState.pct_from_1min >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatShortPct(symbolState.pct_from_1min)}
                </span>
              </div>
            </div>
            )
          })
        ) : (
          sortedData.map(symbolState => {
            const pctValue = getPercentValue(symbolState, baselineFilter)
            const rowKey = `${columnId}-${symbolState.symbol}`
            const flashDirection = flashingRows.get(rowKey)
            const flashClass = flashDirection === 'up' ? 'row-flash-green' : flashDirection === 'down' ? 'row-flash-red' : ''
            return (
              <div
                key={symbolState.symbol}
                className={`border-b border-green-900 hover:bg-green-950/30 transition-colors p-2 text-xs flex items-center ${flashClass}`}
              >
                {/* Column 1: Ticker + Price (2 rows stacked) */}
                <div className="flex flex-col w-16 flex-shrink-0">
                  <span className="font-bold text-green-300 text-sm mb-0.5">{symbolState.symbol}</span>
                  <span className="text-green-700 text-xs">${symbolState.current_price.toFixed(2)}</span>
                </div>

                {/* Column 2: Discord Icon */}
                <div className="w-6 flex-shrink-0 flex items-center justify-center">
                  {discordJuiceBoxes[symbolState.symbol] >= 3 && (
                    <img
                      src="/images/icon-discord.png"
                      alt="Discord"
                      className="w-6 h-6 opacity-80"
                      title={`${discordJuiceBoxes[symbolState.symbol]} juice boxes on Discord`}
                    />
                  )}
                </div>

                {/* Column 3: Percentage + Time (2 rows stacked, right-aligned) */}
                <div className="flex flex-col flex-1 items-end">
                  <span className={`font-bold text-sm mb-0.5 ${pctValue !== null ? colorClass : 'text-gray-600'}`}>
                    {pctValue !== null ? `${pctValue > 0 ? '+' : ''}${pctValue.toFixed(2)}%` : '--'}
                  </span>
                  <span className="text-green-700 text-xs">{formatTime(symbolState.last_updated)}</span>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
    )
  }

  return (
    <div className="mb-6">
      {/* Desktop: 3 columns side by side */}
      <div className="hidden md:grid md:grid-cols-3 gap-4">
        {renderColumn('20%+', col20Plus, 'text-red-400', 'col_20_plus')}
        {renderColumn('10-20%', col10To20, 'text-yellow-400', 'col_10_to_20')}
        {renderColumn('1-10%', col1To10, 'text-green-400', 'col_1_to_10')}
      </div>

      {/* Mobile: Single column view with hint */}
      <div className="md:hidden">
        <div className="overflow-hidden">
          <div className="snap-start shrink-0 w-full">
            {renderColumn('20%+', col20Plus, 'text-red-400', 'col_20_plus')}
          </div>
        </div>
        <p className="text-center text-xs text-green-700 mt-2">
          Swipe right on table below to see 10-20% and 1-10% segments
        </p>
      </div>
    </div>
  )
}
