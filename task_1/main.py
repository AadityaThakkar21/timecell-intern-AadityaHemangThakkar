from __future__ import annotations
import json
import sys

from risk_metrics import compute_risk_metrics
from visualiser  import print_risk_report


# ---------------------------------------------------------------------------
# Sample portfolio (from the task brief)
# ---------------------------------------------------------------------------

SAMPLE_PORTFOLIO: dict = {
    "total_value_inr":    10_000_000,   # 1 Crore INR
    "monthly_expenses_inr": 80_000,
    "assets": [
        {"name": "BTC",     "allocation_pct": 30, "expected_crash_pct": -80},
        {"name": "NIFTY50", "allocation_pct": 40, "expected_crash_pct": -40},
        {"name": "GOLD",    "allocation_pct": 20, "expected_crash_pct": -15},
        {"name": "CASH",    "allocation_pct": 10, "expected_crash_pct":   0},
    ],
}


# ---------------------------------------------------------------------------
# Edge-case portfolios for demonstration
# ---------------------------------------------------------------------------

EDGE_CASES: list[tuple[str, dict]] = [
    (
        "100 % Cash Portfolio",
        {
            "total_value_inr": 5_000_000,
            "monthly_expenses_inr": 50_000,
            "assets": [
                {"name": "CASH", "allocation_pct": 100, "expected_crash_pct": 0},
            ],
        },
    ),
    (
        "Single Concentrated Asset (> 40 %)",
        {
            "total_value_inr": 2_000_000,
            "monthly_expenses_inr": 200_000,
            "assets": [
                {"name": "CRYPTO", "allocation_pct": 90, "expected_crash_pct": -70},
                {"name": "CASH",   "allocation_pct": 10, "expected_crash_pct":   0},
            ],
        },
    ),
    (
        "Zero Monthly Expenses (Infinite Runway)",
        {
            "total_value_inr": 1_000_000,
            "monthly_expenses_inr": 0,
            "assets": [
                {"name": "BONDS", "allocation_pct": 60, "expected_crash_pct": -5},
                {"name": "CASH",  "allocation_pct": 40, "expected_crash_pct":  0},
            ],
        },
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _separator(char: str = "═", width: int = 70) -> None:
    print(char * width)


def run_portfolio(label: str, portfolio: dict) -> None:
    """Compute metrics and print the full report for one portfolio."""
    _separator()
    print(f"  PORTFOLIO: {label}")
    _separator()
    metrics = compute_risk_metrics(portfolio)
    print_risk_report(portfolio, metrics)
    print("  Raw metrics (JSON):")
    print(json.dumps(metrics, indent=4, default=str))
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Primary sample portfolio
    run_portfolio("Sample (from task brief)", SAMPLE_PORTFOLIO)

    # Edge cases
    for label, portfolio in EDGE_CASES:
        run_portfolio(label, portfolio)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:                        # noqa: BLE001
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
