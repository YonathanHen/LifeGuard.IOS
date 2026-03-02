"""SignalFlow — Data Fetchers."""
from .yahoo_finance import fetch_yahoo
from .cross_asset import fetch_cross_asset
from .fred_fetcher import fetch_credit_spread, fetch_fred, fetch_yield_curve, fetch_macro_data

__all__ = [
    "fetch_yahoo", "fetch_cross_asset", "fetch_credit_spread", "fetch_fred",
    "fetch_yield_curve", "fetch_macro_data",
]
