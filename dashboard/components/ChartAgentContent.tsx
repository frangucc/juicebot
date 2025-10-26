'use client'

import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import StockChart from './StockChartHistorical'
import ChatInterface from './ChatInterface'
import GamepadController from './GamepadController'

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

        {/* Right Side - Chart (75%) */}
        <div className="w-3/4 h-full" style={{ minHeight: 0 }}>
          <StockChart
            symbol={symbol}
            dataMode={dataMode}
            onReplayStatusChange={setReplayStatus}
          />
        </div>
      </div>

      {/* Gamepad Controller Widget */}
      <GamepadController
        symbol={symbol}
        onCommandExecute={(command, result) => {
          console.log('Gamepad command executed:', command, result)
        }}
      />
    </div>
  )
}
