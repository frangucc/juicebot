'use client'

interface StatsCardsProps {
  stats: {
    total_alerts: number
    unique_symbols: number
    avg_pct_move: number
    by_type: Record<string, number>
  }
  leaderboardCounts?: {
    movers_20plus: number
    movers_10to20: number
    movers_1to10: number
  }
}

export function StatsCards({ stats, leaderboardCounts }: StatsCardsProps) {
  return (
    <div className="grid grid-cols-3 md:grid-cols-3 lg:grid-cols-6 gap-2 md:gap-4 mb-6">
      {/* Total Alerts */}
      <div className="bg-gray-900 border border-green-800 rounded p-2 md:p-4">
        <p className="text-2xl md:text-3xl font-bold text-green-300 mb-0.5">{stats.total_alerts}</p>
        <h3 className="text-green-600 text-[10px] md:text-xs uppercase tracking-wider">
          Total Alerts (24h)
        </h3>
      </div>

      {/* Unique Symbols */}
      <div className="bg-gray-900 border border-green-800 rounded p-2 md:p-4">
        <p className="text-2xl md:text-3xl font-bold text-green-300 mb-0.5">{stats.unique_symbols}</p>
        <h3 className="text-green-600 text-[10px] md:text-xs uppercase tracking-wider">
          Unique Symbols
        </h3>
      </div>

      {/* Average Move */}
      <div className="bg-gray-900 border border-green-800 rounded p-2 md:p-4">
        <p className="text-2xl md:text-3xl font-bold text-green-300 mb-0.5">{stats.avg_pct_move.toFixed(2)}%</p>
        <h3 className="text-green-600 text-[10px] md:text-xs uppercase tracking-wider">
          Avg % Move
        </h3>
      </div>

      {/* 20%+ Movers */}
      {leaderboardCounts && (
        <>
          <div className="bg-gray-900 border border-red-800 rounded p-2 md:p-4">
            <p className="text-2xl md:text-3xl font-bold text-red-400 mb-0.5">{leaderboardCounts.movers_20plus}</p>
            <h3 className="text-red-600 text-[10px] md:text-xs uppercase tracking-wider">
              20%+ Movers
            </h3>
          </div>

          {/* 10-20% Movers */}
          <div className="bg-gray-900 border border-yellow-800 rounded p-2 md:p-4">
            <p className="text-2xl md:text-3xl font-bold text-yellow-400 mb-0.5">{leaderboardCounts.movers_10to20}</p>
            <h3 className="text-yellow-600 text-[10px] md:text-xs uppercase tracking-wider">
              10-20% Movers
            </h3>
          </div>

          {/* 1-10% Movers */}
          <div className="bg-gray-900 border border-green-800 rounded p-2 md:p-4">
            <p className="text-2xl md:text-3xl font-bold text-green-400 mb-0.5">{leaderboardCounts.movers_1to10}</p>
            <h3 className="text-green-600 text-[10px] md:text-xs uppercase tracking-wider">
              1-10% Movers
            </h3>
          </div>
        </>
      )}
    </div>
  )
}
