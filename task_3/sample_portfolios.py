"""
sample_portfolios.py
--------------------
Multiple example portfolios — the script is NOT hardcoded to a single one.
Pass --portfolio NAME on the CLI to pick one, or load your own from JSON.
"""

from __future__ import annotations

# ── Sample portfolios (keys are CLI-friendly names) ──────────────────────────

SAMPLE_PORTFOLIOS: dict[str, dict] = {

    # The exact portfolio from the task brief
    "default": {
        "total_value_inr":      10_000_000,   # ₹1 Crore
        "monthly_expenses_inr":     80_000,
        "assets": [
            {"name": "BTC",     "allocation_pct": 30, "expected_crash_pct": -80},
            {"name": "NIFTY50", "allocation_pct": 40, "expected_crash_pct": -40},
            {"name": "GOLD",    "allocation_pct": 20, "expected_crash_pct": -15},
            {"name": "CASH",    "allocation_pct": 10, "expected_crash_pct":   0},
        ],
    },

    # Conservative retiree — heavy cash, low equity
    "conservative": {
        "total_value_inr":     5_000_000,
        "monthly_expenses_inr":   40_000,
        "assets": [
            {"name": "CASH",     "allocation_pct": 50, "expected_crash_pct":   0},
            {"name": "BONDS",    "allocation_pct": 30, "expected_crash_pct": -10},
            {"name": "NIFTY50",  "allocation_pct": 15, "expected_crash_pct": -40},
            {"name": "GOLD",     "allocation_pct":  5, "expected_crash_pct": -15},
        ],
    },

    # Aggressive young trader — crypto-heavy, high concentration
    "aggressive": {
        "total_value_inr":     2_000_000,
        "monthly_expenses_inr":   60_000,
        "assets": [
            {"name": "BTC",     "allocation_pct": 50, "expected_crash_pct": -80},
            {"name": "ETH",     "allocation_pct": 30, "expected_crash_pct": -75},
            {"name": "NIFTY50", "allocation_pct": 15, "expected_crash_pct": -40},
            {"name": "CASH",    "allocation_pct":  5, "expected_crash_pct":   0},
        ],
    },

    # FAIL ruin test — high expenses + concentrated risk
    "fragile": {
        "total_value_inr":     1_500_000,
        "monthly_expenses_inr":  100_000,
        "assets": [
            {"name": "DOGECOIN", "allocation_pct": 80, "expected_crash_pct": -90},
            {"name": "NIFTY50",  "allocation_pct": 15, "expected_crash_pct": -40},
            {"name": "CASH",     "allocation_pct":  5, "expected_crash_pct":   0},
        ],
    },
}


def get_portfolio(name: str) -> dict:
    """Look up a sample portfolio by name."""
    if name not in SAMPLE_PORTFOLIOS:
        raise KeyError(
            f"Unknown portfolio '{name}'. Available: {list(SAMPLE_PORTFOLIOS)}"
        )
    return SAMPLE_PORTFOLIOS[name]
