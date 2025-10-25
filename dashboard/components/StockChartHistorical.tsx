'use client'

import { useEffect, useRef, useState } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const AI_SERVICE_URL = 'http://localhost:8002'
const HISTORICAL_WS_URL = 'ws://localhost:8001'

// Send bar data to AI service for fast-path responses
async function updateAIServiceMarketData(symbol: string, bar: BarData) {
  try {
    await fetch(`${AI_SERVICE_URL}/market_data`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol,
        timestamp: bar.timestamp,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
        volume: bar.volume
      })
    })
  } catch (error) {
    // Silently fail - don't disrupt chart rendering
    console.debug('Failed to update AI service:', error)
  }
}

interface StockChartProps {
  symbol: string
  dataMode?: 'live' | 'historical'
  onReplayStatusChange?: (status: {
    isPlaying: boolean
    currentIndex: number
    totalBars: number
    progress: number
  }) => void
}

interface BarData {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export default function StockChart({ symbol, dataMode = 'live', onReplayStatusChange }: StockChartProps) {
  const priceChartRef = useRef<HTMLDivElement>(null)
  const volumeChartRef = useRef<HTMLDivElement>(null)
  const priceChartInstanceRef = useRef<any>(null)
  const volumeChartInstanceRef = useRef<any>(null)
  const candlestickSeriesRef = useRef<any>(null)
  const volumeSeriesRef = useRef<any>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const activeFVGsRef = useRef<any[]>([]) // Track active FVGs
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [historicalData, setHistoricalData] = useState<any[]>([])
  const [replayStatus, setReplayStatus] = useState<{
    isPlaying: boolean
    currentIndex: number
    totalBars: number
    progress: number
  }>({ isPlaying: false, currentIndex: 0, totalBars: 0, progress: 0 })

  // Initialize charts once when component mounts
  useEffect(() => {
    if (!priceChartRef.current || !volumeChartRef.current) return

    let isMounted = true

    const initCharts = async () => {
      try {
        const { createChart, ColorType, BarSeries, HistogramSeries } = await import('lightweight-charts')

        if (!isMounted || !priceChartRef.current || !volumeChartRef.current) return

        console.log('Creating charts for', symbol)

        // Create price chart
        const priceChart = createChart(priceChartRef.current, {
          layout: {
            background: { type: ColorType.Solid, color: '#0b0e13' },
            textColor: '#55b685',
          },
          grid: {
            vertLines: { visible: false },
            horzLines: { visible: false },
          },
          rightPriceScale: {
            borderColor: '#55b68533',
            scaleMargins: {
              top: 0.1,
              bottom: 0.1,
            },
            minimumWidth: 60,
          },
          leftPriceScale: {
            borderColor: '#55b68533',
          },
          timeScale: {
            visible: false,  // Hide time scale on price chart
            borderColor: '#55b68533',
            timeVisible: true,
            secondsVisible: false,
            barSpacing: 6,
            minBarSpacing: 6,
            maxBarSpacing: 6,
            rightOffset: 80,
          },
          handleScroll: {
            mouseWheel: false,
            pressedMouseMove: true,
            horzTouchDrag: true,
            vertTouchDrag: false,
          },
          handleScale: {
            axisPressedMouseMove: false,
            mouseWheel: false,
            pinch: false,
          },
          width: priceChartRef.current.clientWidth,
          height: priceChartRef.current.clientHeight,
        })

        priceChartInstanceRef.current = priceChart

        // Add bar series
        const candlestickSeries = priceChart.addSeries(BarSeries, {
          thinBars: true,
          upColor: '#10B981',
          downColor: '#EF4444',
          openVisible: true,
        })

        candlestickSeriesRef.current = candlestickSeries

        // Create volume chart
        const volumeChart = createChart(volumeChartRef.current, {
          layout: {
            background: { type: ColorType.Solid, color: '#0b0e13' },
            textColor: '#55b685',
          },
          grid: {
            vertLines: { visible: false },
            horzLines: { visible: false },
          },
          rightPriceScale: {
            borderColor: '#55b68533',
            scaleMargins: {
              top: 0.1,
              bottom: 0.1,
            },
            minimumWidth: 60,
          },
          timeScale: {
            borderColor: '#55b68533',
            timeVisible: true,
            secondsVisible: false,
            barSpacing: 6,
            minBarSpacing: 6,
            maxBarSpacing: 6,
            rightOffset: 80,
          },
          handleScroll: {
            mouseWheel: false,
            pressedMouseMove: true,
            horzTouchDrag: true,
            vertTouchDrag: false,
          },
          handleScale: {
            axisPressedMouseMove: false,
            mouseWheel: false,
            pinch: false,
          },
          width: volumeChartRef.current.clientWidth,
          height: volumeChartRef.current.clientHeight,
        })

        volumeChartInstanceRef.current = volumeChart

        // Add volume histogram
        const volumeSeries = volumeChart.addSeries(HistogramSeries, {
          color: '#55b685',
          priceFormat: {
            type: 'volume',
          },
        })

        volumeSeriesRef.current = volumeSeries

        // Sync time scales for user panning only
        priceChart.timeScale().subscribeVisibleLogicalRangeChange((logicalRange: any) => {
          if (logicalRange && volumeChart && volumeChart.timeScale()) {
            volumeChart.timeScale().setVisibleLogicalRange(logicalRange)
          }
        })

        const handleResize = () => {
          if (priceChartRef.current && priceChart) {
            priceChart.applyOptions({
              width: priceChartRef.current.clientWidth,
              height: priceChartRef.current.clientHeight,
            })
          }
          if (volumeChartRef.current && volumeChart) {
            volumeChart.applyOptions({
              width: volumeChartRef.current.clientWidth,
              height: volumeChartRef.current.clientHeight,
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

    initCharts()

    return () => {
      isMounted = false
      if (priceChartInstanceRef.current) {
        priceChartInstanceRef.current.remove()
        priceChartInstanceRef.current = null
        candlestickSeriesRef.current = null
      }
      if (volumeChartInstanceRef.current) {
        volumeChartInstanceRef.current.remove()
        volumeChartInstanceRef.current = null
        volumeSeriesRef.current = null
      }
    }
  }, [symbol])

  // Handle data fetching/streaming based on mode
  useEffect(() => {
    console.log(`StockChart useEffect - dataMode: ${dataMode}, symbol: ${symbol}, chartReady: ${!!candlestickSeriesRef.current}`)
    if (!candlestickSeriesRef.current) {
      console.log('Chart not ready yet, waiting for initialization...')
      return
    }
    console.log('Chart is ready, proceeding with data connection...')

    let intervalId: NodeJS.Timeout

    if (dataMode === 'live') {
      // Live mode: Poll REST API
      const fetchLiveData = async () => {
        try {
          const response = await fetch(`${API_URL}/bars/${symbol}?limit=500`)
          if (!response.ok) throw new Error(`Failed to fetch: ${response.statusText}`)

          const bars: BarData[] = await response.json()
          console.log(`Fetched ${bars.length} live bars`)

          if (!bars || bars.length === 0) {
            setError(`No live data for ${symbol}`)
            return
          }

          // Update AI service with latest bar
          if (bars.length > 0) {
            updateAIServiceMarketData(symbol, bars[bars.length - 1])
          }

          const chartData = bars.map(bar => ({
            time: Math.floor(new Date(bar.timestamp).getTime() / 1000) as any,
            open: bar.open,
            high: bar.high,
            low: bar.low,
            close: bar.close,
          })).sort((a, b) => a.time - b.time)

          const volumeData = bars.map(bar => ({
            time: Math.floor(new Date(bar.timestamp).getTime() / 1000) as any,
            value: bar.volume,
            color: bar.close >= bar.open ? '#55b685' : '#ff0000',
          })).sort((a, b) => a.time - b.time)

          if (candlestickSeriesRef.current) {
            candlestickSeriesRef.current.setData(chartData)
            priceChartInstanceRef.current?.timeScale().fitContent()
            setError(null)
          }

          if (volumeSeriesRef.current) {
            volumeSeriesRef.current.setData(volumeData)
          }
        } catch (err: any) {
          console.error('Error fetching live data:', err)
          setError(`Failed to update chart: ${err.message}`)
        }
      }

      fetchLiveData()
      intervalId = setInterval(fetchLiveData, 5000)
    } else {
      // Historical mode: WebSocket replay
      console.log(`Connecting to historical WebSocket (${HISTORICAL_WS_URL})...`)

      const ws = new WebSocket(HISTORICAL_WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('✓ Connected to historical WebSocket')
        console.log(`Subscribing to ${symbol}...`)
        ws.send(JSON.stringify({ command: 'subscribe', symbol }))
        setTimeout(() => {
          console.log(`Setting playback speed to 60x (1 second per bar)...`)
          ws.send(JSON.stringify({ command: 'set_speed', symbol, speed: 60.0 }))
          console.log(`Starting playback for ${symbol}...`)
          ws.send(JSON.stringify({ command: 'play', symbol }))
        }, 100)
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)

          if (msg.type === 'bar') {
            // Update AI service with latest bar data
            updateAIServiceMarketData(symbol, msg.data)

            const chartBar = {
              time: Math.floor(new Date(msg.data.timestamp).getTime() / 1000) as any,
              open: msg.data.open,
              high: msg.data.high,
              low: msg.data.low,
              close: msg.data.close,
              volume: msg.data.volume,
            }

            setHistoricalData(prev => {
              // Check if this timestamp already exists to avoid duplicates
              const lastBar = prev[prev.length - 1]
              if (lastBar && lastBar.time === chartBar.time) {
                // Update the last bar instead of adding a duplicate
                const newData = [...prev.slice(0, -1), chartBar]
                if (candlestickSeriesRef.current) {
                  candlestickSeriesRef.current.setData(newData)
                }
                if (volumeSeriesRef.current) {
                  const volumeData = newData.map(bar => ({
                    time: bar.time,
                    value: bar.volume,
                    color: bar.close >= bar.open ? '#55b685' : '#ff0000',
                  }))
                  volumeSeriesRef.current.setData(volumeData)
                }
                return newData
              }

              // Skip bars with timestamps earlier than the last bar (out of order)
              if (lastBar && chartBar.time < lastBar.time) {
                console.warn(`Skipping out-of-order bar: ${chartBar.time} < ${lastBar.time}`)
                return prev
              }

              const newData = [...prev, chartBar]
              if (candlestickSeriesRef.current) {
                candlestickSeriesRef.current.setData(newData)

                // Detect and draw FVGs
                if (newData.length >= 3 && priceChartInstanceRef.current) {
                  const bar1 = newData[newData.length - 3]
                  const bar2 = newData[newData.length - 2]
                  const bar3 = newData[newData.length - 1]

                  // Bearish FVG: gap between bar1.low and bar3.high
                  if (bar1.low > bar3.high) {
                    const fvg = {
                      type: 'bearish',
                      top: bar1.low,
                      bottom: bar3.high,
                      time: bar3.time,
                      filled: false
                    }
                    console.log(`🔴 Bearish FVG detected at ${new Date(bar3.time * 1000).toISOString()}: ${fvg.bottom.toFixed(4)} - ${fvg.top.toFixed(4)}`)

                    // Draw horizontal lines for the FVG
                    try {
                      console.log('  Creating price lines...')
                      console.log('  Series ref exists?', !!candlestickSeriesRef.current)
                      console.log('  Series has createPriceLine?', typeof candlestickSeriesRef.current?.createPriceLine)

                      const topLine = candlestickSeriesRef.current.createPriceLine({
                        price: fvg.top,
                        color: '#EF4444',
                        lineWidth: 2,
                        lineStyle: 2, // Dashed
                        axisLabelVisible: true,
                        title: 'FVG Top',
                      })
                      console.log('  ✓ Top line created:', topLine)

                      const bottomLine = candlestickSeriesRef.current.createPriceLine({
                        price: fvg.bottom,
                        color: '#EF4444',
                        lineWidth: 2,
                        lineStyle: 2, // Dashed
                        axisLabelVisible: true,
                        title: 'FVG Bottom',
                      })
                      console.log('  ✓ Bottom line created:', bottomLine)

                      activeFVGsRef.current.push({
                        ...fvg,
                        topLine,
                        bottomLine
                      })
                      console.log(`  ✓ FVG stored, total active: ${activeFVGsRef.current.length}`)
                    } catch (err) {
                      console.error('  ✗ Error creating price lines:', err)
                    }
                  }

                  // Bullish FVG: gap between bar1.high and bar3.low
                  if (bar1.high < bar3.low) {
                    const fvg = {
                      type: 'bullish',
                      top: bar3.low,
                      bottom: bar1.high,
                      time: bar3.time,
                      filled: false
                    }
                    console.log(`🟢 Bullish FVG detected at ${new Date(bar3.time * 1000).toISOString()}: ${fvg.bottom.toFixed(4)} - ${fvg.top.toFixed(4)}`)

                    // Draw horizontal lines for the FVG
                    try {
                      console.log('  Creating price lines...')

                      const topLine = candlestickSeriesRef.current.createPriceLine({
                        price: fvg.top,
                        color: '#10B981',
                        lineWidth: 2,
                        lineStyle: 2, // Dashed
                        axisLabelVisible: true,
                        title: 'FVG Top',
                      })
                      console.log('  ✓ Top line created')

                      const bottomLine = candlestickSeriesRef.current.createPriceLine({
                        price: fvg.bottom,
                        color: '#10B981',
                        lineWidth: 2,
                        lineStyle: 2, // Dashed
                        axisLabelVisible: true,
                        title: 'FVG Bottom',
                      })
                      console.log('  ✓ Bottom line created')

                      activeFVGsRef.current.push({
                        ...fvg,
                        topLine,
                        bottomLine
                      })
                      console.log(`  ✓ FVG stored, total active: ${activeFVGsRef.current.length}`)
                    } catch (err) {
                      console.error('  ✗ Error creating price lines:', err)
                    }
                  }

                  // Check if any FVGs got filled by current bar
                  // Skip the bar that just created the FVG (don't check if current bar fills it)
                  activeFVGsRef.current.forEach((fvg, idx) => {
                    if (!fvg.filled && fvg.time !== chartBar.time) {
                      const filled = (fvg.type === 'bearish' && chartBar.high >= fvg.bottom) ||
                                    (fvg.type === 'bullish' && chartBar.low <= fvg.top)

                      if (filled) {
                        console.log(`✅ FVG filled at ${new Date(chartBar.time * 1000).toISOString()}: ${fvg.type}`)
                        fvg.filled = true

                        // Remove the price lines
                        if (fvg.topLine && candlestickSeriesRef.current) {
                          candlestickSeriesRef.current.removePriceLine(fvg.topLine)
                        }
                        if (fvg.bottomLine && candlestickSeriesRef.current) {
                          candlestickSeriesRef.current.removePriceLine(fvg.bottomLine)
                        }
                      }
                    }
                  })
                }

                // Let TradingView handle scrolling naturally
              }

              if (volumeSeriesRef.current) {
                const volumeData = newData.map(bar => ({
                  time: bar.time,
                  value: bar.volume,
                  color: bar.close >= bar.open ? '#55b685' : '#ff0000',
                }))
                volumeSeriesRef.current.setData(volumeData)
              }

              return newData
            })

            if (msg.meta) {
              const status = {
                isPlaying: true,
                currentIndex: msg.meta.bar_index,
                totalBars: msg.meta.total_bars,
                progress: msg.meta.progress
              }
              setReplayStatus(status)
              onReplayStatusChange?.(status)
            }
            setError(null)
          } else if (msg.type === 'subscribed') {
            console.log(`Subscribed: ${msg.total_bars} bars available`)
            setHistoricalData([])
            const status = {
              isPlaying: false,
              currentIndex: 0,
              totalBars: msg.total_bars,
              progress: 0
            }
            setReplayStatus(status)
            onReplayStatusChange?.(status)
          } else if (msg.type === 'replay_complete') {
            console.log('✓ Replay complete')
            setReplayStatus(prev => {
              const newStatus = { ...prev, isPlaying: false }
              onReplayStatusChange?.(newStatus)
              return newStatus
            })
          } else if (msg.type === 'error') {
            setError(msg.message)
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err)
        }
      }

      ws.onerror = (err) => {
        console.error('WebSocket error:', err)
        setError('Failed to connect to historical server on port 8001. Run: python historical_websocket_server.py')
      }

      ws.onclose = () => console.log('WebSocket disconnected')
    }

    return () => {
      if (intervalId) clearInterval(intervalId)
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [symbol, dataMode, isLoading])

  return (
    <div className="h-full w-full relative flex flex-col" style={{ backgroundColor: '#0b0e13' }}>
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center z-10" style={{ backgroundColor: '#0b0e13', color: '#55b685' }}>
          <div>Loading chart for {symbol}...</div>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center z-10" style={{ backgroundColor: '#0b0e13' }}>
          <div className="mb-2" style={{ color: '#ff0000' }}>{error}</div>
          {dataMode === 'historical' && (
            <div className="text-sm" style={{ color: '#55b685' }}>
              Start server: <code className="px-2 py-1 rounded" style={{ backgroundColor: '#0a0a0a', color: '#55b685' }}>python historical_websocket_server.py</code>
            </div>
          )}
        </div>
      )}
      {/* Price Chart - 70% */}
      <div ref={priceChartRef} style={{ width: '100%', height: '70%' }} />
      {/* Volume Chart - 30% */}
      <div ref={volumeChartRef} style={{ width: '100%', height: '30%', borderTop: '1px solid #55b68533' }} />
    </div>
  )
}
