'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface Alert {
  id: string;
  symbol: string;
  alert_type: string;
  trigger_price: number;
  trigger_time: string;
  conditions: {
    pct_move: number;
    previous_close: number;
  };
  metadata: {
    bid: number;
    ask: number;
  };
}

export default function LiveFeedPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Poll for new alerts every 2 seconds
    const pollAlerts = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/alerts?limit=100`);
        if (response.ok) {
          const data = await response.json();
          setAlerts(data);
          setIsConnected(true);
        }
      } catch (error) {
        console.error('Failed to fetch alerts:', error);
        setIsConnected(false);
      }
    };

    // Initial fetch
    pollAlerts();

    // Poll every 2 seconds
    const interval = setInterval(pollAlerts, 2000);

    return () => clearInterval(interval);
  }, []);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
      hour12: false,
    });
  };

  const getColorClass = (pctMove: number) => {
    if (pctMove > 0) return 'text-green-400';
    if (pctMove < 0) return 'text-red-400';
    return 'text-gray-400';
  };

  return (
    <div className="min-h-screen bg-black p-4 font-mono text-green-400">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 border-b border-green-800 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold mb-2">
                ⚡ ALERT FEED
              </h1>
              <p className="text-green-600 text-sm">
                Real-time price movement alerts • 11,895 symbols monitored
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
                className="px-4 py-2 bg-green-900 text-green-300 rounded font-medium transition-colors border border-green-600"
              >
                Alert Feed
              </Link>
              <Link
                href="/raw-feed"
                className="px-4 py-2 bg-green-900/50 hover:bg-green-900 text-green-700 hover:text-green-400 rounded font-medium transition-colors border border-green-800"
              >
                Raw Data
              </Link>
            </div>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="mb-6 grid grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-green-800 rounded p-3">
            <div className="text-green-600 text-xs mb-1 uppercase tracking-wider">Status</div>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
              <span className="text-lg font-bold text-green-300">{isConnected ? 'CONNECTED' : 'OFFLINE'}</span>
            </div>
          </div>
          <div className="bg-gray-900 border border-green-800 rounded p-3">
            <div className="text-green-600 text-xs mb-1 uppercase tracking-wider">Total Alerts</div>
            <div className="text-2xl font-bold text-green-300">{alerts.length}</div>
          </div>
          <div className="bg-gray-900 border border-green-800 rounded p-3">
            <div className="text-green-600 text-xs mb-1 uppercase tracking-wider">Unique Symbols</div>
            <div className="text-2xl font-bold text-green-300">
              {new Set(alerts.map((a) => a.symbol)).size}
            </div>
          </div>
          <div className="bg-gray-900 border border-green-800 rounded p-3">
            <div className="text-green-600 text-xs mb-1 uppercase tracking-wider">Avg Move</div>
            <div className="text-2xl font-bold text-green-300">
              {alerts.length > 0
                ? (
                    alerts
                      .filter(a => a.conditions?.pct_move !== undefined)
                      .reduce((sum, a) => sum + Math.abs(a.conditions.pct_move), 0) /
                    (alerts.filter(a => a.conditions?.pct_move !== undefined).length || 1)
                  ).toFixed(2)
                : '0.00'}
              %
            </div>
          </div>
        </div>

        {/* Alert Feed */}
        <div className="bg-gray-950 border border-green-800 rounded overflow-hidden">
          <div className="p-3 border-b border-green-800 bg-gray-900">
            <div className="flex items-center justify-between">
              <div className="text-xs text-green-600 uppercase tracking-wider">
                ⚡ ALERT STREAM
              </div>
              <div className="text-xs text-green-700">
                Refreshing every 2 seconds • 11,895 symbols monitored
              </div>
            </div>
          </div>
          <div className="h-[600px] overflow-y-auto p-4 space-y-2 bg-black">
            {alerts.length === 0 ? (
              <div className="text-center py-12 text-green-700">
                <div className="text-4xl mb-3">⏳</div>
                <div className="text-green-500">Waiting for alerts...</div>
                <div className="text-sm mt-2 text-green-800">
                  The screener is monitoring 11,895 symbols
                </div>
              </div>
            ) : (
              [...alerts].reverse().map((alert) => {
                const pctMove = alert.conditions?.pct_move || 0;
                const previousClose = alert.conditions?.previous_close || 0;
                const direction = pctMove > 0 ? 'up' : 'down';
                const arrow = pctMove > 0 ? '↑' : '↓';

                return (
                  <div
                    key={alert.id}
                    className="flex items-center gap-3 text-sm border-b border-green-900 pb-2 hover:bg-green-950/30 transition-colors p-2 rounded"
                  >
                    <div className="text-green-700 text-xs w-32 flex-shrink-0">
                      {formatTime(alert.trigger_time)}
                    </div>
                    <div className="font-bold text-green-300 w-16 flex-shrink-0">
                      {alert.symbol}
                    </div>
                    <div className="text-green-700 w-16">moved</div>
                    <div className={`font-bold w-20 ${getColorClass(pctMove)}`}>
                      {arrow} {Math.abs(pctMove).toFixed(2)}%
                    </div>
                    <div className="text-green-700">
                      (current: <span className="text-green-300">${alert.trigger_price.toFixed(4)}</span>,
                      previous: <span className="text-green-600">${previousClose.toFixed(4)}</span>)
                    </div>
                    <div className="ml-auto text-xs text-green-700">
                      Bid: ${alert.metadata?.bid?.toFixed(2) || 'N/A'} / Ask: ${alert.metadata?.ask?.toFixed(2) || 'N/A'}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
