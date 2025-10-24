'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

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

interface DataContextType {
  alerts: Alert[]
  stats: any
  leaderboardCounts: { movers_20plus: number; movers_10to20: number; movers_1to10: number }
  loadingStatus: string
  isLoading: boolean
  priceUpdates: any[]
  realtimePrices: Map<string, any>
}

const DataContext = createContext<DataContextType | undefined>(undefined)

export function DataProvider({ children }: { children: ReactNode }) {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [stats, setStats] = useState<any>(null)
  const [leaderboardCounts, setLeaderboardCounts] = useState({ movers_20plus: 0, movers_10to20: 0, movers_1to10: 0 })
  const [loadingStatus, setLoadingStatus] = useState<string>('Connecting to server...')
  const [isLoading, setIsLoading] = useState(true)
  const [priceUpdates, setPriceUpdates] = useState<any[]>([])
  const [realtimePrices, setRealtimePrices] = useState<Map<string, any>>(new Map())
  const [retryCount, setRetryCount] = useState(0)
  const maxRetries = 3

  useEffect(() => {
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
          setIsLoading(false)
          hasLoadedOnce = true
        }
        setRetryCount(0)
      } catch (err: any) {
        console.error('Stats fetch error:', err)
        if (retryCount < maxRetries) {
          setRetryCount(prev => prev + 1)
          setLoadingStatus(`Connection issue - retrying (${retryCount + 1}/${maxRetries})...`)
        } else {
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
      } catch (err: any) {
        console.error('Failed to fetch leaderboard counts:', err)
      }
    }

    // Fetch alerts
    const fetchAlerts = async () => {
      try {
        const response = await fetch(`${API_URL}/alerts?limit=100`)
        if (!response.ok) throw new Error('Failed to fetch alerts')
        const data = await response.json()
        setAlerts(data)
      } catch (err: any) {
        console.error('Failed to fetch alerts:', err)
      }
    }

    // Fetch price updates
    const fetchPrices = async () => {
      try {
        const response = await fetch(`${API_URL}/prices/recent?limit=20`)
        if (response.ok) {
          const data = await response.json()
          setPriceUpdates(data)
        }
      } catch (error) {
        console.error('Failed to fetch prices:', error)
      }
    }

    // Initial parallel fetch
    Promise.all([fetchStats(), fetchLeaderboardCounts(), fetchAlerts(), fetchPrices()])

    // Refresh intervals (keep for fallback)
    const alertInterval = setInterval(fetchAlerts, 2000)
    const leaderboardInterval = setInterval(fetchLeaderboardCounts, 2000)
    const statsInterval = setInterval(fetchStats, 30000)
    const pricesInterval = setInterval(fetchPrices, 2000)

    // WebSocket connection for real-time price updates
    let ws: WebSocket | null = null
    const connectWebSocket = () => {
      try {
        const wsUrl = API_URL.replace('http', 'ws')
        ws = new WebSocket(`${wsUrl}/ws/prices`)

        ws.onopen = () => {
          console.log('WebSocket connected for real-time prices')
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'price_update' && data.data) {
              // Update the realtime prices map
              setRealtimePrices(prev => {
                const newMap = new Map(prev)
                newMap.set(data.data.symbol, {
                  price: data.data.price,
                  bid: data.data.bid,
                  ask: data.data.ask,
                  pct_from_yesterday: data.data.pct_from_yesterday,
                  timestamp: data.data.timestamp
                })
                return newMap
              })
            }
          } catch (err) {
            console.error('Error parsing WebSocket message:', err)
          }
        }

        ws.onerror = (error) => {
          console.error('WebSocket error:', error)
        }

        ws.onclose = () => {
          console.log('WebSocket closed, will reconnect in 5s')
          setTimeout(connectWebSocket, 5000)
        }
      } catch (err) {
        console.error('Failed to connect WebSocket:', err)
      }
    }

    connectWebSocket()

    return () => {
      clearInterval(alertInterval)
      clearInterval(leaderboardInterval)
      clearInterval(statsInterval)
      clearInterval(pricesInterval)
      if (ws) {
        ws.close()
      }
    }
  }, [retryCount])

  return (
    <DataContext.Provider
      value={{
        alerts,
        stats,
        leaderboardCounts,
        loadingStatus,
        isLoading,
        priceUpdates,
        realtimePrices
      }}
    >
      {children}
    </DataContext.Provider>
  )
}

export function useData() {
  const context = useContext(DataContext)
  if (context === undefined) {
    throw new Error('useData must be used within a DataProvider')
  }
  return context
}
