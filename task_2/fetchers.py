"""
fetchers.py
-----------
Data-source adapters for stocks/indices (yfinance) and crypto (CoinGecko).
Each fetcher returns an AssetPrice or raises a FetchError — callers decide
what to do with failures.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ── IST timezone ──────────────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))


# ── Domain types ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AssetPrice:
    name: str
    symbol: str
    price: float
    currency: str
    fetched_at: datetime
    source: str

    def price_display(self) -> str:
        return f"{self.price:,.2f}"

    def timestamp_display(self) -> str:
        return self.fetched_at.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S IST")


class FetchError(Exception):
    """Raised when a price cannot be retrieved from a data source."""
    def __init__(self, symbol: str, source: str, reason: str):
        self.symbol = symbol
        self.source = source
        self.reason = reason
        super().__init__(f"[{source}] {symbol}: {reason}")


# ── yfinance adapter (stocks / indices) ──────────────────────────────────────

def fetch_yfinance(name: str, ticker: str, currency: str) -> AssetPrice:
    """
    Fetch the latest price for a stock or index via yfinance.

    Parameters
    ----------
    name     : Human-readable label shown in the table (e.g. "Reliance")
    ticker   : Yahoo Finance ticker symbol (e.g. "RELIANCE.NS")
    currency : Currency string to display (e.g. "INR")
    """
    if yf is None:
        raise FetchError(ticker, "yfinance", "yfinance not installed — run: pip install yfinance")

    try:
        t = yf.Ticker(ticker)
        info = t.fast_info

        price = info.last_price
        if price is None or price != price:          # None or NaN
            raise FetchError(ticker, "yfinance", "last_price returned null — market may be closed or ticker invalid")

        return AssetPrice(
            name=name,
            symbol=ticker,
            price=float(price),
            currency=currency,
            fetched_at=datetime.now(tz=IST),
            source="Yahoo Finance",
        )

    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(ticker, "yfinance", str(exc)) from exc


# ── CoinGecko adapter (crypto) ───────────────────────────────────────────────

_COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_COINGECKO_TIMEOUT = 10   # seconds


def fetch_coingecko(name: str, coin_id: str, vs_currency: str = "usd") -> AssetPrice:
    """
    Fetch the latest crypto price from the CoinGecko public API (no key needed).

    Parameters
    ----------
    name        : Human-readable label (e.g. "Bitcoin")
    coin_id     : CoinGecko coin ID (e.g. "bitcoin", "ethereum", "solana")
    vs_currency : Target currency code (e.g. "usd", "inr")
    """
    url = f"{_COINGECKO_BASE}/simple/price"
    params = {
        "ids": coin_id,
        "vs_currencies": vs_currency,
        "include_last_updated_at": "true",
    }

    try:
        response = requests.get(url, params=params, timeout=_COINGECKO_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise FetchError(coin_id, "CoinGecko", "request timed out") from exc
    except requests.exceptions.HTTPError as exc:
        raise FetchError(coin_id, "CoinGecko", f"HTTP {response.status_code}") from exc
    except requests.exceptions.ConnectionError as exc:
        raise FetchError(coin_id, "CoinGecko", "connection failed — check internet") from exc

    data = response.json()

    if coin_id not in data:
        raise FetchError(coin_id, "CoinGecko", f"coin ID '{coin_id}' not found in response")

    coin_data = data[coin_id]

    if vs_currency not in coin_data:
        raise FetchError(coin_id, "CoinGecko", f"currency '{vs_currency}' not available for this coin")

    price = coin_data[vs_currency]
    last_updated = coin_data.get("last_updated_at")
    fetched_at = (
        datetime.fromtimestamp(last_updated, tz=IST)
        if last_updated
        else datetime.now(tz=IST)
    )

    return AssetPrice(
        name=name,
        symbol=coin_id.upper(),
        price=float(price),
        currency=vs_currency.upper(),
        fetched_at=fetched_at,
        source="CoinGecko",
    )
