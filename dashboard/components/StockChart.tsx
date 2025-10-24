'use client'

import { useEffect, useRef, useState } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface StockChartProps {
  symbol: string
}

interface BarData {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export default function StockChart({ symbol }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const candlestickSeriesRef = useRef<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Initialize chart once and fetch data when symbol changes
  useEffect(() => {
    if (!chartContainerRef.current) return

    let isMounted = true
    let chart: any = null
    let candlestickSeries: any = null

    const initChartAndData = async () => {
      try {
        // Import chart library
        const { createChart, ColorType, CandlestickSeries } = await import('lightweight-charts')

        if (!isMounted || !chartContainerRef.current) return

        console.log('Creating chart for', symbol)
        console.log('Container dimensions:', chartContainerRef.current.clientWidth, 'x', chartContainerRef.current.clientHeight)

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

        console.log('Chart created, fetching data...')

        // Fetch bar data
        const response = await fetch(`${API_URL}/bars/${symbol}?limit=500`)
        if (!response.ok) {
          throw new Error(`Failed to fetch bar data: ${response.statusText}`)
        }

        const bars: BarData[] = await response.json()
        console.log(`Received ${bars.length} bars for ${symbol}`)

        if (!isMounted) return

        if (!bars || bars.length === 0) {
          setError(`No chart data available for ${symbol}`)
          setIsLoading(false)
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

        console.log('Chart data sample:', chartData.slice(0, 3))

        if (candlestickSeries && isMounted) {
          console.log('Setting data on chart...')
          candlestickSeries.setData(chartData)
          chart?.timeScale().fitContent()
          console.log('Data set successfully!')
          setIsLoading(false)
          setError(null)
        }
      } catch (err: any) {
        if (!isMounted) return
        console.error('Error initializing chart:', err)
        setError(`Failed to load chart: ${err.message}`)
        setIsLoading(false)
      }
    }

    initChartAndData()

    return () => {
      isMounted = false
      if (chart) {
        chart.remove()
        chartRef.current = null
        candlestickSeriesRef.current = null
      }
    }
  }, [symbol])

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
