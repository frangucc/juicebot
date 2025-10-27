#!/usr/bin/env python3
"""
Murphy Market Analysis Endpoint

Provides standalone market commentary using Murphy's Classifier logic.
Can be called by any strategy or on-demand for chart analysis.

Example usage:
    murphy_analysis = get_murphy_analysis(bars, lookback=50)
    print(murphy_analysis['narrative'])
    # Output: "🟢 Bullish - New money entering on rising volume.
    #          Price efficiency strong. Likely continuation."
"""

from typing import List, Dict
from murphy_classifier import MurphyClassifier, Bar


class MurphyAnalyzer:
    """
    Standalone Murphy analysis for any market situation.
    Maps OHLCV patterns to John Murphy's price-volume-OI logic.
    """

    def __init__(self):
        self.murphy = MurphyClassifier()

    def analyze_current_market(
        self,
        bars: List[Bar],
        lookback: int = 50
    ) -> Dict:
        """
        Analyze current market state and provide narrative.

        Returns:
            {
                'bias': '🟢 Bullish' | '🔴 Bearish' | '⚪ Neutral',
                'interpretation': 'Market Behavior / Interpretation',
                'narrative': 'Full explanation',
                'confidence': 0-10,
                'recommendation': 'continuation' | 'reversal' | 'wait',
                'components': {...}
            }
        """
        if len(bars) < lookback:
            lookback = len(bars)

        current_index = len(bars) - 1
        current_bar = bars[current_index]

        # Get Murphy's base classification
        murphy_signal = self.murphy.classify(bars, current_index, lookback)

        # Analyze recent price action (last 5-10 bars)
        recent_bars = bars[-min(10, len(bars)):]
        price_trend = self._analyze_price_trend(recent_bars)
        volume_trend = self._analyze_volume_trend(recent_bars, bars, lookback)

        # Map to Price-Volume-OI table
        interpretation = self._map_to_murphy_table(
            price_trend,
            volume_trend,
            murphy_signal
        )

        # Generate narrative
        narrative = self._generate_narrative(
            price_trend,
            volume_trend,
            murphy_signal,
            interpretation
        )

        # Determine recommendation
        recommendation = self._get_recommendation(
            interpretation['bias'],
            murphy_signal.grade,
            murphy_signal.stars
        )

        return {
            'bias': interpretation['bias'],
            'interpretation': interpretation['behavior'],
            'narrative': narrative,
            'confidence': murphy_signal.grade,
            'stars': murphy_signal.stars,
            'direction': murphy_signal.direction,
            'recommendation': recommendation,
            'components': {
                'price_trend': price_trend,
                'volume_trend': volume_trend,
                'rvol': murphy_signal.rvol,
                'volume_efficiency': murphy_signal.volume_efficiency,
                'body_ratio': murphy_signal.body_ratio,
                'atr_ratio': murphy_signal.atr_ratio,
            },
            'murphy_label': self.murphy.format_label(murphy_signal)
        }

    def _analyze_price_trend(self, recent_bars: List[Bar]) -> str:
        """Determine if price is rising, falling, or flat"""
        if len(recent_bars) < 2:
            return 'flat'

        first_close = recent_bars[0].close
        last_close = recent_bars[-1].close
        change_pct = ((last_close - first_close) / first_close) * 100

        if change_pct > 0.5:
            return 'rising'
        elif change_pct < -0.5:
            return 'falling'
        else:
            return 'flat'

    def _analyze_volume_trend(
        self,
        recent_bars: List[Bar],
        all_bars: List[Bar],
        lookback: int
    ) -> str:
        """Determine if volume is rising, falling, or normal"""
        if len(recent_bars) < 2 or len(all_bars) < lookback:
            return 'normal'

        # Average volume of recent bars
        recent_avg_volume = sum(b.volume for b in recent_bars) / len(recent_bars)

        # Historical average
        historical_bars = all_bars[-lookback:-len(recent_bars)] if len(all_bars) > len(recent_bars) else all_bars
        if not historical_bars:
            return 'normal'

        historical_avg_volume = sum(b.volume for b in historical_bars) / len(historical_bars)

        if historical_avg_volume == 0:
            return 'normal'

        ratio = recent_avg_volume / historical_avg_volume

        if ratio > 1.3:
            return 'rising'
        elif ratio < 0.7:
            return 'falling'
        else:
            return 'normal'

    def _estimate_synthetic_oi_trend(
        self,
        price_trend: str,
        volume_trend: str,
        volume_efficiency: float,
        body_ratio: float
    ) -> str:
        """
        Estimate if synthetic OI is rising or falling.

        Rising OI = new positions opening (conviction)
        Falling OI = positions closing (exhaustion/covering)
        """
        # High volume + efficient move + directional body = rising OI
        efficiency_high = volume_efficiency * 1000 > 0.3
        body_strong = body_ratio > 0.6

        if volume_trend == 'rising' and efficiency_high and body_strong:
            return 'rising'
        elif volume_trend == 'falling':
            return 'falling'
        else:
            return 'normal'

    def _map_to_murphy_table(
        self,
        price_trend: str,
        volume_trend: str,
        murphy_signal
    ) -> Dict:
        """
        Map current conditions to John Murphy's Price-Volume-OI table.

        Returns bias and interpretation.
        """
        # Estimate synthetic OI
        oi_trend = self._estimate_synthetic_oi_trend(
            price_trend,
            volume_trend,
            murphy_signal.volume_efficiency,
            murphy_signal.body_ratio
        )

        # Map to Murphy's table
        if price_trend == 'rising' and volume_trend == 'rising' and oi_trend == 'rising':
            return {
                'bias': '🟢 Bullish',
                'behavior': 'New money entering; buyers in control and adding positions. Confirms uptrend strength.',
                'pattern': 'continuation'
            }

        elif price_trend == 'falling' and volume_trend == 'rising' and oi_trend == 'rising':
            return {
                'bias': '🔴 Bearish',
                'behavior': 'New shorts being opened aggressively; sellers in control, trend expanding.',
                'pattern': 'continuation'
            }

        elif price_trend == 'rising' and volume_trend == 'falling' and oi_trend == 'falling':
            return {
                'bias': '⚪ Weak Bullish',
                'behavior': 'Short covering rally on declining participation. Not sustained buying.',
                'pattern': 'temporary'
            }

        elif price_trend == 'falling' and volume_trend == 'falling' and oi_trend == 'falling':
            return {
                'bias': '🟢 Bullish Divergence',
                'behavior': 'Long liquidation only; no new shorts. Market losing energy → possible end of downtrend.',
                'pattern': 'reversal_setup'
            }

        elif price_trend == 'rising' and volume_trend == 'rising' and oi_trend == 'falling':
            return {
                'bias': '⚠️ Cautious',
                'behavior': 'Rising prices but positions being closed. Shorts exiting faster than longs entering. Often near top.',
                'pattern': 'potential_reversal'
            }

        elif price_trend == 'falling' and volume_trend == 'rising' and oi_trend == 'falling':
            return {
                'bias': '🟢 Potential Reversal',
                'behavior': 'Price down on high volume but declining OI. Panic liquidation without new shorts. Exhaustive move.',
                'pattern': 'reversal_setup'
            }

        elif price_trend == 'rising' and volume_trend == 'falling' and oi_trend == 'rising':
            return {
                'bias': '🔴 Weak Bullish / Bearish Warning',
                'behavior': 'Rising OI but falling volume. Complacent rally, risk of trap if new longs stall.',
                'pattern': 'potential_reversal'
            }

        else:
            # Default/mixed signals
            return {
                'bias': '⚪ Neutral',
                'behavior': 'Mixed signals. No clear directional conviction.',
                'pattern': 'wait'
            }

    def _generate_narrative(
        self,
        price_trend: str,
        volume_trend: str,
        murphy_signal,
        interpretation: Dict
    ) -> str:
        """Generate human-readable narrative"""
        lines = []

        # Opening statement
        lines.append(f"{interpretation['bias']} - {interpretation['behavior']}")
        lines.append("")

        # Technical details
        lines.append("📊 Technical Breakdown:")
        lines.append(f"  • Price: {price_trend.upper()}")
        lines.append(f"  • Volume: {volume_trend.upper()} (RVOL: {murphy_signal.rvol:.2f}x)")
        lines.append(f"  • Efficiency: {murphy_signal.volume_efficiency * 1000:.3f} (price move per volume)")
        lines.append(f"  • Body Ratio: {murphy_signal.body_ratio:.2f} (directional conviction)")
        lines.append(f"  • Volatility: {murphy_signal.atr_ratio:.2f}x average")
        lines.append("")

        # Pattern classification
        pattern = interpretation['pattern']
        if pattern == 'continuation':
            lines.append("🎯 Pattern: CONTINUATION - Trend likely to persist")
        elif pattern == 'reversal_setup':
            lines.append("🔄 Pattern: REVERSAL SETUP - Watch for change in direction")
        elif pattern == 'potential_reversal':
            lines.append("⚠️ Pattern: POTENTIAL REVERSAL - Caution, trend may be exhausting")
        elif pattern == 'temporary':
            lines.append("⏱️ Pattern: TEMPORARY MOVE - Likely to fade")
        else:
            lines.append("⏸️ Pattern: WAIT - No clear setup")

        lines.append("")

        # Murphy's grade
        grade_desc = "Excellent" if murphy_signal.grade >= 8 else \
                     "Strong" if murphy_signal.grade >= 6 else \
                     "Moderate" if murphy_signal.grade >= 4 else "Weak"

        lines.append(f"🎯 Murphy's Grade: {murphy_signal.grade}/10 ({grade_desc})")
        lines.append(f"   Label: {self.murphy.format_label(murphy_signal)}")

        return "\n".join(lines)

    def _get_recommendation(
        self,
        bias: str,
        grade: int,
        stars: int
    ) -> str:
        """
        Get actionable recommendation.

        Returns: 'buy_continuation', 'sell_continuation',
                 'reversal_long', 'reversal_short', 'wait'
        """
        if '🟢 Bullish' in bias and grade >= 7 and stars >= 3:
            return 'buy_continuation'
        elif '🔴 Bearish' in bias and grade >= 7 and stars >= 3:
            return 'sell_continuation'
        elif 'Reversal' in bias and grade >= 6:
            if 'Bullish' in bias or '🟢' in bias:
                return 'reversal_long'
            else:
                return 'reversal_short'
        elif 'Cautious' in bias or 'Weak' in bias:
            return 'wait'
        else:
            return 'wait'


# API endpoint for other systems to use
def get_murphy_analysis(bars: List[Bar], lookback: int = 50) -> Dict:
    """
    Standalone function to get Murphy's market analysis.
    Can be called by any strategy or indicator.

    Usage:
        from murphy_analysis_endpoint import get_murphy_analysis

        analysis = get_murphy_analysis(bars)
        print(analysis['narrative'])

        if analysis['recommendation'] == 'buy_continuation':
            # Execute long entry
            pass
    """
    analyzer = MurphyAnalyzer()
    return analyzer.analyze_current_market(bars, lookback)


if __name__ == "__main__":
    # Test with sample data
    test_bars = [
        Bar(f"2025-01-01T09:{i:02d}", 100 + i*0.1, 100 + i*0.15, 100 + i*0.05, 100 + i*0.12, 1000 + i*100, i)
        for i in range(50)
    ]

    analysis = get_murphy_analysis(test_bars)
    print(analysis['narrative'])
    print(f"\nRecommendation: {analysis['recommendation']}")
