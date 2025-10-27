'use client'

import { useState, useEffect } from 'react'
import { X, PlayCircle, StopCircle, RefreshCw } from 'lucide-react'

// Murphy test endpoints are on AI service (port 8002)
const API_URL = 'http://localhost:8002'

interface TestSession {
  id: string
  symbol: string
  started_at: string
  ended_at: string | null
  status: string
  config: {
    min_stars: number
    min_grade: number
    min_confidence: number
    sticky_direction: boolean
    require_flip_conviction: boolean
  }
  metrics: {
    total_signals_generated: number
    signals_displayed: number
    signals_filtered: number
    correct_displayed: number
    correct_filtered: number
    accuracy_displayed: number
    accuracy_filtered: number
    avg_grade_displayed: number
    avg_grade_filtered: number
  }
  notes?: string
}

interface SignalRecord {
  id: string
  timestamp: string
  entry_price: number
  bar_count_at_signal: number
  bars_elapsed: number
  direction: string
  stars: number
  grade: number
  confidence: number
  passed_filter: boolean
  filter_reason: string | null

  // Heat/Gain tracking
  peak_price: number
  peak_gain_pct: number
  worst_price: number
  max_heat_pct: number
  exit_price: number | null
  final_pnl_pct: number | null
  duration_seconds: number | null

  // Multi-timeframe evaluation
  result_5_bars: string | null
  pnl_at_5_bars: number | null
  result_10_bars: string | null
  pnl_at_10_bars: number | null
  result_20_bars: string | null
  pnl_at_20_bars: number | null
  result_50_bars: string | null
  pnl_at_50_bars: number | null

  final_result: string
  interpretation: string
}

interface MurphyTestModalProps {
  symbol: string
  isOpen: boolean
  onClose: () => void
}

export default function MurphyTestModal({ symbol, isOpen, onClose }: MurphyTestModalProps) {
  const [activeSession, setActiveSession] = useState<TestSession | null>(null)
  const [signals, setSignals] = useState<SignalRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [view, setView] = useState<'all' | 'displayed' | 'filtered'>('all')
  const [autoRefresh, setAutoRefresh] = useState(true)

  // Fetch active session
  const fetchSession = async () => {
    try {
      const response = await fetch(`${API_URL}/murphy-test/sessions/${symbol}/active`)
      const data = await response.json()
      if (data.success && data.session) {
        setActiveSession(data.session)
      } else {
        setActiveSession(null)
      }
    } catch (error) {
      console.error('Failed to fetch session:', error)
    }
  }

  // Fetch signals for active session
  const fetchSignals = async () => {
    if (!activeSession) return

    try {
      const passedFilter = view === 'displayed' ? true : view === 'filtered' ? false : undefined
      const url = passedFilter !== undefined
        ? `${API_URL}/murphy-test/sessions/${activeSession.id}/signals?passed_filter=${passedFilter}&limit=50`
        : `${API_URL}/murphy-test/sessions/${activeSession.id}/signals?limit=50`

      const response = await fetch(url)
      const data = await response.json()
      if (data.success) {
        setSignals(data.signals)
      }
    } catch (error) {
      console.error('Failed to fetch signals:', error)
    }
  }

  // Start new test session
  const startSession = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/murphy-test/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          notes: `Test session started at ${new Date().toLocaleString()}`
        })
      })
      const data = await response.json()
      if (data.success) {
        setActiveSession(data.session)
        console.log('✓ Test session started:', data.session.id)
      }
    } catch (error) {
      console.error('Failed to start session:', error)
    } finally {
      setLoading(false)
    }
  }

  // End active session
  const endSession = async () => {
    if (!activeSession) return

    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/murphy-test/sessions/${activeSession.id}/end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'completed' })
      })
      const data = await response.json()
      if (data.success) {
        console.log('✓ Test session ended')
        setActiveSession(null)
        setSignals([])
      }
    } catch (error) {
      console.error('Failed to end session:', error)
    } finally {
      setLoading(false)
    }
  }

  // Auto-refresh data
  useEffect(() => {
    if (!isOpen) return

    fetchSession()
    const interval = setInterval(() => {
      if (autoRefresh) {
        fetchSession()
      }
    }, 5000) // Refresh every 5 seconds

    return () => clearInterval(interval)
  }, [isOpen, symbol, autoRefresh])

  useEffect(() => {
    if (activeSession) {
      fetchSignals()
      const interval = setInterval(() => {
        if (autoRefresh) {
          fetchSignals()
        }
      }, 5000)

      return () => clearInterval(interval)
    }
  }, [activeSession, view, autoRefresh])

  if (!isOpen) return null

  // Helper to render multi-timeframe evaluation cell
  const getBarEvalDisplay = (result: string | null, pnl: number | null) => {
    if (!result || pnl === null) {
      return <span className="text-gray-600 text-xs">-</span>
    }

    if (result === 'neutral') {
      return <span className="text-gray-400 text-xs">~{pnl.toFixed(1)}%</span>
    }

    const isCorrect = result === 'correct'
    const color = isCorrect ? 'text-green-400' : 'text-red-400'
    const icon = isCorrect ? '✓' : '✗'

    return (
      <span className={`${color} text-xs font-medium`}>
        {icon}{pnl > 0 ? '+' : ''}{pnl.toFixed(1)}%
      </span>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="geek-bg-card border border-[#55b68533] rounded-lg w-[95vw] h-[90vh] flex flex-col font-mono">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#55b68533]">
          <h2 className="text-xl font-bold" style={{ color: '#55b685' }}>
            MURPHY TEST LAB - {symbol}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Session Controls */}
        <div className="p-4 border-b border-[#55b68533] flex items-center justify-between">
          <div className="flex items-center gap-4">
            {activeSession ? (
              <>
                <button
                  onClick={endSession}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600/20 border border-red-600/50 rounded hover:bg-red-600/30 transition-colors disabled:opacity-50"
                  style={{ color: '#ff6b6b' }}
                >
                  <StopCircle className="w-4 h-4" />
                  END SESSION
                </button>
                <div className="text-sm text-gray-400">
                  Running since {new Date(activeSession.started_at).toLocaleTimeString()}
                </div>
              </>
            ) : (
              <div className="text-sm text-gray-400">
                No test session active. Start Murphy Live to auto-create a session.
              </div>
            )}
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-gray-400">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded"
              />
              Auto-refresh
            </label>
            <button
              onClick={() => {
                fetchSession()
                fetchSignals()
              }}
              className="p-2 hover:bg-white/10 rounded transition-colors"
            >
              <RefreshCw className="w-4 h-4" style={{ color: '#55b685' }} />
            </button>
          </div>
        </div>

        {/* Metrics Dashboard */}
        {activeSession && (
          <div className="p-4 border-b border-[#55b68533]">
            <div className="grid grid-cols-5 gap-3 text-sm mb-3">
              <div className="p-3 geek-bg-secondary rounded">
                <div className="text-gray-400 text-xs mb-1">Total Signals</div>
                <div className="text-2xl font-bold" style={{ color: '#55b685' }}>
                  {activeSession.metrics.total_signals_generated}
                </div>
                <div className="text-xs text-gray-500">
                  {activeSession.metrics.signals_displayed} shown, {activeSession.metrics.signals_filtered} hidden
                </div>
              </div>

              <div className="p-3 geek-bg-secondary rounded">
                <div className="text-gray-400 text-xs mb-1">Overall Accuracy</div>
                <div className={`text-2xl font-bold ${
                  activeSession.metrics.accuracy_displayed >= 60 ? 'text-green-400' :
                  activeSession.metrics.accuracy_displayed >= 40 ? 'text-yellow-400' :
                  'text-red-400'
                }`}>
                  {activeSession.metrics.accuracy_displayed > 0
                    ? activeSession.metrics.accuracy_displayed.toFixed(1)
                    : '0.0'}%
                </div>
                <div className="text-xs text-gray-500">
                  {activeSession.metrics.correct_displayed} / {activeSession.metrics.signals_displayed} correct
                </div>
              </div>

              <div className="p-3 geek-bg-secondary rounded">
                <div className="text-gray-400 text-xs mb-1">Hidden Accuracy</div>
                <div className={`text-2xl font-bold ${
                  activeSession.metrics.accuracy_filtered >= 60 ? 'text-green-400' :
                  activeSession.metrics.accuracy_filtered >= 40 ? 'text-yellow-400' :
                  'text-red-400'
                }`}>
                  {activeSession.metrics.accuracy_filtered > 0
                    ? activeSession.metrics.accuracy_filtered.toFixed(1)
                    : '0.0'}%
                </div>
                <div className="text-xs text-gray-500">
                  {activeSession.metrics.correct_filtered} / {activeSession.metrics.signals_filtered} correct
                </div>
              </div>

              <div className="p-3 geek-bg-secondary rounded">
                <div className="text-gray-400 text-xs mb-1">Avg Grade</div>
                <div className="text-2xl font-bold text-blue-400">
                  [{activeSession.metrics.avg_grade_displayed > 0
                    ? activeSession.metrics.avg_grade_displayed.toFixed(1)
                    : '0.0'}]
                </div>
                <div className="text-xs text-gray-500">
                  shown signals
                </div>
              </div>

              <div className="p-3 geek-bg-secondary rounded">
                <div className="text-gray-400 text-xs mb-1">Filter Quality</div>
                <div className={`text-2xl font-bold ${
                  activeSession.metrics.accuracy_displayed > activeSession.metrics.accuracy_filtered
                    ? 'text-green-400'
                    : 'text-yellow-400'
                }`}>
                  {activeSession.metrics.accuracy_displayed > activeSession.metrics.accuracy_filtered ? '✓' : '⚠️'}
                </div>
                <div className="text-xs text-gray-500">
                  {activeSession.metrics.accuracy_displayed > activeSession.metrics.accuracy_filtered
                    ? 'Blocking bad signals'
                    : 'May block winners'}
                </div>
              </div>
            </div>

            <div className="text-xs text-gray-400 p-2 geek-bg-secondary rounded">
              💡 <span className="font-semibold">Goal:</span> Hidden accuracy should be LOWER than overall accuracy (we want to filter out bad signals, not hide winners)
            </div>
          </div>
        )}

        {/* View Tabs */}
        {activeSession && (
          <div className="flex border-b border-[#55b68533]">
            <button
              onClick={() => setView('all')}
              className={`px-6 py-3 text-sm transition-colors ${
                view === 'all'
                  ? 'border-b-2 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
              style={view === 'all' ? { borderColor: '#55b685', color: '#55b685' } : {}}
            >
              All Signals ({activeSession.metrics.total_signals_generated})
            </button>
            <button
              onClick={() => setView('displayed')}
              className={`px-6 py-3 text-sm transition-colors ${
                view === 'displayed'
                  ? 'border-b-2 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
              style={view === 'displayed' ? { borderColor: '#55b685', color: '#55b685' } : {}}
            >
              Displayed ({activeSession.metrics.signals_displayed})
            </button>
            <button
              onClick={() => setView('filtered')}
              className={`px-6 py-3 text-sm transition-colors ${
                view === 'filtered'
                  ? 'border-b-2 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
              style={view === 'filtered' ? { borderColor: '#55b685', color: '#55b685' } : {}}
            >
              Filtered Out ({activeSession.metrics.signals_filtered})
            </button>
          </div>
        )}

        {/* Signals Table */}
        <div className="flex-1 overflow-auto p-4">
          {!activeSession ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <p className="text-lg mb-2">No active test session</p>
                <p className="text-sm mb-4">Type "murphy live" in the chat to start recording signals</p>
                <p className="text-xs text-gray-500">Test sessions auto-create when Murphy Live starts</p>
              </div>
            </div>
          ) : signals.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <p className="text-lg mb-2">Warming up...</p>
                <p className="text-sm mb-4">Murphy needs ~20 bars to start generating signals</p>
                <p className="text-xs text-gray-500">Signals will appear here automatically once available</p>
              </div>
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0 geek-bg-card">
                <tr className="text-left text-gray-400 border-b border-[#55b68533]">
                  <th className="p-2 text-xs">Time</th>
                  <th className="p-2 text-xs">Signal</th>
                  <th className="p-2 text-xs">Entry @ Bars</th>
                  <th className="p-2 text-center text-xs">5B</th>
                  <th className="p-2 text-center text-xs">10B</th>
                  <th className="p-2 text-center text-xs">20B</th>
                  <th className="p-2 text-center text-xs">50B</th>
                  <th className="p-2 text-center text-xs">Best</th>
                  <th className="p-2 text-center text-xs">Status</th>
                </tr>
              </thead>
              <tbody>
                {signals.map((signal) => {
                  const isPremature = signal.bar_count_at_signal < 20

                  // Find best result across all timeframes
                  const results = [
                    { frame: '5B', result: signal.result_5_bars, pnl: signal.pnl_at_5_bars },
                    { frame: '10B', result: signal.result_10_bars, pnl: signal.pnl_at_10_bars },
                    { frame: '20B', result: signal.result_20_bars, pnl: signal.pnl_at_20_bars },
                    { frame: '50B', result: signal.result_50_bars, pnl: signal.pnl_at_50_bars },
                  ].filter(r => r.result)

                  const bestResult = results.length > 0
                    ? results.reduce((best, curr) => {
                        if (curr.result === 'correct') return curr
                        if (best.result === 'wrong' && curr.result === 'neutral') return curr
                        return best
                      }, results[0])
                    : null

                  return (
                    <tr key={signal.id} className="border-b border-[#55b68533]/30 hover:bg-white/5 transition-colors">
                      {/* Time */}
                      <td className="p-2 text-gray-400 text-xs">
                        {new Date(signal.timestamp).toLocaleTimeString()}
                      </td>

                      {/* Signal: Direction + Stars + Grade + Confidence */}
                      <td className="p-2">
                        <div className="flex items-center gap-2">
                          <span className={`font-bold text-sm ${
                            signal.direction === 'BULLISH' ? 'text-green-400' :
                            signal.direction === 'BEARISH' ? 'text-red-400' :
                            'text-gray-400'
                          }`}>
                            {signal.direction === 'BULLISH' ? '↑' : signal.direction === 'BEARISH' ? '↓' : '−'}
                          </span>
                          <span className="text-yellow-400 text-xs">
                            {'★'.repeat(signal.stars || 0)}
                          </span>
                          <span className="font-bold text-xs" style={{ color: '#55b685' }}>
                            [{signal.grade}]
                          </span>
                          <span className="text-gray-500 text-xs">
                            {signal.confidence?.toFixed(1) || '0.0'}
                          </span>
                        </div>
                      </td>

                      {/* Entry @ Bars */}
                      <td className="p-2">
                        <div className="flex flex-col gap-0.5">
                          <span className="text-gray-300 text-xs">${signal.entry_price.toFixed(2)}</span>
                          <span className={`text-xs ${isPremature ? 'text-yellow-400' : 'text-gray-500'}`}>
                            @ {signal.bar_count_at_signal || 0}b
                            {isPremature && ' ⚠️'}
                          </span>
                        </div>
                      </td>

                      {/* Multi-timeframe evaluation columns */}
                      <td className="p-2 text-center">
                        {getBarEvalDisplay(signal.result_5_bars, signal.pnl_at_5_bars)}
                      </td>
                      <td className="p-2 text-center">
                        {getBarEvalDisplay(signal.result_10_bars, signal.pnl_at_10_bars)}
                      </td>
                      <td className="p-2 text-center">
                        {getBarEvalDisplay(signal.result_20_bars, signal.pnl_at_20_bars)}
                      </td>
                      <td className="p-2 text-center">
                        {getBarEvalDisplay(signal.result_50_bars, signal.pnl_at_50_bars)}
                      </td>

                      {/* Best Result */}
                      <td className="p-2 text-center">
                        {bestResult ? (
                          <div className="flex flex-col items-center gap-0.5">
                            <span className={`text-xs font-bold ${
                              bestResult.result === 'correct' ? 'text-green-400' :
                              bestResult.result === 'wrong' ? 'text-red-400' :
                              'text-gray-400'
                            }`}>
                              {bestResult.result === 'correct' ? '✓' : bestResult.result === 'wrong' ? '✗' : '~'}
                            </span>
                            <span className="text-gray-500 text-xs">{bestResult.frame}</span>
                          </div>
                        ) : (
                          <span className="text-gray-600 text-xs">-</span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="p-2 text-center">
                        <span className={`text-xs font-medium ${
                          signal.passed_filter ? 'text-green-400' : 'text-gray-500'
                        }`}>
                          {signal.passed_filter ? 'SHOWN' : 'HIDDEN'}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
