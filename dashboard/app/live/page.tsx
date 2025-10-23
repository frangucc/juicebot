'use client';

import Link from 'next/link';
import { useData } from '@/contexts/DataContext';

export default function LiveFeedPage() {
  const { alerts, loadingStatus, isLoading } = useData();

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
    <div className="min-h-screen bg-black p-4 md:p-6 font-mono text-green-400">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold mb-1">
                ⚡ ALERT FEED
              </h1>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  loadingStatus.includes('Live') || loadingStatus === 'Connected • Live'
                    ? 'bg-green-500'
                    : loadingStatus.includes('could not') || loadingStatus.includes('down')
                    ? 'bg-red-500'
                    : loadingStatus.includes('retrying') || loadingStatus.includes('issue')
                    ? 'bg-yellow-500'
                    : 'bg-green-700'
                }`}></div>
                <p className={`text-sm ${
                  loadingStatus.includes('Live') || loadingStatus === 'Connected • Live'
                    ? 'text-green-600'
                    : loadingStatus.includes('could not') || loadingStatus.includes('down')
                    ? 'text-red-600'
                    : loadingStatus.includes('retrying') || loadingStatus.includes('issue')
                    ? 'text-yellow-600'
                    : 'text-green-700'
                }`}>
                  {loadingStatus}
                </p>
              </div>
            </div>
            <div className="hidden md:flex gap-3">
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

        {/* Mobile Navigation */}
        <div className="md:hidden mb-6 flex gap-2 overflow-x-auto">
          <Link
            href="/"
            className="px-4 py-2 bg-green-900/50 hover:bg-green-900 text-green-700 hover:text-green-400 rounded font-medium transition-colors border border-green-800 whitespace-nowrap"
          >
            Dashboard
          </Link>
          <Link
            href="/live"
            className="px-4 py-2 bg-green-900 text-green-300 rounded font-medium transition-colors border border-green-600 whitespace-nowrap"
          >
            Alert Feed
          </Link>
          <Link
            href="/raw-feed"
            className="px-4 py-2 bg-green-900/50 hover:bg-green-900 text-green-700 hover:text-green-400 rounded font-medium transition-colors border border-green-800 whitespace-nowrap"
          >
            Raw Data
          </Link>
        </div>

        {/* Stats Bar */}
        <div className="mb-6 grid grid-cols-3 gap-3 md:gap-4">
          <div className="glass-card rounded-lg p-3 transition-all hover:shadow-glow-sm">
            <div className="text-teal-dark text-xs mb-1 uppercase tracking-wider">Total Alerts</div>
            <div className="text-2xl font-bold text-teal">{alerts.length}</div>
          </div>
          <div className="glass-card rounded-lg p-3 transition-all hover:shadow-glow-sm">
            <div className="text-teal-dark text-xs mb-1 uppercase tracking-wider">Unique Symbols</div>
            <div className="text-2xl font-bold text-teal">
              {new Set(alerts.map((a) => a.symbol)).size}
            </div>
          </div>
          <div className="glass-card rounded-lg p-3 transition-all hover:shadow-glow-sm">
            <div className="text-teal-dark text-xs mb-1 uppercase tracking-wider">Avg Move</div>
            <div className="text-2xl font-bold text-teal">
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
        <div className="bg-gray-950 border border-glass rounded-lg overflow-hidden">
          <div className="p-3 border-b border-glass glass-header">
            <div className="flex items-center justify-between">
              <div className="text-xs text-teal uppercase tracking-wider font-semibold">
                ⚡ ALERT STREAM
              </div>
              <div className="text-xs text-teal-dark">
                Refreshing every 2 seconds • 11,895 symbols monitored
              </div>
            </div>
          </div>
          <div className="h-[600px] overflow-y-auto p-4 space-y-2 bg-black">
            {isLoading && alerts.length === 0 ? (
              <div className="text-center py-12 text-green-700">
                <div className="text-4xl mb-3">⏳</div>
                <div className="text-green-500">{loadingStatus}</div>
                <div className="text-sm mt-2 text-green-800">
                  Loading recent alerts from the last 24 hours...
                </div>
              </div>
            ) : alerts.length === 0 ? (
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
