"""
test_fetcher.py
---------------
Unit tests for the asset price fetcher.
Uses unittest.mock to patch network calls — no internet required.

Run:  python -m pytest test_fetcher.py -v
  or: python test_fetcher.py
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone, timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

from fetchers import AssetPrice, FetchError, fetch_coingecko, fetch_yfinance
from assets   import fetch_all, AssetConfig
from display  import render_table

IST = timezone(timedelta(hours=5, minutes=30))
_NOW = datetime(2025, 6, 1, 10, 32, 15, tzinfo=IST)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_price(**kwargs) -> AssetPrice:
    defaults = dict(
        name="TestAsset", symbol="TST", price=100.0,
        currency="USD", fetched_at=_NOW, source="Mock",
    )
    return AssetPrice(**{**defaults, **kwargs})


# ── CoinGecko fetcher tests ───────────────────────────────────────────────────

class TestFetchCoingecko(unittest.TestCase):

    def _mock_response(self, json_data: dict, status: int = 200) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = json_data
        resp.raise_for_status = MagicMock(
            side_effect=None if status == 200
            else __import__("requests").exceptions.HTTPError(f"{status}")
        )
        return resp

    @patch("fetchers.requests.get")
    def test_successful_fetch(self, mock_get):
        mock_get.return_value = self._mock_response({
            "bitcoin": {"usd": 67_500.0, "last_updated_at": 1748765535}
        })
        result = fetch_coingecko("Bitcoin", "bitcoin", "usd")
        self.assertEqual(result.name, "Bitcoin")
        self.assertAlmostEqual(result.price, 67_500.0)
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.source, "CoinGecko")

    @patch("fetchers.requests.get")
    def test_unknown_coin_raises(self, mock_get):
        mock_get.return_value = self._mock_response({})   # coin ID absent
        with self.assertRaises(FetchError) as ctx:
            fetch_coingecko("Ghost", "ghost-coin", "usd")
        self.assertIn("not found", ctx.exception.reason)

    @patch("fetchers.requests.get")
    def test_unknown_currency_raises(self, mock_get):
        mock_get.return_value = self._mock_response({"bitcoin": {}})
        with self.assertRaises(FetchError) as ctx:
            fetch_coingecko("Bitcoin", "bitcoin", "xyz")
        self.assertIn("not available", ctx.exception.reason)

    @patch("fetchers.requests.get")
    def test_timeout_raises_fetch_error(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.Timeout()
        with self.assertRaises(FetchError) as ctx:
            fetch_coingecko("Bitcoin", "bitcoin", "usd")
        self.assertIn("timed out", ctx.exception.reason)

    @patch("fetchers.requests.get")
    def test_connection_error_raises_fetch_error(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError()
        with self.assertRaises(FetchError) as ctx:
            fetch_coingecko("Bitcoin", "bitcoin", "usd")
        self.assertIn("connection failed", ctx.exception.reason)


# ── yfinance fetcher tests ────────────────────────────────────────────────────

class TestFetchYfinance(unittest.TestCase):

    @patch("fetchers.yf")
    def test_successful_fetch(self, mock_yf):
        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = 1_482.30
        mock_yf.Ticker.return_value = mock_ticker

        result = fetch_yfinance("Infosys", "INFY.NS", "INR")
        self.assertEqual(result.name, "Infosys")
        self.assertAlmostEqual(result.price, 1_482.30)
        self.assertEqual(result.currency, "INR")

    @patch("fetchers.yf")
    def test_null_price_raises(self, mock_yf):
        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = None
        mock_yf.Ticker.return_value = mock_ticker

        with self.assertRaises(FetchError) as ctx:
            fetch_yfinance("Infosys", "INFY.NS", "INR")
        self.assertIn("null", ctx.exception.reason)

    @patch("fetchers.yf")
    def test_exception_wrapped_as_fetch_error(self, mock_yf):
        mock_yf.Ticker.side_effect = RuntimeError("network blip")
        with self.assertRaises(FetchError) as ctx:
            fetch_yfinance("Infosys", "INFY.NS", "INR")
        self.assertIn("network blip", ctx.exception.reason)


# ── fetch_all dispatcher tests ────────────────────────────────────────────────

class TestFetchAll(unittest.TestCase):

    def test_all_succeed(self):
        p = _make_price()
        assets = [
            AssetConfig("A", lambda: p),
            AssetConfig("B", lambda: _make_price(name="B")),
        ]
        successes, failures = fetch_all(assets)
        self.assertEqual(len(successes), 2)
        self.assertEqual(len(failures), 0)

    def test_one_fails_others_continue(self):
        def boom():
            raise FetchError("X", "Mock", "simulated failure")

        assets = [
            AssetConfig("Good", lambda: _make_price()),
            AssetConfig("Bad",  boom),
            AssetConfig("Good2", lambda: _make_price(name="C")),
        ]
        successes, failures = fetch_all(assets)
        self.assertEqual(len(successes), 2)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].symbol, "X")

    def test_all_fail_returns_empty_successes(self):
        def boom():
            raise FetchError("Y", "Mock", "all down")

        assets = [AssetConfig("X", boom), AssetConfig("Z", boom)]
        successes, failures = fetch_all(assets)
        self.assertEqual(successes, [])
        self.assertEqual(len(failures), 2)

    def test_unexpected_exception_does_not_crash(self):
        def explode():
            raise RuntimeError("totally unexpected")

        assets = [AssetConfig("Boom", explode)]
        successes, failures = fetch_all(assets)
        self.assertEqual(successes, [])
        self.assertEqual(len(failures), 1)


# ── Display / table rendering tests ──────────────────────────────────────────

class TestRenderTable(unittest.TestCase):

    def _capture(self, prices, errors) -> str:
        import sys
        old_stdout = sys.stdout
        sys.stdout = buf = StringIO()
        try:
            render_table(prices, errors)
        finally:
            sys.stdout = old_stdout
        return buf.getvalue()

    def test_renders_without_error(self):
        prices = [_make_price(name="BTC", price=67000, currency="USD")]
        output = self._capture(prices, [])
        self.assertIn("BTC", output)
        self.assertIn("67,000.00", output)
        self.assertIn("USD", output)

    def test_error_section_shown_when_failures_present(self):
        err = FetchError("ETH", "CoinGecko", "timeout")
        output = self._capture([], [err])
        self.assertIn("ETH", output)
        self.assertIn("timeout", output)

    def test_price_display_formatting(self):
        p = _make_price(price=1_234_567.89)
        self.assertEqual(p.price_display(), "1,234,567.89")

    def test_timestamp_display_ist(self):
        p = _make_price(fetched_at=_NOW)
        self.assertIn("IST", p.timestamp_display())
        self.assertIn("2025-06-01", p.timestamp_display())


# ── Run as plain script ───────────────────────────────────────────────────────
if __name__ == "__main__":
    unittest.main(verbosity=2)
