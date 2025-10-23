'use client'

import { useEffect, useState } from 'react'
import { formatDistanceToNow } from 'date-fns'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Alert {
  id: string
  symbol: string
  alert_type: string
  trigger_price: number
  trigger_time: string
  pct_move: number
  conditions?: {
    pct_move: number
    previous_close: number
  }
  metadata: any
}

interface SymbolState {
  symbol: string
  current_price: number
  pct_from_yesterday: number
  pct_from_open: number
  pct_from_15min: number
  pct_from_5min: number
  hod_pct: number
}

interface AlertsListProps {
  threshold?: number
  priceFilter?: 'all' | 'small' | 'mid' | 'large'
  alerts: Alert[]
}

export function AlertsList({ threshold = 0, priceFilter = 'all', alerts: propsAlerts }: AlertsListProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isPaused, setIsPaused] = useState(false)
  const [queuedAlerts, setQueuedAlerts] = useState<Alert[]>([])
  const [displayAlerts, setDisplayAlerts] = useState<Alert[]>(propsAlerts)
  const [symbolStates, setSymbolStates] = useState<Map<string, SymbolState>>(new Map())

  useEffect(() => {
    if (isPaused) {
      setQueuedAlerts(propsAlerts)
    } else {
      setDisplayAlerts(propsAlerts)
    }
  }, [propsAlerts, isPaused])

  // Fetch symbol states for all visible alerts
  useEffect(() => {
    const fetchSymbolStates = async () => {
      try {
        // Get unique symbols from displayed alerts
        const symbols = [...new Set(displayAlerts.map(a => a.symbol))]
        if (symbols.length === 0) return

        // Fetch state for all symbols
        const response = await fetch(`${API_URL}/symbols/state?threshold=0&limit=500`)
        if (response.ok) {
          const states: SymbolState[] = await response.json()
          const stateMap = new Map<string, SymbolState>()
          states.forEach(state => stateMap.set(state.symbol, state))
          setSymbolStates(stateMap)
        }
      } catch (error) {
        console.error('Failed to fetch symbol states:', error)
      }
    }

    fetchSymbolStates()
    const interval = setInterval(fetchSymbolStates, 2000)
    return () => clearInterval(interval)
  }, [displayAlerts])

  const handlePauseToggle = () => {
    if (isPaused) {
      // Resume: show queued alerts
      if (queuedAlerts.length > 0) {
        setDisplayAlerts(queuedAlerts)
        setQueuedAlerts([])
      }
    }
    setIsPaused(!isPaused)
  }

  // Apply price filter
  const filterByPrice = (alert: Alert) => {
    const price = alert.trigger_price
    if (priceFilter === 'small') return price < 20
    if (priceFilter === 'mid') return price >= 20 && price < 100
    if (priceFilter === 'large') return price >= 100
    return true
  }

  // Deduplicate: Keep only the latest alert per symbol
  const deduplicatedAlerts = displayAlerts.reduce((acc, alert) => {
    const existing = acc.find(a => a.symbol === alert.symbol)
    if (!existing) {
      acc.push(alert)
    } else {
      // Keep the one with the most recent timestamp
      if (new Date(alert.trigger_time) > new Date(existing.trigger_time)) {
        const index = acc.indexOf(existing)
        acc[index] = alert
      }
    }
    return acc
  }, [] as Alert[])

  // Filter alerts based on threshold and price
  const filteredAlerts = deduplicatedAlerts
    .filter(alert => Math.abs(alert.pct_move) >= threshold)
    .filter(filterByPrice)

  if (displayAlerts.length === 0) {
    return (
      <div className="text-center py-8 text-green-700">
        No alerts yet. The screener may not be running.
      </div>
    )
  }

  if (filteredAlerts.length === 0) {
    return (
      <div className="bg-gray-950 border border-green-800 rounded overflow-hidden">
        <div className="px-6 py-4 border-b border-green-800 bg-gray-900 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-green-400">⚡ RECENT ALERTS</h2>
          <button
            onClick={handlePauseToggle}
            className={`px-4 py-2 rounded font-medium transition-colors border ${
              isPaused
                ? 'bg-green-900 hover:bg-green-800 text-green-400 border-green-700'
                : 'bg-gray-800 hover:bg-gray-700 text-green-500 border-green-800'
            }`}
          >
            {isPaused ? '▶ Resume' : '⏸ Pause'}
          </button>
        </div>
        <div className="text-center py-12 text-yellow-600">
          <div className="text-4xl mb-3">🔍</div>
          <div className="text-yellow-500">No alerts match the {threshold.toFixed(1)}% threshold</div>
          <div className="text-sm mt-2 text-yellow-800">
            {alerts.length} total alerts available. Lower the threshold to see more.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-950 border border-green-800 rounded overflow-hidden">
      <div className="px-4 md:px-6 py-3 md:py-4 border-b border-green-800 bg-gray-900 flex items-center justify-between">
        <div className="flex-1">
          <h2 className="text-lg md:text-xl font-semibold text-green-400">RECENT ALERTS</h2>
          {threshold > 0 && (
            <p className="text-xs text-green-700 mt-1">
              Showing {filteredAlerts.length} of {displayAlerts.length} alerts (≥{threshold.toFixed(1)}%)
            </p>
          )}
        </div>
        <button
          onClick={handlePauseToggle}
          className={`px-2 md:px-4 py-1.5 md:py-2 rounded text-sm font-medium transition-colors border ${
            isPaused
              ? 'bg-green-900 hover:bg-green-800 text-green-400 border-green-700'
              : 'bg-gray-800 hover:bg-gray-700 text-green-500 border-green-800'
          }`}
          aria-label={isPaused ? 'Resume' : 'Pause'}
        >
          {isPaused ? '▶' : '⏸'}
        </button>
      </div>
      {isPaused && queuedAlerts.length > 0 && (
        <div className="px-6 py-2 bg-yellow-900 text-yellow-200 text-sm border-b border-green-900">
          ⏸ Stream paused. {queuedAlerts.length} new alerts waiting. Click Resume to update.
        </div>
      )}

      <div className="overflow-x-auto -mx-px">
        <table className="w-full min-w-max">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-2 md:px-4 py-2 md:py-3 text-left text-[10px] md:text-xs font-medium text-green-600 uppercase tracking-wider border-b border-green-900 whitespace-nowrap">
                Symbol
              </th>
              <th className="px-2 md:px-4 py-2 md:py-3 text-left text-[10px] md:text-xs font-medium text-green-600 uppercase tracking-wider border-b border-green-900 whitespace-nowrap">
                Type
              </th>
              <th className="px-2 md:px-4 py-2 md:py-3 text-left text-[10px] md:text-xs font-medium text-green-600 uppercase tracking-wider border-b border-green-900 whitespace-nowrap">
                Price
              </th>
              <th className="px-2 md:px-3 py-2 md:py-3 text-left text-[10px] md:text-xs font-medium text-green-600 uppercase tracking-wider border-b border-green-900 whitespace-nowrap">
                % Yest
              </th>
              <th className="px-2 md:px-3 py-2 md:py-3 text-left text-[10px] md:text-xs font-medium text-green-600 uppercase tracking-wider border-b border-green-900 whitespace-nowrap">
                % Open
              </th>
              <th className="px-2 md:px-3 py-2 md:py-3 text-left text-[10px] md:text-xs font-medium text-green-600 uppercase tracking-wider border-b border-green-900 whitespace-nowrap">
                % 15m
              </th>
              <th className="px-2 md:px-3 py-2 md:py-3 text-left text-[10px] md:text-xs font-medium text-green-600 uppercase tracking-wider border-b border-green-900 whitespace-nowrap">
                % 5m
              </th>
              <th className="px-2 md:px-3 py-2 md:py-3 text-left text-[10px] md:text-xs font-medium text-green-600 uppercase tracking-wider border-b border-green-900 whitespace-nowrap">
                HOD %
              </th>
              <th className="px-2 md:px-3 py-2 md:py-3 text-left text-[10px] md:text-xs font-medium text-green-600 uppercase tracking-wider border-b border-green-900 whitespace-nowrap">
                Time
              </th>
            </tr>
          </thead>
          <tbody className="bg-black">
            {filteredAlerts.map((alert) => {
              const state = symbolStates.get(alert.symbol)
              return (
                <tr
                  key={alert.id}
                  className="border-b border-green-900 hover:bg-green-950/30 transition-colors"
                >
                  <td className="px-2 md:px-4 py-2 md:py-4 whitespace-nowrap font-medium text-green-300 text-sm">
                    {alert.symbol}
                  </td>
                  <td className="px-2 md:px-4 py-2 md:py-4 whitespace-nowrap">
                    <span
                      className={`px-1.5 md:px-2 py-0.5 md:py-1 text-[10px] md:text-xs rounded border ${
                        alert.alert_type === 'gap_up'
                          ? 'bg-green-900/50 text-green-400 border-green-700'
                          : 'bg-red-900/50 text-red-400 border-red-700'
                      }`}
                    >
                      {alert.alert_type}
                    </span>
                  </td>
                  <td className="px-2 md:px-4 py-2 md:py-4 whitespace-nowrap text-green-400 text-sm">
                    ${(state?.current_price || alert.trigger_price).toFixed(2)}
                  </td>
                  <td
                    className={`px-2 md:px-3 py-2 md:py-4 whitespace-nowrap font-semibold text-sm ${
                      (state?.pct_from_yesterday || alert.pct_move) > 0 ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    {(state?.pct_from_yesterday || alert.pct_move) > 0 ? '+' : ''}
                    {(state?.pct_from_yesterday || alert.pct_move).toFixed(2)}%
                  </td>
                  <td
                    className={`px-2 md:px-3 py-2 md:py-4 whitespace-nowrap font-semibold text-sm ${
                      (state?.pct_from_open || 0) > 0 ? 'text-green-400' : state?.pct_from_open ? 'text-red-400' : 'text-gray-600'
                    }`}
                  >
                    {state?.pct_from_open !== null && state?.pct_from_open !== undefined ? (
                      <>
                        {state.pct_from_open > 0 ? '+' : ''}
                        {state.pct_from_open.toFixed(2)}%
                      </>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td
                    className={`px-2 md:px-3 py-2 md:py-4 whitespace-nowrap font-semibold text-sm ${
                      (state?.pct_from_15min || 0) > 0 ? 'text-green-400' : state?.pct_from_15min ? 'text-red-400' : 'text-gray-600'
                    }`}
                  >
                    {state?.pct_from_15min !== null && state?.pct_from_15min !== undefined ? (
                      <>
                        {state.pct_from_15min > 0 ? '+' : ''}
                        {state.pct_from_15min.toFixed(2)}%
                      </>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td
                    className={`px-2 md:px-3 py-2 md:py-4 whitespace-nowrap font-semibold text-sm ${
                      (state?.pct_from_5min || 0) > 0 ? 'text-green-400' : state?.pct_from_5min ? 'text-red-400' : 'text-gray-600'
                    }`}
                  >
                    {state?.pct_from_5min !== null && state?.pct_from_5min !== undefined ? (
                      <>
                        {state.pct_from_5min > 0 ? '+' : ''}
                        {state.pct_from_5min.toFixed(2)}%
                      </>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td
                    className={`px-2 md:px-3 py-2 md:py-4 whitespace-nowrap font-bold text-sm ${
                      (state?.hod_pct || 0) > 0 ? 'text-yellow-400' : state?.hod_pct ? 'text-red-400' : 'text-gray-600'
                    }`}
                  >
                    {state?.hod_pct !== null && state?.hod_pct !== undefined ? (
                      <>
                        {state.hod_pct > 0 ? '+' : ''}
                        {state.hod_pct.toFixed(2)}%
                      </>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td className="px-2 md:px-3 py-2 md:py-4 whitespace-nowrap text-xs md:text-sm text-green-700">
                    {(() => {
                      const date = new Date(alert.trigger_time)
                      const now = new Date()
                      const diffMs = now.getTime() - date.getTime()
                      const diffMin = Math.floor(diffMs / 60000)

                      if (diffMin < 1) return '1 min ago'
                      if (diffMin < 60) return `${diffMin} min ago`
                      const diffHours = Math.floor(diffMin / 60)
                      if (diffHours < 24) return `${diffHours}h ago`
                      return `${Math.floor(diffHours / 24)}d ago`
                    })()}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
