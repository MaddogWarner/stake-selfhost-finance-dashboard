"""Ticker/exchange normalisation shared by the Stake sync and manual entry paths.

Tickers are stored in bare form (no exchange suffix); the exchange is stored
separately as ``ASX`` or ``NYSE``. This is the storage form — yfinance appends
``.AX`` for ASX tickers at call time, so do not reuse yfinance's own helper here.
"""


def normalise_exchange(value: str | None) -> str:
    raw = (value or "").upper()
    if raw in {"ASX", "AU", "AUS"}:
        return "ASX"
    return "NYSE"


def normalise_ticker(value: str, exchange: str) -> str:
    ticker = value.upper().strip()
    if exchange == "ASX":
        ticker = ticker.removesuffix(".AX")
    return ticker
