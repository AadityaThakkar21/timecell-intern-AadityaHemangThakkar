"""
engine.py — Monte Carlo simulation core, metrics, and insight generation.

All heavy computation lives here. No I/O, no argparse — pure functions
that take parameters and return structured results.
"""

import numpy as np


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _annual_to_monthly(annual_return: float, annual_vol: float) -> tuple[float, float]:
    """Convert annualised return/vol to monthly equivalents (log-normal scaling)."""
    return annual_return / 12.0, annual_vol / np.sqrt(12.0)


# ---------------------------------------------------------------------------
# SIMULATION
# ---------------------------------------------------------------------------

def run(
    networth:       float,
    monthly_burn:   float,
    years:          int,
    weights:        np.ndarray,      # [equity, debt, crypto]
    annual_returns: np.ndarray,      # [eq_ret, debt_ret, crypto_ret]
    annual_vols:    np.ndarray,      # [eq_vol, debt_vol, crypto_vol]
    inflation:      float,
    n_sims:         int,
    seed:           int | None,
) -> dict:
    """
    Vectorised Monte Carlo engine.

    Pre-allocates the full shock tensor (n_months × n_sims × n_assets) so the
    inner loop operates only over time steps, never over individual paths.
    Dead paths are hard-clamped to zero; they do not recover.

    Returns a dict of raw arrays — no formatting, no printing.
    """
    rng      = np.random.default_rng(seed)
    n_months = years * 12
    N        = n_sims

    # Monthly equivalents for each asset class
    monthly_means, monthly_stds = zip(*[
        _annual_to_monthly(r, v) for r, v in zip(annual_returns, annual_vols)
    ])
    monthly_means = np.array(monthly_means)   # (3,)
    monthly_stds  = np.array(monthly_stds)    # (3,)

    # Monthly inflation compounding factor
    monthly_infl = (1.0 + inflation) ** (1.0 / 12.0)

    # Full random shock matrix — generated once, shape (n_months, N, 3)
    shocks = rng.standard_normal(size=(n_months, N, 3))

    # Simulation state
    wealth       = np.full(N, networth, dtype=np.float64)
    ruined       = np.zeros(N, dtype=bool)
    time_to_ruin = np.full(N, np.nan)

    for t in range(n_months):
        # Asset returns this month: mu + sigma * Z, shape (N, 3)
        asset_returns = monthly_means + monthly_stds * shocks[t]

        # Weighted portfolio return, shape (N,)
        portfolio_return = asset_returns @ weights

        # Inflation-adjusted burn for this month
        burn_t = monthly_burn * (monthly_infl ** t)

        # Update wealth
        wealth = wealth * (1.0 + portfolio_return) - burn_t

        # Mark newly ruined paths
        newly_ruined        = (~ruined) & (wealth <= 0.0)
        time_to_ruin[newly_ruined] = t + 1   # 1-indexed month
        ruined             |= newly_ruined
        wealth[ruined]      = 0.0            # dead paths stay dead

    return {
        "final_wealth":   wealth,
        "ruined":         ruined,
        "time_to_ruin":   time_to_ruin,   # NaN = survived
        "n_months":       n_months,
        "N":              N,
    }


# ---------------------------------------------------------------------------
# METRICS
# ---------------------------------------------------------------------------

def compute_metrics(results: dict, args_snapshot: dict) -> dict:
    """
    Derive all decision-grade statistics from raw simulation output.

    args_snapshot: plain dict of CLI values needed for derived metrics
    (avoids coupling this module to argparse).
    """
    W      = results["final_wealth"]
    ruined = results["ruined"]
    ttr    = results["time_to_ruin"]
    N      = results["N"]

    prob_ruin = ruined.mean() * 100.0

    # Wealth distribution across ALL paths (ruined = 0)
    median_wealth = float(np.median(W))
    p10_wealth    = float(np.percentile(W, 10))
    p90_wealth    = float(np.percentile(W, 90))
    min_wealth    = float(W.min())

    # Time-to-ruin stats (ruined paths only)
    ruined_ttr       = ttr[ruined]
    median_ttr_years = float(np.median(ruined_ttr)) / 12.0 if ruined_ttr.size > 0 else None

    # Withdrawal rate
    withdrawal_rate = args_snapshot["monthly_burn"] * 12 / args_snapshot["networth"] * 100.0

    # Blended portfolio return and vol (annualised, no cross-correlation)
    w  = np.array(args_snapshot["weights"])
    ar = np.array(args_snapshot["annual_returns"])
    av = np.array(args_snapshot["annual_vols"])
    blended_return = float(np.dot(w, ar))
    blended_vol    = float(np.sqrt(np.dot(w ** 2, av ** 2)))

    # Early-ruin fraction: ruin within first third of horizon
    early_cutoff   = results["n_months"] / 3.0
    early_ruined   = (~np.isnan(ttr)) & (ttr <= early_cutoff)
    early_ruin_pct = early_ruined.sum() / N * 100.0 if ruined.any() else 0.0

    return {
        "prob_ruin":        prob_ruin,
        "median_wealth":    median_wealth,
        "p10_wealth":       p10_wealth,
        "p90_wealth":       p90_wealth,
        "min_wealth":       min_wealth,
        "median_ttr_years": median_ttr_years,
        "withdrawal_rate":  withdrawal_rate,
        "blended_return":   blended_return,
        "blended_vol":      blended_vol,
        "early_ruin_pct":   early_ruin_pct,
        "n_ruined":         int(ruined.sum()),
    }


# ---------------------------------------------------------------------------
# INSIGHTS
# ---------------------------------------------------------------------------

def generate_insights(metrics: dict, args_snapshot: dict) -> list[str]:
    """
    Rule-based insight engine. Every insight references actual computed values —
    no generic boilerplate. Returns a list of plain strings.
    """
    m       = metrics
    a       = args_snapshot
    insights = []

    # — Ruin probability severity —
    if m["prob_ruin"] > 50:
        insights.append(
            f"CRITICAL: {m['prob_ruin']:.1f}% of paths end in ruin. "
            "This portfolio is structurally unsustainable at current spending."
        )
    elif m["prob_ruin"] > 25:
        insights.append(
            f"High failure risk: {m['prob_ruin']:.1f}% ruin probability. "
            "Significant spending cuts or reallocation are necessary."
        )
    elif m["prob_ruin"] > 10:
        insights.append(
            f"Moderate ruin probability ({m['prob_ruin']:.1f}%). "
            "Portfolio survives most scenarios but is vulnerable to adverse sequences."
        )
    elif m["prob_ruin"] > 0:
        insights.append(f"Low ruin probability ({m['prob_ruin']:.1f}%). Tail risk remains but is manageable.")
    else:
        insights.append("Zero ruin events across all paths — portfolio appears highly durable.")

    # — Withdrawal rate vs 4% rule —
    wr = m["withdrawal_rate"]
    if wr > 6.0:
        insights.append(
            f"Withdrawal rate of {wr:.1f}%/yr far exceeds the 4% safe-withdrawal benchmark. "
            "Current burn is mathematically incompatible with long-term survival."
        )
    elif wr > 4.0:
        insights.append(
            f"Withdrawal rate of {wr:.1f}%/yr is above the 4% empirical threshold. "
            "Moderate spending cuts would materially reduce ruin probability."
        )
    elif wr < 2.0:
        insights.append(
            f"Withdrawal rate is only {wr:.1f}%/yr — well below growth potential. "
            "Wealth accumulation is likely even under adverse conditions."
        )

    # — Sequence-of-returns risk —
    if m["n_ruined"] > 0 and m["early_ruin_pct"] > 40:
        horizon_third = a["years"] // 3
        insights.append(
            f"{m['early_ruin_pct']:.0f}% of ruin events occur within the first {horizon_third} years. "
            "Strong sequence-of-returns risk — a bad early run permanently impairs recovery."
        )

    # — Crypto tail risk —
    crypto_alloc = a["weights"][2]
    crypto_vol   = a["annual_vols"][2]
    if crypto_alloc > 0.20:
        insights.append(
            f"Crypto at {crypto_alloc*100:.0f}% allocation ({crypto_vol*100:.0f}%/yr vol) "
            f"drives the p10/p90 wealth spread of ${m['p10_wealth']:,.0f} / ${m['p90_wealth']:,.0f}. "
            "Outsized tail risk in both directions."
        )
    elif crypto_alloc > 0.10:
        insights.append(
            f"Crypto at {crypto_alloc*100:.0f}% introduces meaningful tail risk. "
            "Consider sizing below 10% for controlled exposure."
        )

    # — Geometric variance drag —
    vol_drag = 0.5 * m["blended_vol"] ** 2
    if vol_drag > 0.03:
        insights.append(
            f"Portfolio vol of {m['blended_vol']*100:.1f}%/yr creates ~{vol_drag*100:.1f}%/yr variance drag, "
            "meaningfully reducing geometric compound growth below the arithmetic return."
        )

    # — Median time to ruin relative to horizon —
    if m["median_ttr_years"] is not None and m["median_ttr_years"] < a["years"] / 2:
        insights.append(
            f"Median ruin occurs at year {m['median_ttr_years']:.1f} — before the midpoint. "
            "Survival to full horizon requires an unusually favourable return sequence."
        )

    # — Outcome dispersion —
    p10, p90 = m["p10_wealth"], m["p90_wealth"]
    if p10 > 0 and p90 / p10 > 10:
        insights.append(
            f"Wide outcome spread: 90th percentile (${p90:,.0f}) is {p90/p10:.0f}x the 10th (${p10:,.0f}). "
            "Returns are strongly path-dependent."
        )

    return insights
