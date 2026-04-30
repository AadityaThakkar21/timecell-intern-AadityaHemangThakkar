"""
assets.py
---------
Catalogue of assets to fetch, plus the fetch-dispatch logic.
Add or swap assets here — nothing else needs changing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from fetchers import AssetPrice, FetchError, fetch_coingecko, fetch_yfinance

logger = logging.getLogger(__name__)


# ── Asset descriptor ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AssetConfig:
    """Everything needed to fetch and label one asset."""
    display_name: str
    fetch: Callable[[], AssetPrice]   # zero-arg callable, returns AssetPrice


# ── Asset catalogue ──────────────────────────────────────────────────────────
#
# Exactly 3 assets as required:
#   • Tata Steel   — NSE-listed steel giant, part of the Tata Group
#   • HDFC Bank    — India's largest private-sector bank by market cap
#   • Dogecoin     — crypto asset; originally a meme coin, now widely traded
#
# All tickers verified against Yahoo Finance and CoinGecko as of 2025.
# ─────────────────────────────────────────────────────────────────────────────

ASSETS: list[AssetConfig] = [
    # ── NSE-listed stocks ─────────────────────────────────────────────────────
    AssetConfig(
        display_name="Tata Steel",
        fetch=lambda: fetch_yfinance("Tata Steel", "TATASTEEL.NS", "INR"),
    ),
    AssetConfig(
        display_name="HDFC Bank",
        fetch=lambda: fetch_yfinance("HDFC Bank", "HDFCBANK.NS", "INR"),
    ),
    # ── Crypto ────────────────────────────────────────────────────────────────
    AssetConfig(
        display_name="Dogecoin",
        fetch=lambda: fetch_coingecko("Dogecoin", "dogecoin", "usd"),
    ),
]


# ── Fetch dispatcher ─────────────────────────────────────────────────────────

def fetch_all(
    assets: list[AssetConfig] | None = None,
) -> tuple[list[AssetPrice], list[FetchError]]:
    """
    Fetch prices for all assets.  Never raises — errors are collected and
    returned alongside successful results so the table always renders.

    Returns
    -------
    (successes, failures)
        successes : list[AssetPrice]  — one entry per successful fetch
        failures  : list[FetchError]  — one entry per failed fetch
    """
    if assets is None:
        assets = ASSETS

    successes: list[AssetPrice] = []
    failures:  list[FetchError] = []

    for cfg in assets:
        try:
            price = cfg.fetch()
            successes.append(price)
            logger.debug("OK  %s -> %.4f %s", cfg.display_name, price.price, price.currency)
        except FetchError as exc:
            failures.append(exc)
            logger.error("FAIL %s | %s", exc.symbol, exc.reason)
        except Exception as exc:                         # unexpected — still don't crash
            err = FetchError(cfg.display_name, "unknown", str(exc))
            failures.append(err)
            logger.exception("Unexpected error fetching %s", cfg.display_name)

    return successes, failures
