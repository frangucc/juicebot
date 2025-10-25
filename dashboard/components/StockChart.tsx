'use client'

import { useEffect, useRef, useState } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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

export default function StockChart({ symbol, dataMode = 'live' }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const candlestickSeriesRef = useRef<any>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
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

  // Fetch and update data periodically (every 5 seconds for live, once for historical)
  useEffect(() => {
    if (!candlestickSeriesRef.current) return

    let intervalId: NodeJS.Timeout

    const fetchData = async () => {
      try {
        // Choose endpoint based on data mode
        const endpoint = dataMode === 'historical'
          ? `${API_URL}/bars/${symbol}/historical?limit=1000`
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
