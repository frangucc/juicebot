"""
JuiceBot Tools Package

Tools are functions that the AI can call to interact with market data,
manage positions, and perform analysis.
"""

from .market_data import (
    get_current_price,
    get_volume_stats,
    get_price_range,
    get_historical_bars,
    detect_fvg,
    detect_bos,
    detect_choch,
    detect_pattern_confluence
)

__all__ = [
    "get_current_price",
    "get_volume_stats",
    "get_price_range",
    "get_historical_bars",
    "detect_fvg",
    "detect_bos",
    "detect_choch",
    "detect_pattern_confluence"
]
