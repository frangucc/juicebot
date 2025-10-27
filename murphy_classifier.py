#!/usr/bin/env python3
"""
Murphy's Classifier - Market Intent Inference Engine

Analyzes OHLCV data to estimate synthetic open interest (money flow direction)
and assign conviction levels to BoS/CHoCH signals.

Uses John Murphy's price-volume relationship principles to determine:
- Direction: ↑ (bullish) / ↓ (bearish) / − (neutral/choppy)
- Conviction: **** (1.5+), *** (1.2+), ** (0.8+), * (0.5+)
- Grade: 1-10 score based on multiple factors

Core Philosophy:
- High volume + efficient price move + expanding volatility = new money IN
- High volume + inefficient price move + compressing volatility = exhaustion
- Low volume + price move = covering/liquidation only (not sustainable)
"""

import statistics
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Bar:
    """Single OHLCV bar"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    index: int


@dataclass
class MurphySignal:
    """Murphy's classification output"""
    direction: str  # "↑", "↓", "−"
    stars: int  # 0-4
    grade: int  # 1-10
    confidence: float  # synthetic OI delta
    volume_efficiency: float
    rvol: float
    body_ratio: float
    atr_ratio: float
    interpretation: str  # Human-readable explanation


class MurphyClassifier:
    """
    Market intent classifier using OHLCV to estimate money flow.

    Thresholds (configurable):
    - **** : synthetic_oi_delta > 1.5 (extreme conviction)
    - ***  : synthetic_oi_delta > 1.2 (strong)
    - **   : synthetic_oi_delta > 0.8 (moderate)
    - *    : synthetic_oi_delta > 0.5 (weak)
    - −    : -0.3 to +0.3 (neutral/choppy)
    """

    def __init__(
        self,
        threshold_4_star: float = 1.5,
        threshold_3_star: float = 1.2,
        threshold_2_star: float = 0.8,
        threshold_1_star: float = 0.5,
        neutral_threshold: float = 0.3
    ):
        self.threshold_4_star = threshold_4_star
        self.threshold_3_star = threshold_3_star
        self.threshold_2_star = threshold_2_star
        self.threshold_1_star = threshold_1_star
        self.neutral_threshold = neutral_threshold

    def calculate_rvol(self, bars: List[Bar], current_index: int, lookback: int = 20) -> float:
        """
        Relative Volume: current volume vs. average volume
        > 1.5 = abnormal participation
        < 0.5 = low conviction
        """
        if current_index < lookback:
            lookback = current_index

        if lookback < 1:
            return 1.0

        recent_bars = bars[max(0, current_index - lookback):current_index]
        if not recent_bars:
            return 1.0

        avg_volume = statistics.mean([b.volume for b in recent_bars])
        current_volume = bars[current_index].volume

        if avg_volume == 0:
            return 1.0

        return current_volume / avg_volume

    def calculate_volume_efficiency(self, bar: Bar) -> float:
        """
        Volume Efficiency: How much price moved per unit of volume
        High = directional conviction (efficient move)
        Low = churn/distribution (inefficient)
        """
        if bar.volume == 0:
            return 0.0

        price_change = abs(bar.close - bar.open)
        return price_change / bar.volume

    def calculate_body_ratio(self, bar: Bar) -> float:
        """
        Body Ratio: Size of candle body vs. total range
        > 0.7 = strong directional
        < 0.3 = indecision/reversal potential
        """
        total_range = bar.high - bar.low
        if total_range == 0:
            return 0.0

        body_size = abs(bar.close - bar.open)
        return body_size / total_range

    def calculate_atr_ratio(self, bars: List[Bar], current_index: int, atr_period: int = 14) -> float:
        """
        ATR Ratio: Current ATR vs. average ATR
        > 1.2 = expanding volatility (trend strength)
        < 0.8 = compressing volatility (consolidation)
        """
        if current_index < atr_period * 2:
            return 1.0

        # Calculate recent ATR
        recent_bars = bars[max(0, current_index - atr_period):current_index + 1]
        recent_true_ranges = []
        for i in range(1, len(recent_bars)):
            tr = max(
                recent_bars[i].high - recent_bars[i].low,
                abs(recent_bars[i].high - recent_bars[i-1].close),
                abs(recent_bars[i].low - recent_bars[i-1].close)
            )
            recent_true_ranges.append(tr)

        if not recent_true_ranges:
            return 1.0

        current_atr = statistics.mean(recent_true_ranges)

        # Calculate historical ATR
        historical_bars = bars[max(0, current_index - atr_period * 2):max(0, current_index - atr_period)]
        historical_true_ranges = []
        for i in range(1, len(historical_bars)):
            tr = max(
                historical_bars[i].high - historical_bars[i].low,
                abs(historical_bars[i].high - historical_bars[i-1].close),
                abs(historical_bars[i].low - historical_bars[i-1].close)
            )
            historical_true_ranges.append(tr)

        if not historical_true_ranges:
            return 1.0

        avg_atr = statistics.mean(historical_true_ranges)

        if avg_atr == 0:
            return 1.0

        return current_atr / avg_atr

    def calculate_delta_momentum(self, bars: List[Bar], current_index: int, lookback: int) -> float:
        """
        Delta Momentum: Price efficiency over N bars weighted by volume
        Positive + high volume = persistent buying
        Negative + high volume = persistent selling
        """
        if current_index < lookback:
            lookback = current_index

        if lookback < 1:
            return 0.0

        start_index = max(0, current_index - lookback)
        price_change = bars[current_index].close - bars[start_index].close

        total_volume = sum(b.volume for b in bars[start_index:current_index + 1])

        if total_volume == 0:
            return 0.0

        # Normalize by volume (directional efficiency)
        return price_change / (total_volume / lookback)

    def calculate_synthetic_oi(
        self,
        bars: List[Bar],
        current_index: int,
        adaptive_lookback: int
    ) -> Tuple[float, Dict[str, float]]:
        """
        Synthetic Open Interest Delta - estimates money flow direction

        Returns:
            (synthetic_oi_delta, components_dict)
        """
        bar = bars[current_index]

        # Component calculations
        rvol = self.calculate_rvol(bars, current_index, adaptive_lookback)
        vol_efficiency = self.calculate_volume_efficiency(bar)
        body_ratio = self.calculate_body_ratio(bar)
        delta_momentum = self.calculate_delta_momentum(bars, current_index, adaptive_lookback)
        atr_ratio = self.calculate_atr_ratio(bars, current_index)

        # Weighted combination (John Murphy principles)
        # High RVOL + efficient move + directional body + momentum = new money
        synthetic_oi = (
            rvol * 0.3 +                    # Participation weight
            vol_efficiency * 1000 * 0.25 +  # Efficiency weight (scaled)
            body_ratio * 0.2 +              # Conviction weight
            delta_momentum * 100 * 0.15 +   # Persistence weight (scaled)
            atr_ratio * 0.1                 # Volatility regime weight
        )

        # Apply directional bias
        is_bullish = bar.close > bar.open
        directional_oi = synthetic_oi if is_bullish else -synthetic_oi

        components = {
            'rvol': rvol,
            'volume_efficiency': vol_efficiency,
            'body_ratio': body_ratio,
            'delta_momentum': delta_momentum,
            'atr_ratio': atr_ratio,
            'raw_oi': synthetic_oi,
            'directional_oi': directional_oi
        }

        return directional_oi, components

    def assign_stars(self, synthetic_oi_delta: float) -> int:
        """Assign star rating based on conviction level"""
        abs_oi = abs(synthetic_oi_delta)

        if abs_oi >= self.threshold_4_star:
            return 4
        elif abs_oi >= self.threshold_3_star:
            return 3
        elif abs_oi >= self.threshold_2_star:
            return 2
        elif abs_oi >= self.threshold_1_star:
            return 1
        else:
            return 0

    def calculate_grade(self, components: Dict[str, float], synthetic_oi_delta: float) -> int:
        """
        Calculate 1-10 grade based on multiple factors
        10 = perfect alignment (high RVOL, efficient, directional, expanding vol)
        1 = weak/conflicting signals
        """
        score = 5.0  # Start at middle

        # RVOL contribution (0-2 points)
        if components['rvol'] > 1.5:
            score += 2.0
        elif components['rvol'] > 1.2:
            score += 1.5
        elif components['rvol'] > 1.0:
            score += 1.0
        elif components['rvol'] < 0.5:
            score -= 1.0

        # Volume efficiency (0-2 points)
        vol_eff_scaled = components['volume_efficiency'] * 1000
        if vol_eff_scaled > 0.5:
            score += 2.0
        elif vol_eff_scaled > 0.3:
            score += 1.0

        # Body ratio (0-2 points)
        if components['body_ratio'] > 0.7:
            score += 2.0
        elif components['body_ratio'] > 0.5:
            score += 1.0
        elif components['body_ratio'] < 0.3:
            score -= 1.0

        # ATR expansion (0-1 points)
        if components['atr_ratio'] > 1.2:
            score += 1.0
        elif components['atr_ratio'] < 0.8:
            score -= 0.5

        # Delta momentum alignment (0-1 points)
        delta_mom_scaled = components['delta_momentum'] * 100
        if abs(delta_mom_scaled) > 0.5:
            score += 1.0

        # Overall conviction (0-2 points)
        if abs(synthetic_oi_delta) > 1.5:
            score += 2.0
        elif abs(synthetic_oi_delta) > 1.0:
            score += 1.0

        # Clamp to 1-10
        return max(1, min(10, int(round(score))))

    def generate_interpretation(
        self,
        direction: str,
        stars: int,
        grade: int,
        components: Dict[str, float]
    ) -> str:
        """Generate human-readable interpretation"""
        if direction == "−":
            return "Choppy/Neutral - No clear conviction"

        # Conviction level
        if stars == 4:
            conviction = "Extreme conviction"
        elif stars == 3:
            conviction = "Strong conviction"
        elif stars == 2:
            conviction = "Moderate conviction"
        elif stars == 1:
            conviction = "Weak conviction"
        else:
            conviction = "Minimal conviction"

        # Money flow interpretation
        rvol = components['rvol']
        body = components['body_ratio']
        atr = components['atr_ratio']

        if direction == "↑":
            base = f"{conviction} bullish"
            if rvol > 1.5 and body > 0.7 and atr > 1.2:
                flow = "- New bulls aggressively entering, expanding trend"
            elif rvol < 0.7 or body < 0.4:
                flow = "- Likely short covering, not sustained buying"
            else:
                flow = "- Buyers in control, moderate participation"
        else:  # ↓
            base = f"{conviction} bearish"
            if rvol > 1.5 and body > 0.7 and atr > 1.2:
                flow = "- New bears aggressively entering, expanding downtrend"
            elif rvol < 0.7 or body < 0.4:
                flow = "- Likely long liquidation, exhaustion possible"
            else:
                flow = "- Sellers in control, moderate participation"

        return f"{base} {flow}"

    def classify(
        self,
        bars: List[Bar],
        signal_index: int,
        structure_age_bars: int
    ) -> MurphySignal:
        """
        Main classification method

        Args:
            bars: All historical bars
            signal_index: Index where BoS/CHoCH occurred
            structure_age_bars: How many bars ago the swing point formed
                               (used for adaptive lookback)

        Returns:
            MurphySignal with direction, stars, grade, and interpretation
        """
        # Adaptive lookback: minimum 2x structure age, capped at available bars
        adaptive_lookback = min(
            max(structure_age_bars * 2, 20),  # At least 2x structure or 20
            signal_index  # Can't look back more than available
        )

        # Calculate synthetic OI
        synthetic_oi_delta, components = self.calculate_synthetic_oi(
            bars, signal_index, adaptive_lookback
        )

        # Determine direction
        if abs(synthetic_oi_delta) < self.neutral_threshold:
            direction = "−"
        elif synthetic_oi_delta > 0:
            direction = "↑"
        else:
            direction = "↓"

        # Assign stars
        stars = self.assign_stars(synthetic_oi_delta)

        # Calculate grade
        grade = self.calculate_grade(components, synthetic_oi_delta)

        # Generate interpretation
        interpretation = self.generate_interpretation(direction, stars, grade, components)

        return MurphySignal(
            direction=direction,
            stars=stars,
            grade=grade,
            confidence=synthetic_oi_delta,
            volume_efficiency=components['volume_efficiency'],
            rvol=components['rvol'],
            body_ratio=components['body_ratio'],
            atr_ratio=components['atr_ratio'],
            interpretation=interpretation
        )

    def format_label(self, signal: MurphySignal) -> str:
        """Format signal for chart display: ↑ **** [8]"""
        star_str = "*" * signal.stars if signal.stars > 0 else ""
        return f"{signal.direction} {star_str} [{signal.grade}]".strip()


if __name__ == "__main__":
    # Quick test
    test_bars = [
        Bar("2025-01-01T09:00", 100, 102, 99, 101, 1000, 0),
        Bar("2025-01-01T09:01", 101, 105, 100, 104, 2500, 1),  # Strong bullish
        Bar("2025-01-01T09:02", 104, 106, 103, 105, 3000, 2),  # Continuation
    ]

    murphy = MurphyClassifier()
    signal = murphy.classify(test_bars, signal_index=2, structure_age_bars=10)

    print("Murphy's Classifier Test:")
    print(f"Label: {murphy.format_label(signal)}")
    print(f"Interpretation: {signal.interpretation}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"RVOL: {signal.rvol:.2f}")
