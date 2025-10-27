'use client'

import { useEffect, useRef, useState } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const AI_API_URL = 'http://localhost:8002'

interface StockChartProps {
  symbol: string
  dataMode?: 'live' | 'historical'
}

interface BarData {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface Position {
  id: string
  symbol: string
  side: 'long' | 'short'
  quantity: number
  entry_price: number
  current_price: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  realized_pnl: number
  total_pnl: number
  entry_time: string
  status: string
}

export default function StockChart({ symbol, dataMode = 'live' }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const candlestickSeriesRef = useRef<any>(null)
  const positionLineRef = useRef<any>(null)
  const bosLinesRef = useRef<any[]>([]) // Track BoS indicator lines
  const chochLinesRef = useRef<any[]>([]) // Track CHoCH indicator lines
  const wsRef = useRef<WebSocket | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [position, setPosition] = useState<Position | null>(null)
  const [historicalData, setHistoricalData] = useState<any[]>([])
  const [replayStatus, setReplayStatus] = useState<{
    isPlaying: boolean
    currentIndex: number
    totalBars: number
    progress: number
  }>({ isPlaying: false, currentIndex: 0, totalBars: 0, progress: 0 })

  // Initialize chart once when component mounts
  useEffect(() => {
    if (!chartContainerRef.current) return

    let isMounted = true
    let chart: any = null
    let candlestickSeries: any = null

    const initChart = async () => {
      try {
        // Import chart library
        const { createChart, ColorType, CandlestickSeries } = await import('lightweight-charts')

        if (!isMounted || !chartContainerRef.current) return

        console.log('Creating chart for', symbol)

        // Create chart
        chart = createChart(chartContainerRef.current, {
          layout: {
            background: { type: ColorType.Solid, color: '#030712' },
            textColor: '#9CA3AF',
          },
          grid: {
            vertLines: { color: '#1F2937' },
            horzLines: { color: '#1F2937' },
          },
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
          timeScale: {
            timeVisible: true,
            secondsVisible: false,
          },
        })

        chartRef.current = chart

        // Add candlestick series
        candlestickSeries = chart.addSeries(CandlestickSeries, {
          upColor: '#10B981',
          downColor: '#EF4444',
          borderUpColor: '#10B981',
          borderDownColor: '#EF4444',
          wickUpColor: '#10B981',
          wickDownColor: '#EF4444',
        })

        candlestickSeriesRef.current = candlestickSeries

        // Handle resize
        const handleResize = () => {
          if (chartContainerRef.current && chart) {
            chart.applyOptions({
              width: chartContainerRef.current.clientWidth,
              height: chartContainerRef.current.clientHeight,
            })
          }
        }

        window.addEventListener('resize', handleResize)

        console.log('Chart created successfully!')
        setIsLoading(false)
      } catch (err: any) {
        if (!isMounted) return
        console.error('Error initializing chart:', err)
        setError(`Failed to load chart: ${err.message}`)
        setIsLoading(false)
      }
    }

    initChart()

    return () => {
      isMounted = false
      if (chart) {
        chart.remove()
        chartRef.current = null
        candlestickSeriesRef.current = null
      }
    }
  }, [symbol])

  // Fetch position data
  useEffect(() => {
    if (!symbol) return

    let intervalId: NodeJS.Timeout

    const fetchPosition = async () => {
      try {
        const response = await fetch(`${AI_API_URL}/position/${symbol}`)
        if (!response.ok) return

        const data = await response.json()
        setPosition(data.position)
      } catch (err) {
        console.error('Error fetching position:', err)
      }
    }

    // Initial fetch
    fetchPosition()

    // Poll every 1 second for live P&L updates
    intervalId = setInterval(fetchPosition, 1000)

    return () => {
      if (intervalId) clearInterval(intervalId)
    }
  }, [symbol])

  // Update position line when position changes
  useEffect(() => {
    if (!chartRef.current || !candlestickSeriesRef.current) {
      console.log('[Position Line] Chart not ready yet', {
        chart: !!chartRef.current,
        series: !!candlestickSeriesRef.current
      })
      return
    }

    console.log('[Position Line] Position data:', position)

    // Remove existing position line
    if (positionLineRef.current) {
      candlestickSeriesRef.current.removePriceLine(positionLineRef.current)
      positionLineRef.current = null
      console.log('[Position Line] Removed old position line')
    }

    // Add new position line if position exists
    if (position) {
      const color = position.side === 'short' ? '#EAB308' : '#A855F7' // Yellow for short, purple for long
      const pnlDirection = position.unrealized_pnl >= 0 ? 'up' : 'down'
      const pnlSign = position.unrealized_pnl >= 0 ? '+' : ''

      console.log('[Position Line] Creating line at price:', position.entry_price, 'color:', color)

      positionLineRef.current = candlestickSeriesRef.current.createPriceLine({
        price: position.entry_price,
        color: color,
        lineWidth: 2,
        lineStyle: 0, // Solid
        axisLabelVisible: true,
        title: `${position.side} ${position.quantity} ${pnlDirection} ${pnlSign}$${Math.abs(position.unrealized_pnl).toFixed(2)}`,
      })

      console.log('[Position Line] Line created successfully')
    }
  }, [position, chartRef.current, candlestickSeriesRef.current])

  // Fetch and update data periodically (every 5 seconds for live, once for historical)
  useEffect(() => {
    if (!candlestickSeriesRef.current) return

    let intervalId: NodeJS.Timeout

    const fetchData = async () => {
      try {
        // Choose endpoint based on data mode
        // For historical mode, request all available bars (API caps at 10000)
        const endpoint = dataMode === 'historical'
          ? `${API_URL}/bars/${symbol}/historical?limit=10000`
          : `${API_URL}/bars/${symbol}?limit=500`

        const response = await fetch(endpoint)
        if (!response.ok) {
          throw new Error(`Failed to fetch bar data: ${response.statusText}`)
        }

        const bars: BarData[] = await response.json()
        console.log(`[${new Date().toLocaleTimeString()}] Fetched ${bars.length} ${dataMode} bars for ${symbol}`)

        if (!bars || bars.length === 0) {
          setError(`No ${dataMode} chart data available for ${symbol}`)
          return
        }

        // Transform data for chart format
        const chartData = bars.map(bar => ({
          time: Math.floor(new Date(bar.timestamp).getTime() / 1000) as any,
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
        }))

        // Sort by time ascending
        chartData.sort((a, b) => a.time - b.time)

        if (candlestickSeriesRef.current) {
          candlestickSeriesRef.current.setData(chartData)
          chartRef.current?.timeScale().fitContent()
          setError(null)
        }
      } catch (err: any) {
        console.error('Error fetching chart data:', err)
        setError(`Failed to update chart: ${err.message}`)
      }
    }

    // Initial fetch
    fetchData()

    // Poll every 5 seconds only for live data
    if (dataMode === 'live') {
      intervalId = setInterval(fetchData, 5000)
    }

    return () => {
      if (intervalId) clearInterval(intervalId)
    }
  }, [symbol, dataMode, candlestickSeriesRef.current])

  // Fetch and display SMC indicators (BoS and CHoCH)
  useEffect(() => {
    if (!candlestickSeriesRef.current) return

    let intervalId: NodeJS.Timeout

    const fetchIndicators = async () => {
      try {
        const response = await fetch(`${AI_API_URL}/indicators/${symbol}?lookback=200`)
        if (!response.ok) return

        const data = await response.json()
        console.log(`[${new Date().toLocaleTimeString()}] Fetched indicators:`, {
          bos: data.bos_levels?.length || 0,
          choch: data.choch_levels?.length || 0
        })

        // Remove existing indicator lines
        bosLinesRef.current.forEach(line => {
          if (candlestickSeriesRef.current) {
            candlestickSeriesRef.current.removePriceLine(line)
          }
        })
        chochLinesRef.current.forEach(line => {
          if (candlestickSeriesRef.current) {
            candlestickSeriesRef.current.removePriceLine(line)
          }
        })
        bosLinesRef.current = []
        chochLinesRef.current = []

        // Draw BoS levels (white lines)
        if (data.bos_levels) {
          data.bos_levels.forEach((level: any) => {
            if (!candlestickSeriesRef.current) return

            const line = candlestickSeriesRef.current.createPriceLine({
              price: level.price,
              color: '#FFFFFF',
              lineWidth: 2,
              lineStyle: 0, // Solid
              axisLabelVisible: true,
              title: `BoS ${level.type} (${level.confidence.toFixed(1)})`,
            })
            bosLinesRef.current.push(line)
            console.log(`  ✓ BoS ${level.type} at $${level.price.toFixed(4)} (confidence: ${level.confidence})`)
          })
        }

        // Draw CHoCH levels (cyan lines)
        if (data.choch_levels) {
          data.choch_levels.forEach((level: any) => {
            if (!candlestickSeriesRef.current) return

            const line = candlestickSeriesRef.current.createPriceLine({
              price: level.price,
              color: '#00FFFF',
              lineWidth: 2,
              lineStyle: 0, // Solid
              axisLabelVisible: true,
              title: `CHoCH (${level.confidence.toFixed(1)})`,
            })
            chochLinesRef.current.push(line)
            console.log(`  ✓ CHoCH at $${level.price.toFixed(4)} (confidence: ${level.confidence})`)
          })
        }
      } catch (err) {
        console.error('Error fetching indicators:', err)
      }
    }

    // Initial fetch
    fetchIndicators()

    // Poll every 5 seconds for indicator updates
    intervalId = setInterval(fetchIndicators, 5000)

    return () => {
      if (intervalId) clearInterval(intervalId)
      // Clean up indicator lines
      bosLinesRef.current.forEach(line => {
        if (candlestickSeriesRef.current) {
          candlestickSeriesRef.current.removePriceLine(line)
        }
      })
      chochLinesRef.current.forEach(line => {
        if (candlestickSeriesRef.current) {
          candlestickSeriesRef.current.removePriceLine(line)
        }
      })
      bosLinesRef.current = []
      chochLinesRef.current = []
    }
  }, [symbol, candlestickSeriesRef.current])

  return (
    <div className="h-full w-full relative bg-gray-950">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-950 z-10">
          <div className="text-gray-400">Loading chart for {symbol}...</div>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-950 z-10">
          <div className="text-red-400">{error}</div>
        </div>
      )}
      <div ref={chartContainerRef} className="h-full w-full" />
    </div>
  )
}
