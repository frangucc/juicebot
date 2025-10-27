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

export default function StockChart({ symbol, dataMode = 'live', onReplayStatusChange }: StockChartProps) {
  const priceChartRef = useRef<HTMLDivElement>(null)
  const volumeChartRef = useRef<HTMLDivElement>(null)
  const priceChartInstanceRef = useRef<any>(null)
  const volumeChartInstanceRef = useRef<any>(null)
  const candlestickSeriesRef = useRef<any>(null)
  const volumeSeriesRef = useRef<any>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const activeFVGsRef = useRef<any[]>([]) // Track active FVGs
  const positionLineRef = useRef<any>(null) // Track position price line
  const bosLinesRef = useRef<any[]>([]) // Track BoS indicator lines
  const chochLinesRef = useRef<any[]>([]) // Track CHoCH indicator lines
  const swingHighsRef = useRef<any[]>([]) // Track swing highs for BoS/CHoCH
  const swingLowsRef = useRef<any[]>([]) // Track swing lows for BoS/CHoCH
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

  // Fetch position data and update P&L
  useEffect(() => {
    if (!symbol) return

    let intervalId: NodeJS.Timeout

    const fetchPosition = async () => {
      try {
        const response = await fetch(`${AI_SERVICE_URL}/position/${symbol}`)
        if (!response.ok) return

        const data = await response.json()
        setPosition(data.position)
      } catch (err) {
        console.error('[Position] Error fetching position:', err)
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
    if (!candlestickSeriesRef.current) {
      console.log('[Position Line] Chart not ready yet')
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
  }, [position, candlestickSeriesRef.current])

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

                    // Check if FVG overlaps with position entry price
                    const overlapsPosition = position &&
                      position.entry_price >= fvg.bottom &&
                      position.entry_price <= fvg.top

                    if (overlapsPosition) {
                      console.log('  ⚠️ FVG overlaps with position marker - skipping FVG to keep position visible')
                    } else {
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

                    // Check if FVG overlaps with position entry price
                    const overlapsPosition = position &&
                      position.entry_price >= fvg.bottom &&
                      position.entry_price <= fvg.top

                    if (overlapsPosition) {
                      console.log('  ⚠️ FVG overlaps with position marker - skipping FVG to keep position visible')
                    } else {
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

                  // Detect BoS and CHoCH - track swing points as they form
                  if (newData.length >= 20) {
                    const lookback = 5
                    const recentBars = newData.slice(-30)

                    // Check if we just formed a new swing high or low
                    if (recentBars.length > lookback * 2) {
                      const checkIndex = recentBars.length - lookback - 1 // Check the bar that's now "confirmed"
                      if (checkIndex >= lookback) {
                        const bar = recentBars[checkIndex]

                        // Check if this is a confirmed swing high
                        const isSwingHigh = recentBars.slice(checkIndex - lookback, checkIndex).every(b => b.high < bar.high) &&
                                            recentBars.slice(checkIndex + 1, checkIndex + lookback + 1).every(b => b.high < bar.high)

                        if (isSwingHigh) {
                          // Add to swing highs tracking (if not already there)
                          const alreadyTracked = swingHighsRef.current.find(s => Math.abs(s.price - bar.high) < 0.0001)
                          if (!alreadyTracked) {
                            swingHighsRef.current.push({ price: bar.high, time: bar.time, broken: false })
                            console.log(`📍 Swing High formed at $${bar.high.toFixed(4)}`)

                            // Keep only last 10 swing highs
                            if (swingHighsRef.current.length > 10) swingHighsRef.current.shift()
                          }
                        }

                        // Check if this is a confirmed swing low
                        const isSwingLow = recentBars.slice(checkIndex - lookback, checkIndex).every(b => b.low > bar.low) &&
                                           recentBars.slice(checkIndex + 1, checkIndex + lookback + 1).every(b => b.low > bar.low)

                        if (isSwingLow) {
                          const alreadyTracked = swingLowsRef.current.find(s => Math.abs(s.price - bar.low) < 0.0001)
                          if (!alreadyTracked) {
                            swingLowsRef.current.push({ price: bar.low, time: bar.time, broken: false })
                            console.log(`📍 Swing Low formed at $${bar.low.toFixed(4)}`)

                            if (swingLowsRef.current.length > 10) swingLowsRef.current.shift()
                          }
                        }
                      }
                    }

                    // Check if current bar breaks any unbroken swing points
                    // BoS = breaking in direction of trend (making new highs/lows)
                    // CHoCH = breaking against trend (reversal signal)

                    // Determine trend: more recent swing highs increasing = uptrend
                    const recentSwingHighs = swingHighsRef.current.slice(-3)
                    const recentSwingLows = swingLowsRef.current.slice(-3)
                    const isUptrend = recentSwingHighs.length >= 2 &&
                                      recentSwingHighs[recentSwingHighs.length - 1].price > recentSwingHighs[0].price
                    const isDowntrend = recentSwingLows.length >= 2 &&
                                        recentSwingLows[recentSwingLows.length - 1].price < recentSwingLows[0].price

                    // Track highest broken swing and lowest broken swing to only mark significant breaks
                    let highestBrokenSwing = bosLinesRef.current
                      .filter(b => b.type === 'bullish')
                      .reduce((max, b) => Math.max(max, b.price), 0)
                    let lowestBrokenSwing = bosLinesRef.current
                      .filter(b => b.type === 'bearish')
                      .reduce((min, b) => b.price > 0 ? Math.min(min, b.price) : min, Infinity)

                    // Check for breaks of swing highs (only mark if it's a NEW high)
                    swingHighsRef.current.forEach(swing => {
                      if (!swing.broken && chartBar.high > swing.price) {
                        // Only mark as BoS if this is higher than previous broken swings
                        const isNewHigh = swing.price > highestBrokenSwing * 1.001 // At least 0.1% higher

                        if (isNewHigh) {
                          swing.broken = true

                          // BoS if uptrend (making new highs), CHoCH if downtrend (reversal)
                          if (isUptrend || !isDowntrend) {
                            console.log(`⚪ Bullish BoS at $${swing.price.toFixed(4)} - New high`)
                            const bosLine = candlestickSeriesRef.current.createPriceLine({
                              price: swing.price,
                              color: '#FFFFFF',
                              lineWidth: 2,
                              lineStyle: 0,
                              axisLabelVisible: true,
                              title: '↑',
                            })
                            bosLinesRef.current.push({ line: bosLine, price: swing.price, type: 'bullish', time: chartBar.time })
                            highestBrokenSwing = swing.price
                          } else {
                            console.log(`🔵 CHoCH at $${swing.price.toFixed(4)} - Reversal`)
                            const chochLine = candlestickSeriesRef.current.createPriceLine({
                              price: swing.price,
                              color: '#00FFFF',
                              lineWidth: 2,
                              lineStyle: 0,
                              axisLabelVisible: true,
                              title: '⟳',
                            })
                            chochLinesRef.current.push({ line: chochLine, price: swing.price, type: 'bullish', time: chartBar.time })
                          }
                        } else {
                          // Mark as broken but don't draw a line (minor swing)
                          swing.broken = true
                        }
                      }
                    })

                    // Check for breaks of swing lows (only mark if it's a NEW low)
                    swingLowsRef.current.forEach(swing => {
                      if (!swing.broken && chartBar.low < swing.price) {
                        const isNewLow = swing.price < lowestBrokenSwing * 0.999 // At least 0.1% lower

                        if (isNewLow) {
                          swing.broken = true

                          // BoS if downtrend (making new lows), CHoCH if uptrend (reversal)
                          if (isDowntrend || !isUptrend) {
                            console.log(`⚪ Bearish BoS at $${swing.price.toFixed(4)} - New low`)
                            const bosLine = candlestickSeriesRef.current.createPriceLine({
                              price: swing.price,
                              color: '#FFFFFF',
                              lineWidth: 2,
                              lineStyle: 0,
                              axisLabelVisible: true,
                              title: '↓',
                            })
                            bosLinesRef.current.push({ line: bosLine, price: swing.price, type: 'bearish', time: chartBar.time })
                            lowestBrokenSwing = swing.price
                          } else {
                            console.log(`🔵 CHoCH at $${swing.price.toFixed(4)} - Reversal`)
                            const chochLine = candlestickSeriesRef.current.createPriceLine({
                              price: swing.price,
                              color: '#00FFFF',
                              lineWidth: 2,
                              lineStyle: 0,
                              axisLabelVisible: true,
                              title: '⟳',
                            })
                            chochLinesRef.current.push({ line: chochLine, price: swing.price, type: 'bearish', time: chartBar.time })
                          }
                        } else {
                          swing.broken = true
                        }
                      }
                    })

                    // Limit to 5 most recent BoS/CHoCH lines each
                    while (bosLinesRef.current.length > 5) {
                      const oldest = bosLinesRef.current.shift()
                      if (oldest && candlestickSeriesRef.current) {
                        candlestickSeriesRef.current.removePriceLine(oldest.line)
                      }
                    }
                    while (chochLinesRef.current.length > 5) {
                      const oldest = chochLinesRef.current.shift()
                      if (oldest && candlestickSeriesRef.current) {
                        candlestickSeriesRef.current.removePriceLine(oldest.line)
                      }
                    }
                  }
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
