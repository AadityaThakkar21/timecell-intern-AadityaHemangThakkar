"""
risk_metrics.py
---------------
Core computation engine for portfolio risk analysis.
Supports full crash and moderate crash scenarios.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Asset:
    name: str
    allocation_pct: float          # 0-100
    expected_crash_pct: float      # negative = loss, 0 = stable

    @property
    def allocation_fraction(self) -> float:
        return self.allocation_pct / 100.0

    def crash_value_fraction(self, magnitude: float = 1.0) -> float:
        """
        Returns the fraction of value retained after crash.
        magnitude=1.0  → full crash
        magnitude=0.5  → moderate crash (50 % of expected loss)
        """
        effective_loss = self.expected_crash_pct * magnitude
        return 1.0 + (effective_loss / 100.0)

    def crash_impact(self, total_value: float, magnitude: float = 1.0) -> float:
        """Absolute INR loss (negative) or gain for this asset."""
        asset_value = self.allocation_fraction * total_value
        return asset_value * (self.crash_value_fraction(magnitude) - 1.0)

    def risk_score(self) -> float:
        """allocation × |crash magnitude| — used to find largest risk asset."""
        return self.allocation_pct * abs(self.expected_crash_pct)


@dataclass
class Portfolio:
    total_value_inr: float
    monthly_expenses_inr: float
    assets: list[Asset] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def validate(self) -> None:
        if self.total_value_inr <= 0:
            raise ValueError("total_value_inr must be positive.")
        if self.monthly_expenses_inr < 0:
            raise ValueError("monthly_expenses_inr cannot be negative.")
        total_alloc = sum(a.allocation_pct for a in self.assets)
        if self.assets and abs(total_alloc - 100.0) > 0.01:
            raise ValueError(
                f"Asset allocations must sum to 100 (got {total_alloc:.2f})."
            )

    # ------------------------------------------------------------------
    # Scenario computation
    # ------------------------------------------------------------------

    def post_crash_value(self, magnitude: float = 1.0) -> float:
        """Portfolio value after crash scenario."""
        total_change = sum(a.crash_impact(self.total_value_inr, magnitude)
                           for a in self.assets)
        return self.total_value_inr + total_change

    def runway_months(self, magnitude: float = 1.0) -> float:
        """Months the post-crash portfolio can cover monthly expenses."""
        if self.monthly_expenses_inr <= 0:
            return float("inf")
        return self.post_crash_value(magnitude) / self.monthly_expenses_inr

    def ruin_test(self, magnitude: float = 1.0) -> str:
        return "PASS" if self.runway_months(magnitude) > 12 else "FAIL"

    def largest_risk_asset(self) -> str:
        """Asset with the highest (allocation × |crash magnitude|) score."""
        if not self.assets:
            return "N/A"
        return max(self.assets, key=lambda a: a.risk_score()).name

    def concentration_warning(self) -> bool:
        """True if any single asset exceeds 40 % of portfolio."""
        return any(a.allocation_pct > 40.0 for a in self.assets)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _build_portfolio(raw: dict[str, Any]) -> Portfolio:
    assets = [
        Asset(
            name=a["name"],
            allocation_pct=float(a["allocation_pct"]),
            expected_crash_pct=float(a["expected_crash_pct"]),
        )
        for a in raw.get("assets", [])
    ]
    return Portfolio(
        total_value_inr=float(raw["total_value_inr"]),
        monthly_expenses_inr=float(raw["monthly_expenses_inr"]),
        assets=assets,
    )


def compute_risk_metrics(portfolio_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Compute risk metrics for the given portfolio dictionary.

    Returns
    -------
    dict with keys:
        post_crash_value        – INR value after full crash
        runway_months           – months portfolio covers expenses post-crash
        ruin_test               – 'PASS' if runway > 12 months, else 'FAIL'
        largest_risk_asset      – name of highest-risk asset
        concentration_warning   – True if any asset > 40 % allocation

        moderate_post_crash_value   – INR value after moderate crash (50 %)
        moderate_runway_months      – runway under moderate crash
        moderate_ruin_test          – 'PASS'/'FAIL' under moderate crash
    """
    portfolio = _build_portfolio(portfolio_dict)
    portfolio.validate()

    full = dict(
        post_crash_value=round(portfolio.post_crash_value(1.0), 2),
        runway_months=round(portfolio.runway_months(1.0), 2),
        ruin_test=portfolio.ruin_test(1.0),
        largest_risk_asset=portfolio.largest_risk_asset(),
        concentration_warning=portfolio.concentration_warning(),
    )

    moderate = dict(
        moderate_post_crash_value=round(portfolio.post_crash_value(0.5), 2),
        moderate_runway_months=round(portfolio.runway_months(0.5), 2),
        moderate_ruin_test=portfolio.ruin_test(0.5),
    )

    return {**full, **moderate}
