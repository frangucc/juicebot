'use client'

interface StatsCardsProps {
  stats: {
    total_alerts: number
    unique_symbols: number
    avg_pct_move: number
    by_type: Record<string, number>
  }
}

export function StatsCards({ stats }: StatsCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {/* Total Alerts */}
      <div className="bg-gray-900 border border-green-800 rounded p-4">
        <h3 className="text-green-600 text-xs mb-1 uppercase tracking-wider">
          Total Alerts (24h)
        </h3>
        <p className="text-3xl font-bold text-green-300">{stats.total_alerts}</p>
      </div>

      {/* Unique Symbols */}
      <div className="bg-gray-900 border border-green-800 rounded p-4">
        <h3 className="text-green-600 text-xs mb-1 uppercase tracking-wider">
          Unique Symbols
        </h3>
        <p className="text-3xl font-bold text-green-300">{stats.unique_symbols}</p>
      </div>

      {/* Average Move */}
      <div className="bg-gray-900 border border-green-800 rounded p-4">
        <h3 className="text-green-600 text-xs mb-1 uppercase tracking-wider">
          Avg % Move
        </h3>
        <p className="text-3xl font-bold text-green-300">{stats.avg_pct_move.toFixed(2)}%</p>
      </div>
    </div>
  )
}
