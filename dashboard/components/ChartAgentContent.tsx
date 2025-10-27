'use client'

import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { ArrowLeft, FlaskConical } from 'lucide-react'
import StockChart from './StockChartHistorical'
import ChatInterface from './ChatInterface'
import GamepadController from './GamepadController'
import MurphyTestModal from './MurphyTestModal'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function ChartAgentContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const symbol = searchParams.get('symbol') || 'AAPL'
  const modeParam = searchParams.get('mode') as 'live' | 'historical' | null
  const [dataMode, setDataMode] = useState<'live' | 'historical'>(modeParam || 'live')
  const [replayStatus, setReplayStatus] = useState<{
    isPlaying: boolean
    currentIndex: number
    totalBars: number
    progress: number
  }>({ isPlaying: false, currentIndex: 0, totalBars: 0, progress: 0 })
  const [testModalOpen, setTestModalOpen] = useState(false)
  const [murphyLive, setMurphyLive] = useState<any>(null)
  const [murphyHistory, setMurphyHistory] = useState<Array<{
    signal: string
    price: number
    timestamp: number
    correct: boolean | null
  }>>([])
  const [murphyAccuracy, setMurphyAccuracy] = useState<{
    lastSignalCorrect: boolean | null
    totalSignals: number
    correctSignals: number
    accuracy: number
  }>({ lastSignalCorrect: null, totalSignals: 0, correctSignals: 0, accuracy: 0 })

  // Momo Live state
  const [momoLive, setMomoLive] = useState<any>(null)
  const [momoHistory, setMomoHistory] = useState<Array<{
    signal: string
    action: string
    price: number
    timestamp: number
    correct: boolean | null
  }>>([])
  const [momoAccuracy, setMomoAccuracy] = useState<{
    lastSignalCorrect: boolean | null
    totalSignals: number
    correctSignals: number
    accuracy: number
  }>({ lastSignalCorrect: null, totalSignals: 0, correctSignals: 0, accuracy: 0 })

  // Murphy Live WebSocket listener
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8002/events/${symbol}`)

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      // Event bus wraps messages as {"type": "event", "event": {actual_event}}
      if (data.type === 'event' && data.event?.type === 'murphy_live') {
        console.log('[Murphy Live] Received:', data.event)
        const murphyData = data.event
        setMurphyLive(murphyData)

        // Extract signal direction from line1
        let signal = 'NEUTRAL'
        const line1 = murphyData.line1 || ''
        if (line1.includes('BULLISH')) signal = 'BULLISH'
        else if (line1.includes('BEARISH')) signal = 'BEARISH'

        // Extract price from line2 (format: "Grade: [7] | Confidence: 0.36 | Price: $0.67")
        const line2 = murphyData.line2 || ''
        const priceMatch = line2.match(/Price:\s*\$?([\d.]+)/)
        const price = priceMatch ? parseFloat(priceMatch[1]) : 0

        console.log('[Murphy Tracking] Signal:', signal, 'Price:', price, 'Line2:', line2)

        // Store new signal only if we have valid data and it's different from last signal
        if (price > 0 && signal !== 'NEUTRAL') {
          setMurphyHistory(prev => {
            // Check if this is a new signal (different direction or price changed significantly)
            const lastSignal = prev[prev.length - 1]
            const isDifferent = !lastSignal ||
                                lastSignal.signal !== signal ||
                                Math.abs(lastSignal.price - price) / lastSignal.price > 0.01

            if (isDifferent) {
              const newSignal = {
                signal,
                price,
                timestamp: Date.now(),
                correct: null
              }
              console.log('[Murphy Tracking] Storing new signal:', newSignal)
              return [...prev, newSignal]
            }
            return prev
          })
        }
      }
    }

    ws.onerror = (error) => {
      console.error('[Murphy Live] WebSocket error:', error)
    }

    return () => {
      ws.close()
    }
  }, [symbol])

  // Momo Live WebSocket listener
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8002/events/${symbol}`)

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      // Event bus wraps messages as {"type": "event", "event": {actual_event}}
      if (data.type === 'event' && data.event?.type === 'momo_live') {
        console.log('[Momo Live] Received:', data.event)
        const momoData = data.event
        setMomoLive(momoData)

        // Extract signal direction and action from line1
        let signal = 'NEUTRAL'
        let action = 'WAIT'
        const line1 = momoData.line1 || ''
        if (line1.includes('BULLISH')) signal = 'BULLISH'
        else if (line1.includes('BEARISH')) signal = 'BEARISH'

        if (line1.includes('STRONG_BUY')) action = 'STRONG_BUY'
        else if (line1.includes('BUY')) action = 'BUY'
        else if (line1.includes('STRONG_SELL')) action = 'STRONG_SELL'
        else if (line1.includes('SELL')) action = 'SELL'
        else action = 'WAIT'

        // Extract price from line2
        const line2 = momoData.line2 || ''
        const priceMatch = line2.match(/Price:\s*\$?([\d.]+)/)
        const price = priceMatch ? parseFloat(priceMatch[1]) : 0

        // Store signal in history (only if different from last)
        if (signal !== 'NEUTRAL') {
          setMomoHistory(prev => {
            const lastSignal = prev[prev.length - 1]
            const isDifferent = !lastSignal ||
              lastSignal.signal !== signal ||
              Math.abs(lastSignal.price - price) > 0.01

            if (isDifferent) {
              const newSignal = {
                signal,
                action,
                price,
                timestamp: Date.now(),
                correct: null
              }
              console.log('[Momo Tracking] Storing new signal:', newSignal)
              return [...prev, newSignal]
            }
            return prev
          })
        }
      }
    }

    ws.onerror = (error) => {
      console.error('[Momo Live] WebSocket error:', error)
    }

    return () => {
      ws.close()
    }
  }, [symbol])

  // Evaluate Murphy signal accuracy every 10 seconds
  useEffect(() => {
    const evaluateAccuracy = async () => {
      if (murphyHistory.length === 0) {
        console.log('[Murphy Eval] No signals in history')
        return
      }

      try {
        // Get current price
        const response = await fetch(`http://localhost:8000/symbols/${symbol}/realtime-price`)
        if (!response.ok) {
          console.log('[Murphy Eval] Failed to fetch current price')
          return
        }

        const data = await response.json()
        const currentPrice = data.price

        // Evaluate signals that are at least 2 minutes old and not yet evaluated
        const now = Date.now()
        const twoMinutes = 2 * 60 * 1000
        let updated = false

        console.log('[Murphy Eval] Current price:', currentPrice, 'History length:', murphyHistory.length)

        const updatedHistory = murphyHistory.map(signal => {
          const age = now - signal.timestamp
          const ageMinutes = age / 60000

          // Skip if already evaluated
          if (signal.correct !== null) {
            return signal
          }

          // Skip if too recent (need at least 2 minutes to evaluate)
          if (age < twoMinutes) {
            console.log(`[Murphy Eval] Signal too recent (${ageMinutes.toFixed(1)} min old)`)
            return signal
          }

          // Calculate price change
          const priceChange = ((currentPrice - signal.price) / signal.price) * 100

          // Evaluate correctness (need at least 0.3% move to count)
          let correct = false
          if (Math.abs(priceChange) >= 0.3) {
            if (signal.signal === 'BULLISH' && priceChange > 0) correct = true
            if (signal.signal === 'BEARISH' && priceChange < 0) correct = true
          }

          console.log(`[Murphy Eval] Evaluating ${signal.signal} at $${signal.price} -> $${currentPrice} (${priceChange.toFixed(2)}%): ${correct ? '✓ CORRECT' : '✗ WRONG'}`)

          updated = true
          return { ...signal, correct }
        })

        if (updated) {
          setMurphyHistory(updatedHistory)

          // Calculate overall accuracy
          const evaluated = updatedHistory.filter(s => s.correct !== null)
          const correctCount = evaluated.filter(s => s.correct).length
          const lastEvaluated = evaluated[evaluated.length - 1]

          const newAccuracy = {
            lastSignalCorrect: lastEvaluated?.correct ?? null,
            totalSignals: evaluated.length,
            correctSignals: correctCount,
            accuracy: evaluated.length > 0 ? (correctCount / evaluated.length) * 100 : 0
          }

          console.log('[Murphy Eval] Updated accuracy:', newAccuracy)
          setMurphyAccuracy(newAccuracy)
        }
      } catch (err) {
        console.error('[Murphy Eval] Error:', err)
      }
    }

    evaluateAccuracy() // Initial evaluation
    const interval = setInterval(evaluateAccuracy, 10000) // Every 10s for faster updates

    return () => clearInterval(interval)
  }, [murphyHistory, symbol])

  // Evaluate Momo signal accuracy every 10 seconds
  useEffect(() => {
    const evaluateAccuracy = async () => {
      if (momoHistory.length === 0) {
        console.log('[Momo Eval] No signals in history')
        return
      }

      try {
        // Get current price
        const response = await fetch(`http://localhost:8000/symbols/${symbol}/realtime-price`)
        if (!response.ok) {
          console.log('[Momo Eval] Failed to fetch current price')
          return
        }
        const priceData = await response.json()
        const currentPrice = priceData.price

        console.log('[Momo Eval] Current price:', currentPrice, '| History count:', momoHistory.length)

        // Update signal correctness
        const updatedHistory = momoHistory.map((sig) => {
          // Skip if already evaluated
          if (sig.correct !== null) return sig

          const timeDiff = Date.now() - sig.timestamp
          const priceDiff = currentPrice - sig.price
          const priceDiffPct = (priceDiff / sig.price) * 100

          // Evaluate after 30 seconds (can adjust)
          if (timeDiff > 30000) {
            const isCorrect =
              (sig.signal === 'BULLISH' && priceDiffPct > 1.0) || // 1% move
              (sig.signal === 'BEARISH' && priceDiffPct < -1.0)

            console.log(`[Momo Eval] Signal @ $${sig.price.toFixed(2)} (${sig.signal}/${sig.action}) | Now $${currentPrice.toFixed(2)} (${priceDiffPct.toFixed(2)}%) → ${isCorrect ? 'CORRECT ✓' : 'WRONG ✗'}`)

            return { ...sig, correct: isCorrect }
          }

          return sig
        })

        setMomoHistory(updatedHistory)

        // Calculate overall accuracy
        const evaluatedSignals = updatedHistory.filter(s => s.correct !== null)
        if (evaluatedSignals.length > 0) {
          const correctCount = evaluatedSignals.filter(s => s.correct === true).length
          const accuracy = (correctCount / evaluatedSignals.length) * 100

          const newAccuracy = {
            lastSignalCorrect: evaluatedSignals[evaluatedSignals.length - 1]?.correct ?? null,
            totalSignals: evaluatedSignals.length,
            correctSignals: correctCount,
            accuracy: accuracy
          }

          console.log('[Momo Eval] Updated accuracy:', newAccuracy)
          setMomoAccuracy(newAccuracy)
        }
      } catch (err) {
        console.error('[Momo Eval] Error:', err)
      }
    }

    evaluateAccuracy() // Initial evaluation
    const interval = setInterval(evaluateAccuracy, 10000) // Every 10s for faster updates

    return () => clearInterval(interval)
  }, [momoHistory, symbol])

  // Update URL when mode changes
  const handleModeChange = (newMode: 'live' | 'historical') => {
    setDataMode(newMode)
    const params = new URLSearchParams(searchParams.toString())
    params.set('mode', newMode)
    router.push(`/chart-agent?${params.toString()}`)
  }

  return (
    <div className="h-full w-full flex flex-col geek-mode">
      {/* Minimal Header - Max 50px */}
      <header className="h-[50px] flex-shrink-0 geek-bg-card border-b border-[#55b68533] flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/')}
            className="transition-colors"
            style={{ color: '#55b685' }}
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-bold font-mono" style={{ color: '#55b685' }}>${symbol}</h1>
        </div>
        <div className="flex items-center gap-3">
          {dataMode === 'historical' && replayStatus.totalBars > 0 && (
            <>
              <div className="text-xs font-mono" style={{ color: '#55b685' }}>
                Bar {replayStatus.currentIndex} / {replayStatus.totalBars} ({replayStatus.progress.toFixed(1)}%)
              </div>
              <button
                onClick={() => window.location.reload()}
                className="text-xs font-mono hover:opacity-70 transition-opacity"
                style={{ color: '#55b685', background: 'none', border: 'none', padding: 0 }}
              >
                Restart
              </button>
            </>
          )}
          <select
            value={dataMode}
            onChange={(e) => handleModeChange(e.target.value as 'live' | 'historical')}
            className="bg-transparent text-sm px-3 py-1.5 rounded focus:outline-none transition-colors font-mono"
            style={{ color: '#55b685', border: 'none' }}
          >
            <option value="live">[ LIVE_DATA ]</option>
            <option value="historical">[ HISTORICAL_DATA ]</option>
          </select>
        </div>
      </header>

      {/* Main Content - Split 25/75 */}
      <div className="flex-1 flex overflow-hidden" style={{ minHeight: 0 }}>
        {/* Left Side - Chat Interface (25%) */}
        <div className="w-1/4 h-full border-r border-[#55b68533] geek-bg-secondary">
          <ChatInterface symbol={symbol} />
        </div>

        {/* Right Side - Chart Area (75%) */}
        <div className="w-3/4 h-full flex flex-col" style={{ minHeight: 0 }}>
          {/* Murphy Live Ticker Bar - Same height as header (50px) */}
          {murphyLive && (
            <div className="h-[50px] flex-shrink-0 border-b border-[#55b68533] geek-bg-card font-mono flex">
              {/* Left Column - Direction Signal */}
              <div
                className={`flex items-center justify-center px-6 text-base font-bold ${
                  murphyLive.line1?.includes('BULLISH')
                    ? 'bg-green-600/80 text-white'
                    : murphyLive.line1?.includes('BEARISH')
                    ? 'bg-red-600/80 text-white'
                    : 'bg-transparent text-gray-400'
                }`}
                style={{ minWidth: '140px' }}
              >
                {murphyLive.line1?.includes('BULLISH')
                  ? '↑ BULLISH'
                  : murphyLive.line1?.includes('BEARISH')
                  ? '↓ BEARISH'
                  : '− NEUTRAL'}
              </div>

              {/* Middle Column - Details (2 rows) */}
              <div className="flex-1 px-4 py-1.5 text-xs flex flex-col justify-center gap-1 min-w-0">
                <div className="text-gray-200 truncate">{murphyLive.line2}</div>
                <div className="text-gray-400 truncate">{murphyLive.line3}</div>
              </div>

              {/* Right Column - Accuracy Stats */}
              <div className="border-l border-[#55b68533] px-4 py-1.5 flex items-center gap-3 flex-shrink-0" style={{ width: '300px' }}>
                <div className="flex-1 flex flex-col justify-center gap-1">
                  <div className="text-xs flex items-center justify-between">
                    <span className="text-gray-400">Last Signal:</span>
                    <span className={`font-bold ${
                      murphyAccuracy.lastSignalCorrect === true ? 'text-green-400' :
                      murphyAccuracy.lastSignalCorrect === false ? 'text-red-400' :
                      'text-gray-500'
                    }`}>
                      {murphyAccuracy.lastSignalCorrect === true ? '✓ CORRECT' :
                       murphyAccuracy.lastSignalCorrect === false ? '✗ WRONG' :
                       'PENDING'}
                    </span>
                  </div>
                  <div className="text-xs flex items-center justify-between">
                    <span className="text-gray-400">Accuracy:</span>
                    <span className={`font-bold ${
                      murphyAccuracy.accuracy >= 60 ? 'text-green-400' :
                      murphyAccuracy.accuracy >= 40 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {murphyAccuracy.totalSignals > 0
                        ? `${murphyAccuracy.accuracy.toFixed(1)}% (${murphyAccuracy.correctSignals}/${murphyAccuracy.totalSignals})`
                        : 'NO DATA'}
                    </span>
                  </div>
                </div>

                {/* Test Lab Icon */}
                <button
                  onClick={() => setTestModalOpen(true)}
                  className="p-2 hover:bg-white/10 rounded transition-colors flex-shrink-0"
                  title="Open Murphy Test Lab"
                >
                  <FlaskConical className="w-5 h-5" style={{ color: '#55b685' }} />
                </button>
              </div>
            </div>
          )}

          {/* Momo Live Ticker Bar - Same height as header (50px) */}
          {momoLive && (
            <div className="h-[50px] flex-shrink-0 border-b border-[#55b68533] geek-bg-card font-mono flex">
              {/* Left Column - Direction Signal + Action */}
              <div
                className={`flex flex-col items-center justify-center px-4 text-sm font-bold ${
                  momoLive.line1?.includes('BULLISH') || momoLive.line1?.includes('BUY')
                    ? 'bg-green-600/80 text-white'
                    : momoLive.line1?.includes('BEARISH') || momoLive.line1?.includes('SELL')
                    ? 'bg-red-600/80 text-white'
                    : 'bg-transparent text-gray-400'
                }`}
                style={{ minWidth: '140px' }}
              >
                <div>
                  {momoLive.line1?.includes('BULLISH')
                    ? '↑ BULLISH'
                    : momoLive.line1?.includes('BEARISH')
                    ? '↓ BEARISH'
                    : '− NEUTRAL'}
                </div>
                <div className="text-[10px] opacity-80 mt-0.5">
                  {momoLive.line1?.includes('STRONG_BUY') ? 'STRONG BUY' :
                   momoLive.line1?.includes('STRONG_SELL') ? 'STRONG SELL' :
                   momoLive.line1?.includes('BUY') ? 'BUY' :
                   momoLive.line1?.includes('SELL') ? 'SELL' :
                   'WAIT'}
                </div>
              </div>

              {/* Middle Column - Details (2 rows) */}
              <div className="flex-1 px-4 py-1.5 text-xs flex flex-col justify-center gap-1 min-w-0">
                <div className="text-gray-200 truncate">{momoLive.line2}</div>
                <div className="text-gray-400 truncate">{momoLive.line3}</div>
              </div>

              {/* Right Column - Accuracy Stats */}
              <div className="border-l border-[#55b68533] px-4 py-1.5 flex items-center gap-3 flex-shrink-0" style={{ width: '300px' }}>
                <div className="flex-1 flex flex-col justify-center gap-1">
                  <div className="text-xs flex items-center justify-between">
                    <span className="text-gray-400">Last Signal:</span>
                    <span className={`font-bold ${
                      momoAccuracy.lastSignalCorrect === true ? 'text-green-400' :
                      momoAccuracy.lastSignalCorrect === false ? 'text-red-400' :
                      'text-gray-500'
                    }`}>
                      {momoAccuracy.lastSignalCorrect === true ? '✓ CORRECT' :
                       momoAccuracy.lastSignalCorrect === false ? '✗ WRONG' :
                       'PENDING'}
                    </span>
                  </div>
                  <div className="text-xs flex items-center justify-between">
                    <span className="text-gray-400">Accuracy:</span>
                    <span className={`font-bold ${
                      momoAccuracy.accuracy >= 60 ? 'text-green-400' :
                      momoAccuracy.accuracy >= 40 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {momoAccuracy.totalSignals > 0
                        ? `${momoAccuracy.accuracy.toFixed(1)}% (${momoAccuracy.correctSignals}/${momoAccuracy.totalSignals})`
                        : 'NO DATA'}
                    </span>
                  </div>
                </div>

                {/* Momo Badge */}
                <div className="p-2 bg-purple-600/20 rounded flex-shrink-0" title="Momo Momentum">
                  <span className="text-purple-400 text-xs font-bold">MOMO</span>
                </div>
              </div>
            </div>
          )}

          {/* Chart - Takes remaining space */}
          <div className="flex-1" style={{ minHeight: 0 }}>
            <StockChart
              symbol={symbol}
              dataMode={dataMode}
              onReplayStatusChange={setReplayStatus}
            />
          </div>
        </div>
      </div>

      {/* Gamepad Controller Widget */}
      <GamepadController
        symbol={symbol}
        onCommandExecute={(command, result) => {
          console.log('Gamepad command executed:', command, result)
        }}
      />

      {/* Murphy Test Lab Modal */}
      <MurphyTestModal
        symbol={symbol}
        isOpen={testModalOpen}
        onClose={() => setTestModalOpen(false)}
      />
    </div>
  )
}
