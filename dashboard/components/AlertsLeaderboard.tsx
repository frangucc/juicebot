'use client'

import { useEffect, useState } from 'react'

interface Alert {
  id: string
  symbol: string
  trigger_price: number
  trigger_time: string
  pct_move: number
  conditions?: {
    pct_move: number
    previous_close: number
  }
}

interface LivePrice {
  symbol: string
  mid: number
  timestamp: string
}

interface AlertsLeaderboardProps {
  alerts: Alert[]
  threshold: number
  priceFilter: 'all' | 'small' | 'mid' | 'large'
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function AlertsLeaderboard({ alerts, threshold, priceFilter }: AlertsLeaderboardProps) {
  const [livePrices, setLivePrices] = useState<LivePrice[]>([])

  useEffect(() => {
    const fetchLivePrices = async () => {
      try {
        const response = await fetch(`${API_URL}/prices/recent?limit=200`)
        if (response.ok) {
          const data = await response.json()
          setLivePrices(data)
        }
      } catch (error) {
        console.error('Failed to fetch live prices:', error)
      }
    }

    fetchLivePrices()
    const interval = setInterval(fetchLivePrices, 2000)
    return () => clearInterval(interval)
  }, [])
  // Apply price filter
  const filterByPrice = (alert: Alert) => {
    const price = alert.trigger_price
    if (priceFilter === 'small') return price < 20
    if (priceFilter === 'mid') return price >= 20 && price < 100
    if (priceFilter === 'large') return price >= 100
    return true
  }

  // Calculate current % move for each alert using live prices
  const alertsWithLiveMove = alerts.map(alert => {
    // Find latest live price for this symbol
    const livePrice = livePrices.find(p => p.symbol === alert.symbol)

    if (!livePrice) {
      // No live price, use alert data
      return { ...alert, currentPrice: alert.trigger_price, currentMove: alert.pct_move }
    }

    // Calculate current % move from baseline (previous_close)
    const baseline = alert.conditions?.previous_close || alert.trigger_price
    const currentMove = ((livePrice.mid - baseline) / baseline) * 100

    return {
      ...alert,
      currentPrice: livePrice.mid,
      currentMove: currentMove
    }
  })

  // Deduplicate by symbol, keep most recent alert
  const deduped = alertsWithLiveMove.reduce((acc, alert) => {
    const existing = acc.find(a => a.symbol === alert.symbol)
    if (!existing) {
      acc.push(alert)
    } else if (new Date(alert.trigger_time) > new Date(existing.trigger_time)) {
      const index = acc.indexOf(existing)
      acc[index] = alert
    }
    return acc
  }, [] as typeof alertsWithLiveMove)

  // Apply filters using CURRENT move %
  const filtered = deduped
    .filter(alert => Math.abs(alert.currentMove) >= threshold)
    .filter(alert => filterByPrice(alert))

  // Categorize into columns using CURRENT move %
  const col20Plus = filtered.filter(a => Math.abs(a.currentMove) >= 20).sort((a, b) => Math.abs(b.currentMove) - Math.abs(a.currentMove))
  const col10To20 = filtered.filter(a => Math.abs(a.currentMove) >= 10 && Math.abs(a.currentMove) < 20).sort((a, b) => Math.abs(b.currentMove) - Math.abs(a.currentMove))
  const col1To10 = filtered.filter(a => Math.abs(a.currentMove) >= 1 && Math.abs(a.currentMove) < 10).sort((a, b) => Math.abs(b.currentMove) - Math.abs(a.currentMove))

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

  const renderColumn = (title: string, icon: string, data: Alert[], colorClass: string) => (
    <div className="bg-gray-950 border border-green-800 rounded overflow-hidden flex-1">
      <div className="p-3 border-b border-green-800 bg-gray-900">
        <h3 className="text-sm font-bold text-green-400">
          {icon} {title}
        </h3>
        <p className="text-xs text-green-700">
          {data.length} active
        </p>
      </div>
      <div className="h-[500px] overflow-y-auto bg-black">
        {data.length === 0 ? (
          <div className="text-center py-12 text-green-800 text-xs">
            No alerts in this range
          </div>
        ) : (
          data.map(alert => (
            <div
              key={alert.id}
              className="border-b border-green-900 hover:bg-green-950/30 transition-colors p-2 text-xs"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-green-300">{alert.symbol}</span>
                <span className={`font-bold ${colorClass}`}>
                  {alert.currentMove > 0 ? '+' : ''}{alert.currentMove.toFixed(2)}%
                </span>
              </div>
              <div className="flex items-center justify-between text-green-700">
                <span>${alert.currentPrice.toFixed(2)}</span>
                <span>{formatTime(alert.trigger_time)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )

  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      {renderColumn('20%+', '🔥', col20Plus, 'text-red-400')}
      {renderColumn('10-20%', '⚡', col10To20, 'text-yellow-400')}
      {renderColumn('1-10%', '📊', col1To10, 'text-green-400')}
    </div>
  )
}
