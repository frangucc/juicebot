'use client'

import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import StockChart from './StockChart'
import ChatInterface from './ChatInterface'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function ChartAgentContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const symbol = searchParams.get('symbol') || 'AAPL'

  return (
    <div className="h-full w-full flex flex-col bg-gray-950">
      {/* Minimal Header - Max 50px */}
      <header className="h-[50px] flex-shrink-0 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/')}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-bold text-white">{symbol}</h1>
        </div>
        <div className="text-sm text-gray-400">Chart Agent</div>
      </header>

      {/* Main Content - Split 25/75 */}
      <div className="flex-1 flex overflow-hidden" style={{ minHeight: 0 }}>
        {/* Left Side - Chat Interface (25%) */}
        <div className="w-1/4 h-full border-r border-gray-800 bg-gray-900">
          <ChatInterface symbol={symbol} />
        </div>

        {/* Right Side - Chart (75%) */}
        <div className="w-3/4 h-full bg-gray-950" style={{ minHeight: 0 }}>
          <StockChart symbol={symbol} />
        </div>
      </div>
    </div>
  )
}
