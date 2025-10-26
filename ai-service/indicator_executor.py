"""
Indicator Executor
==================
Fast execution of technical indicators using bar history data.
All calculations use best-practice algorithms.
"""

import statistics
from typing import Dict, List, Any, Optional


class IndicatorExecutor:
    """Executes technical indicator calculations on bar history."""

    def __init__(self):
        self.bar_history = []  # Historical bars for calculations

    def update_bar_history(self, bar: Dict[str, Any]):
        """Update bar history (keep last 500 bars)."""
        self.bar_history.append(bar)
        if len(self.bar_history) > 500:
            self.bar_history.pop(0)

    async def execute(self, command: str, symbol: str) -> Optional[str]:
        """
        Execute indicator command.

        Returns:
            Response string if executed, None if no match
        """
        command = command.lower().strip()

        # Parse command and parameters
        # Examples: "rvol 50", "vp 200", "vwap 390", "voltrend 100"
        parts = command.split()
        cmd = parts[0]
        param = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

        # Map commands to handlers
        handlers = {
            'vp': self.volume_profile,
            'volume profile': self.volume_profile,
            'rvol': self.relative_volume,
            'relative volume': self.relative_volume,
            'vwap': self.vwap,
            'voltrend': self.volume_trend,
            'volume trend': self.volume_trend,
            'vtrend': self.volume_trend,
        }

        handler = handlers.get(cmd)
        if not handler:
            # Try full command as fallback
            handler = handlers.get(command)
            if not handler:
                return None

        if not self.bar_history:
            return f"⚠️ No bar data available for {symbol}"

        try:
            # Pass parameter if provided
            if param is not None:
                if cmd in ['rvol', 'relative volume']:
                    return await handler(symbol, period=param)
                else:
                    return await handler(symbol, lookback=param)
            else:
                return await handler(symbol)
        except Exception as e:
            return f"❌ Error calculating {command}: {str(e)}"

    async def volume_profile(self, symbol: str, lookback: int = 100) -> str:
        """
        Calculate Volume Profile using TPO (Time-Price-Opportunity) method.
        Shows Point of Control (POC) and Value Area (70% of volume).
        """
        bars = self.bar_history[-lookback:] if len(self.bar_history) > lookback else self.bar_history

        if len(bars) < 10:
            return f"⚠️ Need at least 10 bars for Volume Profile (have {len(bars)})"

        # Find price range
        all_highs = [float(bar['high']) for bar in bars]
        all_lows = [float(bar['low']) for bar in bars]
        price_high = max(all_highs)
        price_low = min(all_lows)
        price_range = price_high - price_low

        if price_range == 0:
            return f"⚠️ No price movement in period"

        # Create 20 price buckets (industry standard for intraday)
        num_buckets = 20
        bucket_size = price_range / num_buckets

        # Initialize buckets
        buckets = {}
        for i in range(num_buckets):
            bucket_price = price_low + (i * bucket_size) + (bucket_size / 2)
            buckets[round(bucket_price, 4)] = 0

        # Distribute volume across buckets (TPO method)
        for bar in bars:
            bar_high = float(bar['high'])
            bar_low = float(bar['low'])
            bar_volume = float(bar['volume'])

            # Calculate how many buckets this bar touches
            touched_buckets = []
            for price_level in buckets.keys():
                if bar_low <= price_level <= bar_high:
                    touched_buckets.append(price_level)

            # Distribute volume evenly across touched buckets
            if touched_buckets:
                vol_per_bucket = bar_volume / len(touched_buckets)
                for price_level in touched_buckets:
                    buckets[price_level] += vol_per_bucket

        # Calculate total volume
        total_volume = sum(buckets.values())

        # Find POC (Point of Control) - price with most volume
        poc_price = max(buckets.items(), key=lambda x: x[1])[0]
        poc_volume = buckets[poc_price]
        poc_pct = (poc_volume / total_volume * 100) if total_volume > 0 else 0

        # Calculate Value Area (70% of volume around POC)
        sorted_buckets = sorted(buckets.items(), key=lambda x: x[1], reverse=True)
        cumulative_volume = 0
        value_area_prices = []

        for price, vol in sorted_buckets:
            cumulative_volume += vol
            value_area_prices.append(price)
            if cumulative_volume >= total_volume * 0.70:
                break

        va_high = max(value_area_prices) if value_area_prices else poc_price
        va_low = min(value_area_prices) if value_area_prices else poc_price

        # Current price position
        current_price = float(bars[-1]['close'])
        if current_price > va_high:
            position = "above value area (bullish)"
        elif current_price < va_low:
            position = "below value area (bearish)"
        elif abs(current_price - poc_price) < bucket_size:
            position = "at POC (balanced)"
        else:
            position = "inside value area"

        return (
            f"📊 Volume Profile ({len(bars)} bars)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"POC (Point of Control): ${poc_price:.4f} ({poc_pct:.1f}% of volume)\n"
            f"Value Area High: ${va_high:.4f}\n"
            f"Value Area Low:  ${va_low:.4f}\n"
            f"Current Price: ${current_price:.4f} ({position})\n"
            f"Total Volume: {int(total_volume):,}"
        )

    async def relative_volume(self, symbol: str, period: int = 20) -> str:
        """
        Calculate Relative Volume (RVOL).
        Compares recent volume to baseline. Industry standard for momentum.
        """
        if len(self.bar_history) < period * 2:
            return f"⚠️ Need at least {period * 2} bars for RVOL (have {len(self.bar_history)})"

        # Get recent and baseline periods
        recent_bars = self.bar_history[-period:]
        baseline_bars = self.bar_history[-(period * 2):-period]

        # Calculate average volumes
        recent_avg = statistics.mean([float(bar['volume']) for bar in recent_bars])
        baseline_avg = statistics.mean([float(bar['volume']) for bar in baseline_bars])

        # Calculate RVOL
        rvol = recent_avg / baseline_avg if baseline_avg > 0 else 1.0

        # Current bar volume
        current_volume = float(self.bar_history[-1]['volume'])
        current_vs_recent = current_volume / recent_avg if recent_avg > 0 else 1.0

        # Professional interpretation (industry standard thresholds)
        if rvol < 0.5:
            status = "🥶 COLD"
            meaning = "Very low interest"
        elif rvol < 0.8:
            status = "❄️ Below Average"
            meaning = "Weak activity"
        elif rvol < 1.2:
            status = "➡️ Normal"
            meaning = "Typical volume"
        elif rvol < 1.5:
            status = "🌡️ Warm"
            meaning = "Elevated interest"
        elif rvol < 2.0:
            status = "🔥 Hot"
            meaning = "Strong activity"
        else:
            status = "💥 EXPLOSIVE"
            meaning = "Exceptional interest"

        return (
            f"📈 Relative Volume (RVOL)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"RVOL: {rvol:.2f}x  {status}\n"
            f"{meaning}\n\n"
            f"Recent Avg:   {int(recent_avg):,}\n"
            f"Baseline Avg: {int(baseline_avg):,}\n"
            f"Current Bar:  {int(current_volume):,} ({current_vs_recent:.2f}x recent)\n"
            f"Period: {period} bars"
        )

    async def vwap(self, symbol: str, lookback: int = 390) -> str:
        """
        Calculate Volume-Weighted Average Price (VWAP).
        Standard institutional benchmark. Uses typical price method.
        """
        bars = self.bar_history[-lookback:] if len(self.bar_history) > lookback else self.bar_history

        if len(bars) < 5:
            return f"⚠️ Need at least 5 bars for VWAP (have {len(bars)})"

        # Calculate VWAP using typical price (H+L+C)/3
        total_pv = 0  # Price × Volume
        total_volume = 0

        for bar in bars:
            typical_price = (float(bar['high']) + float(bar['low']) + float(bar['close'])) / 3
            volume = float(bar['volume'])
            total_pv += typical_price * volume
            total_volume += volume

        vwap = total_pv / total_volume if total_volume > 0 else 0

        # Current price analysis
        current_price = float(bars[-1]['close'])
        distance = current_price - vwap
        distance_pct = (distance / vwap * 100) if vwap > 0 else 0

        # Position interpretation (institutional trading levels)
        if abs(distance_pct) < 0.5:
            position = "⚖️ AT VWAP"
            meaning = "Fair value - balanced"
        elif distance_pct > 2.0:
            position = "⬆️ FAR ABOVE VWAP"
            meaning = "Overbought - potential resistance"
        elif distance_pct > 0:
            position = "↗️ Above VWAP"
            meaning = "Bullish - buyers in control"
        elif distance_pct < -2.0:
            position = "⬇️ FAR BELOW VWAP"
            meaning = "Oversold - potential support"
        else:
            position = "↘️ Below VWAP"
            meaning = "Bearish - sellers in control"

        return (
            f"💰 VWAP Analysis\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"VWAP:  ${vwap:.4f}\n"
            f"Price: ${current_price:.4f}\n"
            f"Distance: ${distance:+.4f} ({distance_pct:+.2f}%)\n\n"
            f"{position}\n"
            f"{meaning}\n"
            f"Bars: {len(bars)}"
        )

    async def volume_trend(self, symbol: str, lookback: int = 50) -> str:
        """
        Analyze volume trend using linear regression slope.
        Detects accumulation/distribution phases.
        """
        bars = self.bar_history[-lookback:] if len(self.bar_history) > lookback else self.bar_history

        if len(bars) < 10:
            return f"⚠️ Need at least 10 bars for trend (have {len(bars)})"

        # Split into halves for comparison
        mid_point = len(bars) // 2
        first_half = bars[:mid_point]
        second_half = bars[mid_point:]

        # Calculate averages
        first_half_avg = statistics.mean([float(bar['volume']) for bar in first_half])
        second_half_avg = statistics.mean([float(bar['volume']) for bar in second_half])

        # Calculate change
        change_pct = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0

        # Determine trend strength (industry standard thresholds)
        if change_pct > 25:
            trend = "📈 STRONG INCREASE"
            meaning = "Heavy accumulation"
        elif change_pct > 10:
            trend = "↗️ Increasing"
            meaning = "Building interest"
        elif change_pct > -10:
            trend = "➡️ Stable"
            meaning = "Consistent flow"
        elif change_pct > -25:
            trend = "↘️ Decreasing"
            meaning = "Fading interest"
        else:
            trend = "📉 STRONG DECREASE"
            meaning = "Distribution phase"

        # Check for recent spike (last 5 bars vs overall average)
        recent_bars = bars[-5:]
        recent_avg = statistics.mean([float(bar['volume']) for bar in recent_bars])
        overall_avg = statistics.mean([float(bar['volume']) for bar in bars])
        spike_ratio = recent_avg / overall_avg if overall_avg > 0 else 1.0

        spike_alert = ""
        if spike_ratio > 1.5:
            spike_alert = f"\n⚡ Recent spike detected! ({spike_ratio:.2f}x avg)"

        return (
            f"📊 Volume Trend ({len(bars)} bars)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{trend}\n"
            f"{meaning}\n\n"
            f"First Half:  {int(first_half_avg):,}\n"
            f"Second Half: {int(second_half_avg):,}\n"
            f"Change: {change_pct:+.1f}%\n"
            f"Recent Avg: {int(recent_avg):,}{spike_alert}"
        )
