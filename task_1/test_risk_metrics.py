"""
test_risk_metrics.py
--------------------
Unit tests for compute_risk_metrics().
Run:  python -m pytest test_risk_metrics.py -v
  or: python test_risk_metrics.py
"""

from __future__ import annotations
import unittest
from risk_metrics import compute_risk_metrics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE = {
    "total_value_inr":      10_000_000,
    "monthly_expenses_inr":     80_000,
    "assets": [
        {"name": "BTC",     "allocation_pct": 30, "expected_crash_pct": -80},
        {"name": "NIFTY50", "allocation_pct": 40, "expected_crash_pct": -40},
        {"name": "GOLD",    "allocation_pct": 20, "expected_crash_pct": -15},
        {"name": "CASH",    "allocation_pct": 10, "expected_crash_pct":   0},
    ],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestComputeRiskMetrics(unittest.TestCase):

    # ── Full crash scenario ──────────────────────────────────────────────────

    def test_post_crash_value_full(self):
        """
        Manual calculation:
          BTC   : 30 % of 10 M =  3 000 000  × (1 - 0.80) =   600 000
          NIFTY : 40 % of 10 M =  4 000 000  × (1 - 0.40) = 2 400 000
          GOLD  : 20 % of 10 M =  2 000 000  × (1 - 0.15) = 1 700 000
          CASH  : 10 % of 10 M =  1 000 000  × (1 - 0.00) = 1 000 000
          Total = 5 700 000
        """
        m = compute_risk_metrics(SAMPLE)
        self.assertAlmostEqual(m["post_crash_value"], 5_700_000, places=0)

    def test_runway_months_full(self):
        # 5 700 000 / 80 000 = 71.25
        m = compute_risk_metrics(SAMPLE)
        self.assertAlmostEqual(m["runway_months"], 71.25, places=2)

    def test_ruin_test_pass(self):
        m = compute_risk_metrics(SAMPLE)
        self.assertEqual(m["ruin_test"], "PASS")

    def test_ruin_test_fail(self):
        tiny = {
            "total_value_inr": 1_000_000,
            "monthly_expenses_inr": 200_000,
            "assets": [
                {"name": "CRYPTO", "allocation_pct": 100, "expected_crash_pct": -99},
            ],
        }
        m = compute_risk_metrics(tiny)
        self.assertEqual(m["ruin_test"], "FAIL")

    def test_largest_risk_asset(self):
        # BTC : 30 × 80 = 2400, NIFTY : 40 × 40 = 1600 → BTC wins
        m = compute_risk_metrics(SAMPLE)
        self.assertEqual(m["largest_risk_asset"], "BTC")

    def test_concentration_warning_true(self):
        # NIFTY50 is 40 % — NOT > 40, so no warning in sample
        m = compute_risk_metrics(SAMPLE)
        self.assertFalse(m["concentration_warning"])

    def test_concentration_warning_triggered(self):
        concentrated = {
            "total_value_inr": 1_000_000,
            "monthly_expenses_inr": 10_000,
            "assets": [
                {"name": "MEGA", "allocation_pct": 60, "expected_crash_pct": -50},
                {"name": "CASH", "allocation_pct": 40, "expected_crash_pct":   0},
            ],
        }
        m = compute_risk_metrics(concentrated)
        self.assertTrue(m["concentration_warning"])

    # ── Moderate crash scenario (50 % of expected loss) ─────────────────────

    def test_moderate_post_crash_value(self):
        """
        Moderate: each asset loses 50 % of its expected crash magnitude.
          BTC   :  3 000 000 × (1 - 0.40) = 1 800 000
          NIFTY :  4 000 000 × (1 - 0.20) = 3 200 000
          GOLD  :  2 000 000 × (1 - 0.075)= 1 850 000
          CASH  :  1 000 000 × 1.0        = 1 000 000
          Total = 7 850 000
        """
        m = compute_risk_metrics(SAMPLE)
        self.assertAlmostEqual(m["moderate_post_crash_value"], 7_850_000, places=0)

    def test_moderate_runway_months(self):
        # 7 850 000 / 80 000 = 98.125
        m = compute_risk_metrics(SAMPLE)
        self.assertAlmostEqual(m["moderate_runway_months"], 98.125, places=2)

    def test_moderate_ruin_test_pass(self):
        m = compute_risk_metrics(SAMPLE)
        self.assertEqual(m["moderate_ruin_test"], "PASS")

    # ── Edge cases ───────────────────────────────────────────────────────────

    def test_100_pct_cash(self):
        cash_portfolio = {
            "total_value_inr": 5_000_000,
            "monthly_expenses_inr": 50_000,
            "assets": [
                {"name": "CASH", "allocation_pct": 100, "expected_crash_pct": 0},
            ],
        }
        m = compute_risk_metrics(cash_portfolio)
        self.assertEqual(m["post_crash_value"], 5_000_000)
        self.assertEqual(m["ruin_test"], "PASS")
        # 100 % is strictly > 40 → concentration warning fires
        self.assertTrue(m["concentration_warning"])

    def test_zero_monthly_expenses(self):
        zero_exp = {
            "total_value_inr": 1_000_000,
            "monthly_expenses_inr": 0,
            "assets": [
                {"name": "BONDS", "allocation_pct": 100, "expected_crash_pct": -5},
            ],
        }
        m = compute_risk_metrics(zero_exp)
        self.assertEqual(m["runway_months"], float("inf"))
        self.assertEqual(m["ruin_test"], "PASS")

    def test_output_keys_present(self):
        m = compute_risk_metrics(SAMPLE)
        required_keys = {
            "post_crash_value", "runway_months", "ruin_test",
            "largest_risk_asset", "concentration_warning",
            "moderate_post_crash_value", "moderate_runway_months",
            "moderate_ruin_test",
        }
        self.assertTrue(required_keys.issubset(m.keys()))

    def test_invalid_total_value(self):
        bad = {**SAMPLE, "total_value_inr": -1}
        with self.assertRaises(ValueError):
            compute_risk_metrics(bad)


# ---------------------------------------------------------------------------
# Allow running as a plain script
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main(verbosity=2)
