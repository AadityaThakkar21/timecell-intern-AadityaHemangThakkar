"""
visualiser.py
-------------
Pure-stdlib CLI visualisation helpers.
No external plotting libraries required.
"""

from __future__ import annotations
from typing import Any

# ── Terminal width (fallback 80) ──────────────────────────────────────────────
import shutil
_TERM_WIDTH: int = min(shutil.get_terminal_size((80, 20)).columns, 100)

BAR_CHAR       = "█"
PARTIAL_CHARS  = ["▏", "▎", "▍", "▌", "▋", "▊", "▉"]  # sub-block precision


# ---------------------------------------------------------------------------
# Allocation bar chart
# ---------------------------------------------------------------------------

def _smooth_bar(fraction: float, bar_width: int) -> str:
    """Render a smooth Unicode progress bar."""
    filled_units = fraction * bar_width
    full_blocks  = int(filled_units)
    remainder    = filled_units - full_blocks

    bar = BAR_CHAR * full_blocks
    if full_blocks < bar_width:
        idx = int(remainder * len(PARTIAL_CHARS))
        bar += PARTIAL_CHARS[idx] if idx > 0 else " "
        bar += " " * (bar_width - full_blocks - 1)
    return bar


def print_allocation_chart(portfolio_dict: dict[str, Any]) -> None:
    """Print a horizontal bar chart of asset allocations to stdout."""
    assets = portfolio_dict.get("assets", [])
    if not assets:
        print("  (no assets to display)")
        return

    title = "  ASSET ALLOCATION BREAKDOWN"
    print()
    print("─" * _TERM_WIDTH)
    print(title)
    print("─" * _TERM_WIDTH)

    name_col_w  = max(len(a["name"]) for a in assets) + 2
    pct_col_w   = 7          # "100.0 %"
    bar_width   = _TERM_WIDTH - name_col_w - pct_col_w - 5

    for asset in assets:
        name  = asset["name"].ljust(name_col_w)
        pct   = float(asset["allocation_pct"])
        bar   = _smooth_bar(pct / 100.0, bar_width)
        label = f"{pct:5.1f}%"
        print(f"  {name} {bar} {label}")

    print("─" * _TERM_WIDTH)


# ---------------------------------------------------------------------------
# Side-by-side scenario table
# ---------------------------------------------------------------------------

def _fmt_inr(value: float) -> str:
    """Format a float as Indian Rupees with commas."""
    is_neg = value < 0
    abs_val = abs(value)
    s = f"{abs_val:,.2f}"
    return f"{'−' if is_neg else ''}₹{s}"


def _fmt_months(months: float) -> str:
    if months == float("inf"):
        return "∞"
    return f"{months:.1f}"


def print_scenario_comparison(metrics: dict[str, Any]) -> None:
    """Print full-crash vs moderate-crash results side by side."""
    col_w = 22

    labels = {
        "Post-Crash Value":  (
            _fmt_inr(metrics["post_crash_value"]),
            _fmt_inr(metrics["moderate_post_crash_value"]),
        ),
        "Runway (months)":   (
            _fmt_months(metrics["runway_months"]),
            _fmt_months(metrics["moderate_runway_months"]),
        ),
        "Ruin Test":         (
            metrics["ruin_test"],
            metrics["moderate_ruin_test"],
        ),
    }

    header_row   = f"  {'METRIC':<26} {'FULL CRASH':>{col_w}}   {'MODERATE CRASH (50%)':>{col_w}}"
    divider      = "─" * _TERM_WIDTH

    print()
    print(divider)
    print("  SCENARIO COMPARISON")
    print(divider)
    print(header_row)
    print(divider)
    for metric, (full_val, mod_val) in labels.items():
        print(f"  {metric:<26} {full_val:>{col_w}}   {mod_val:>{col_w}}")
    print(divider)


# ---------------------------------------------------------------------------
# Full risk summary report
# ---------------------------------------------------------------------------

def print_risk_report(portfolio_dict: dict[str, Any],
                      metrics: dict[str, Any]) -> None:
    """Print the complete risk report to stdout."""
    total = portfolio_dict["total_value_inr"]
    expenses = portfolio_dict["monthly_expenses_inr"]

    width = _TERM_WIDTH
    print()
    print("═" * width)
    print("  PORTFOLIO RISK CALCULATOR — FULL REPORT")
    print("═" * width)
    print(f"  Total Portfolio Value   : {_fmt_inr(total)}")
    print(f"  Monthly Expenses        : {_fmt_inr(expenses)}")

    # Allocation chart
    print_allocation_chart(portfolio_dict)

    # Key metrics
    print()
    print("─" * width)
    print("  KEY RISK METRICS")
    print("─" * width)
    print(f"  Largest Risk Asset      : {metrics['largest_risk_asset']}")
    warning_flag = "⚠  YES" if metrics["concentration_warning"] else "✓  NO"
    print(f"  Concentration Warning   : {warning_flag}")

    # Scenario table
    print_scenario_comparison(metrics)
    print()
