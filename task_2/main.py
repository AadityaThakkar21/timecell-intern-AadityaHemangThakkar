"""
main.py
-------
Entry point for the Asset Price Fetcher.
Run:  python main.py
      python main.py --demo          # offline demo with mock prices
      python main.py --verbose       # show per-fetch debug logs
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone, timedelta

from assets  import fetch_all
from display import render_table
from fetchers import AssetPrice, FetchError

IST = timezone(timedelta(hours=5, minutes=30))


# ── Logging setup ─────────────────────────────────────────────────────────────

def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        format="%(levelname)-8s %(name)s: %(message)s",
        level=level,
        stream=sys.stderr,
    )


# ── Demo / mock mode (no network needed) ─────────────────────────────────────

def _mock_prices() -> tuple[list[AssetPrice], list[FetchError]]:
    """Return plausible-looking fake prices for offline demonstration."""
    now = datetime.now(tz=IST)
    prices = [
        AssetPrice("Tata Steel", "TATASTEEL.NS",   948.65, "INR", now, "Yahoo Finance (mock)"),
        AssetPrice("HDFC Bank",   "HDFCBANK.NS",    1_742.30, "INR", now, "Yahoo Finance (mock)"),
        AssetPrice("Dogecoin",    "DOGECOIN",           0.1623, "USD", now, "CoinGecko (mock)"),
    ]
    # Simulate one failed fetch to show error handling
    errors = [
        FetchError("DEMO_FAIL", "MockSource", "intentional demo failure — error handling works ✓"),
    ]
    return prices, errors


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch live asset prices and display a formatted table."
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Run in offline demo mode with mock prices (no network calls).",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show per-fetch debug logs on stderr.",
    )
    args = parser.parse_args()

    _configure_logging(args.verbose)

    if args.demo:
        print("\n  [DEMO MODE — using mock prices, no network calls]\n")
        prices, errors = _mock_prices()
    else:
        print("\n  Fetching prices…", end="", flush=True)
        prices, errors = fetch_all()
        print(" done.\n" if prices else " all fetches failed.\n")

    render_table(prices, errors)

    # Exit with non-zero code if every single fetch failed (useful in CI/scripts)
    if not prices:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
