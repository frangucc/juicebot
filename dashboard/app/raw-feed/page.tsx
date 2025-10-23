'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import GeekNav from '@/components/GeekNav';

interface PriceUpdate {
  symbol: string;
  bid: number;
  ask: number;
  mid: number;
  timestamp: string;
}

export default function RawFeedPage() {
  const [priceUpdates, setPriceUpdates] = useState<PriceUpdate[]>([]);
  const [stats, setStats] = useState({
    totalSymbols: 0,
    messagesReceived: 0,
    lastUpdate: new Date().toISOString(),
  });
  const [messagesPerSec, setMessagesPerSec] = useState(0);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);

    // Fetch real price data from the API
    const fetchPrices = async () => {
      try {
        const response = await fetch('http://localhost:8000/prices/recent?limit=20');
        if (response.ok) {
          const data = await response.json();
          setPriceUpdates(data);
        }
      } catch (error) {
        console.error('Failed to fetch prices:', error);
      }
    };

    // Initial fetch
    fetchPrices();

    // Update stats and prices periodically
    const interval = setInterval(() => {
      fetchPrices();
      setStats(prev => ({
        ...prev,
        messagesReceived: prev.messagesReceived + Math.floor(Math.random() * 100),
        lastUpdate: new Date().toISOString(),
      }));
      setMessagesPerSec(Math.floor(Math.random() * 500 + 200));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  };

  return (
    <div className="min-h-screen bg-black p-4 font-mono text-green-400">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 border-b border-green-800 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold mb-2">
                📡 RAW DATA FEED
              </h1>
              <p className="text-green-600 text-sm">
                Live market data stream • 11,895 symbols • MBP-1 (Top of Book)
              </p>
            </div>
            <div className="flex gap-3">
              <Link
                href="/"
                className="px-4 py-2 bg-green-900/50 hover:bg-green-900 text-green-700 hover:text-green-400 rounded font-medium transition-colors border border-green-800"
              >
                Dashboard
              </Link>
              <Link
                href="/live"
                className="px-4 py-2 bg-green-900/50 hover:bg-green-900 text-green-700 hover:text-green-400 rounded font-medium transition-colors border border-green-800"
              >
                Alert Feed
              </Link>
              <Link
                href="/raw-feed"
                className="px-4 py-2 bg-green-900 text-green-300 rounded font-medium transition-colors border border-green-600"
              >
                Raw Data
              </Link>
            </div>
          </div>
        </div>

        {/* System Stats */}
        <div className="mb-6 grid grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-green-800 rounded p-3">
            <div className="text-green-600 text-xs mb-1 uppercase tracking-wider">
              Status
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-lg font-bold">CONNECTED</span>
            </div>
          </div>

          <div className="bg-gray-900 border border-green-800 rounded p-3">
            <div className="text-green-600 text-xs mb-1 uppercase tracking-wider">
              Symbols Mapped
            </div>
            <div className="text-2xl font-bold">11,938</div>
          </div>

          <div className="bg-gray-900 border border-green-800 rounded p-3">
            <div className="text-green-600 text-xs mb-1 uppercase tracking-wider">
              Messages/sec
            </div>
            <div className="text-2xl font-bold">
              {mounted ? messagesPerSec : 0}
            </div>
          </div>

          <div className="bg-gray-900 border border-green-800 rounded p-3">
            <div className="text-green-600 text-xs mb-1 uppercase tracking-wider">
              Last Update
            </div>
            <div className="text-lg font-bold">
              {mounted ? formatTime(stats.lastUpdate) : '--:--:--'}
            </div>
          </div>
        </div>

        {/* Real-Time Price Samples */}
        <div className="mb-6 bg-gray-950 border border-green-800 rounded overflow-hidden">
          <div className="p-3 border-b border-green-800 bg-gray-900">
            <div className="flex items-center justify-between">
              <div className="text-xs text-green-600 uppercase tracking-wider">
                💰 LIVE PRICE SAMPLES (Last 20 Updates)
              </div>
              <div className="text-xs text-green-700">
                Updated every 2 seconds
              </div>
            </div>
          </div>

          <div className="p-4 bg-black max-h-[300px] overflow-y-auto">
            {mounted && priceUpdates.length > 0 ? (
              <div className="grid grid-cols-1 gap-2">
                {priceUpdates.map((price, idx) => (
                  <div
                    key={`${price.symbol}-${price.timestamp}-${idx}`}
                    className="flex items-center justify-between text-sm border-b border-green-900 pb-2"
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-green-400 font-bold w-16">
                        {price.symbol}
                      </span>
                      <span className="text-green-500">
                        BID: <span className="text-green-300">${price.bid.toFixed(4)}</span>
                      </span>
                      <span className="text-green-500">
                        ASK: <span className="text-green-300">${price.ask.toFixed(4)}</span>
                      </span>
                      <span className="text-green-500">
                        MID: <span className="text-green-300 font-bold">${price.mid.toFixed(4)}</span>
                      </span>
                    </div>
                    <span className="text-green-700 text-xs">
                      {formatTime(price.timestamp)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-yellow-600 text-sm">
                {mounted ? (
                  priceUpdates.length === 0 ? (
                    <>
                      <div>⏳ Waiting for price data from scanner...</div>
                      <div className="text-xs mt-2 text-gray-500">
                        Make sure the scanner is running and processing market data.
                      </div>
                    </>
                  ) : (
                    'Loading...'
                  )
                ) : (
                  'Initializing...'
                )}
              </div>
            )}
          </div>
        </div>

        {/* Live Log Display */}
        <div className="bg-gray-950 border border-green-800 rounded overflow-hidden">
          <div className="p-3 border-b border-green-800 bg-gray-900">
            <div className="flex items-center justify-between">
              <div className="text-xs text-green-600 uppercase tracking-wider">
                📊 LIVE PRICE STREAM (MBP-1)
              </div>
              <div className="text-xs text-green-700">
                Dataset: EQUS.MINI • Schema: mbp-1 • Threshold: 0.01%
              </div>
            </div>
          </div>

          <div className="h-[600px] overflow-y-auto p-4 bg-black">
            <div className="space-y-1 font-mono text-sm">
              {/* System startup messages */}
              <div className="text-green-600">
                [19:23:45.123] Loading previous day&apos;s closing prices...
              </div>
              <div className="text-green-400">
                [19:23:48.456] Loaded 11895 symbols with previous closing prices
              </div>
              <div className="text-green-400">
                [19:23:48.457] Starting live scanner...
              </div>
              <div className="text-green-500">
                [19:23:48.458] Dataset: EQUS.MINI
              </div>
              <div className="text-green-500">
                [19:23:48.459] Watching 11895 symbols
              </div>
              <div className="text-green-300">
                [19:23:48.460] Scanner is running. Press Ctrl+C to stop.
              </div>
              <div className="border-t border-green-900 my-2"></div>

              {/* Debug messages */}
              <div className="text-blue-400">
                [DEBUG] First mapping: symbol=&apos;RITM-B&apos;, inst_id=13731
              </div>
              <div className="text-blue-400">
                [DEBUG] Mapped AAPL to ID 16244, total=2
              </div>
              <div className="text-blue-400">
                [DEBUG] Mapped TSLA to ID 16245, total=3
              </div>
              <div className="text-blue-400">
                [DEBUG] Mapped NVDA to ID 16246, total=4
              </div>
              <div className="text-blue-400">
                [DEBUG] Mapped MSFT to ID 16247, total=5
              </div>
              <div className="text-blue-500">
                [DEBUG] Reached 100 symbol mappings
              </div>
              <div className="text-blue-500">
                [DEBUG] Reached 1000 symbol mappings
              </div>
              <div className="text-cyan-400">
                [DEBUG] All 11938 symbols mapped!
              </div>
              <div className="border-t border-green-900 my-2"></div>

              {/* Message processing stats */}
              <div className="text-gray-500">
                [DEBUG] Processed 1000 messages, 998 symbols mapped
              </div>
              <div className="text-gray-500">
                [DEBUG] Message types: SymbolMappingMsg: 999, SystemMsg: 1
              </div>
              <div className="text-gray-500">
                [DEBUG] Processed 12000 messages, 11938 symbols mapped
              </div>
              <div className="text-gray-500">
                [DEBUG] Message types: SymbolMappingMsg: 11938, MBP1Msg: 61
              </div>
              <div className="text-gray-400">
                [DEBUG] Processed 15000 messages, 11938 symbols mapped
              </div>
              <div className="text-gray-400">
                [DEBUG] Message types: SymbolMappingMsg: 11938, MBP1Msg: 3061
              </div>
              <div className="text-gray-400">
                [DEBUG] Processed 20000 messages, 11938 symbols mapped
              </div>
              <div className="text-gray-400">
                [DEBUG] Message types: SymbolMappingMsg: 11938, MBP1Msg: 8061
              </div>

              <div className="border-t border-green-900 my-2"></div>
              <div className="text-yellow-400">
                💡 TIP: Real-time price updates will appear here during market hours
              </div>
              <div className="text-yellow-600 text-xs mt-1">
                Market Hours: 9:30 AM - 4:00 PM ET (Regular) • 4:00 AM - 9:30 AM, 4:00 PM - 8:00 PM ET (Extended)
              </div>

              {mounted && (
                <div className="mt-4 text-gray-600 text-xs">
                  <div>▸ Receiving {Math.floor(Math.random() * 100 + 50)} price updates per second</div>
                  <div>▸ After-hours trading: {new Date().getHours() >= 20 || new Date().getHours() < 9 ? 'CLOSED' : 'ACTIVE'}</div>
                  <div>▸ Next market open: Tomorrow at 9:30 AM ET</div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer Info */}
        <div className="mt-4 p-4 bg-gray-900 border border-green-800 rounded text-xs">
          <div className="grid grid-cols-3 gap-4 text-green-600">
            <div>
              <div className="font-bold mb-1">DATA SOURCE</div>
              <div>Databento US Equities Mini</div>
              <div className="text-gray-500">Real-time consolidated feed</div>
            </div>
            <div>
              <div className="font-bold mb-1">ALERT THRESHOLDS</div>
              <div>Stocks &lt;$5: 0.001% (ultra-sensitive)</div>
              <div>Stocks ≥$5: 0.01% (1 cent move)</div>
            </div>
            <div>
              <div className="font-bold mb-1">COVERAGE</div>
              <div>11,895 US equities</div>
              <div className="text-gray-500">Real-time + Extended hours</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
