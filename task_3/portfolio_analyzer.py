"""
portfolio_analyzer.py
---------------------
Pre-computes deterministic portfolio facts BEFORE handing them to the LLM.

Key design decision:
    LLMs are unreliable at arithmetic. This module does ALL the math
    (post-crash value, runway, concentration, risk scoring) in plain Python,
    then hands the LLM a clean fact sheet to interpret.

    This boosts both correctness (numbers are exact) and prompt quality
    (the LLM focuses on judgement, not calculation).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PortfolioFacts:
    """Everything the LLM needs to know about the portfolio — pre-computed."""
    total_value_inr:           float
    monthly_expenses_inr:      float
    asset_count:               int
    asset_breakdown:           list[dict[str, Any]]   # name, alloc%, crash%, risk_score
    post_crash_value:          float
    portfolio_loss_pct:        float
    runway_months:             float
    ruin_test:                 str                    # "PASS" / "FAIL"
    largest_risk_asset:        str
    largest_risk_score:        float
    most_concentrated_asset:   str
    most_concentrated_pct:     float
    concentration_warning:     bool
    risky_asset_share_pct:     float                  # % in assets with crash worse than -30%

    def to_prompt_block(self) -> str:
        """Render facts as an XML block for embedding in the LLM prompt."""
        lines = [
            "<portfolio_facts>",
            f"  <total_value_inr>{self.total_value_inr:,.0f}</total_value_inr>",
            f"  <monthly_expenses_inr>{self.monthly_expenses_inr:,.0f}</monthly_expenses_inr>",
            f"  <asset_count>{self.asset_count}</asset_count>",
            "  <assets>",
        ]
        for a in self.asset_breakdown:
            lines.append(
                f"    <asset name=\"{a['name']}\" "
                f"allocation_pct=\"{a['allocation_pct']}\" "
                f"expected_crash_pct=\"{a['expected_crash_pct']}\" "
                f"risk_score=\"{a['risk_score']:.0f}\" />"
            )
        lines += [
            "  </assets>",
            "  <crash_scenario>",
            f"    <post_crash_value_inr>{self.post_crash_value:,.0f}</post_crash_value_inr>",
            f"    <portfolio_loss_pct>{self.portfolio_loss_pct:.1f}</portfolio_loss_pct>",
            f"    <runway_months>{self.runway_months:.1f}</runway_months>",
            f"    <ruin_test>{self.ruin_test}</ruin_test>",
            "  </crash_scenario>",
            "  <risk_signals>",
            f"    <largest_risk_asset>{self.largest_risk_asset}</largest_risk_asset>",
            f"    <largest_risk_score>{self.largest_risk_score:.0f}</largest_risk_score>",
            f"    <most_concentrated_asset>{self.most_concentrated_asset}</most_concentrated_asset>",
            f"    <most_concentrated_pct>{self.most_concentrated_pct:.0f}</most_concentrated_pct>",
            f"    <concentration_warning>{str(self.concentration_warning).lower()}</concentration_warning>",
            f"    <risky_asset_share_pct>{self.risky_asset_share_pct:.0f}</risky_asset_share_pct>",
            "  </risk_signals>",
            "</portfolio_facts>",
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Computation
# ─────────────────────────────────────────────────────────────────────────────

def _validate(portfolio: dict[str, Any]) -> None:
    if portfolio.get("total_value_inr", 0) <= 0:
        raise ValueError("total_value_inr must be positive.")
    if portfolio.get("monthly_expenses_inr", -1) < 0:
        raise ValueError("monthly_expenses_inr cannot be negative.")
    assets = portfolio.get("assets", [])
    if not assets:
        raise ValueError("portfolio must contain at least one asset.")
    total_alloc = sum(a["allocation_pct"] for a in assets)
    if abs(total_alloc - 100.0) > 0.01:
        raise ValueError(f"asset allocations must sum to 100 (got {total_alloc:.2f}).")


def analyze(portfolio: dict[str, Any]) -> PortfolioFacts:
    """Compute every fact the LLM needs from a raw portfolio dict."""
    _validate(portfolio)

    total = float(portfolio["total_value_inr"])
    expenses = float(portfolio["monthly_expenses_inr"])
    assets = portfolio["assets"]

    # Per-asset enrichment
    breakdown = []
    for a in assets:
        risk_score = a["allocation_pct"] * abs(a["expected_crash_pct"])
        breakdown.append({
            "name":               a["name"],
            "allocation_pct":     a["allocation_pct"],
            "expected_crash_pct": a["expected_crash_pct"],
            "risk_score":         risk_score,
            "rupee_allocation":   total * a["allocation_pct"] / 100,
        })

    # Crash scenario (full magnitude)
    post_crash_value = sum(
        b["rupee_allocation"] * (1 + b["expected_crash_pct"] / 100)
        for b in breakdown
    )
    portfolio_loss_pct = (total - post_crash_value) / total * 100

    # Runway
    runway = float("inf") if expenses == 0 else post_crash_value / expenses
    ruin_test = "PASS" if runway > 12 else "FAIL"

    # Risk signals
    largest_risk    = max(breakdown, key=lambda b: b["risk_score"])
    most_concentrated = max(breakdown, key=lambda b: b["allocation_pct"])
    concentration_warning = any(b["allocation_pct"] > 40 for b in breakdown)

    risky_share = sum(
        b["allocation_pct"] for b in breakdown
        if b["expected_crash_pct"] < -30
    )

    return PortfolioFacts(
        total_value_inr=total,
        monthly_expenses_inr=expenses,
        asset_count=len(assets),
        asset_breakdown=breakdown,
        post_crash_value=round(post_crash_value, 2),
        portfolio_loss_pct=round(portfolio_loss_pct, 2),
        runway_months=round(runway, 2) if runway != float("inf") else float("inf"),
        ruin_test=ruin_test,
        largest_risk_asset=largest_risk["name"],
        largest_risk_score=largest_risk["risk_score"],
        most_concentrated_asset=most_concentrated["name"],
        most_concentrated_pct=most_concentrated["allocation_pct"],
        concentration_warning=concentration_warning,
        risky_asset_share_pct=risky_share,
    )
