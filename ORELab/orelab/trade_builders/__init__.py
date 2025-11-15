"""
Trade builders for generating ORE XML from trade data.
"""

from .base import BaseTradeBuilder
from .fx_forward import FxForwardBuilder
from .fx_option import FxOptionBuilder
from .swap import InterestRateSwapBuilder
from .cross_currency_swap import CrossCurrencySwapBuilder

__all__ = [
    "BaseTradeBuilder",
    "FxForwardBuilder",
    "FxOptionBuilder",
    "InterestRateSwapBuilder",
    "CrossCurrencySwapBuilder",
]

TradeBuilders = {
    "FxForward": FxForwardBuilder,
    "FxOption": FxOptionBuilder,
    "CrossCurrencySwap": CrossCurrencySwapBuilder,
    "InterestRateSwap": InterestRateSwapBuilder,
}
