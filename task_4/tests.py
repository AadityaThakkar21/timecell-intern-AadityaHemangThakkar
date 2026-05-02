"""
tests.py — Lightweight smoke tests for the simulation engine.

Run with: python tests.py
No external test framework needed.
"""

import sys
import numpy as np
import engine


PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"

_failures = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global _failures
    if condition:
        print(f"  {PASS}  {name}")
    else:
        print(f"  {FAIL}  {name}" + (f"  [{detail}]" if detail else ""))
        _failures += 1


# --- Shared fixture ---

BASE = dict(
    networth       = 1_000_000,
    monthly_burn   = 4_000,
    years          = 30,
    weights        = np.array([0.6, 0.3, 0.1]),
    annual_returns = np.array([0.10, 0.05, 0.30]),
    annual_vols    = np.array([0.18, 0.06, 0.80]),
    inflation      = 0.05,
    n_sims         = 2_000,
    seed           = 0,
)


def make_results(**overrides):
    kwargs = {**BASE, **overrides}
    return engine.run(**kwargs)


# ---------------------------------------------------------------------------

def test_output_shapes():
    r = make_results()
    N = BASE["n_sims"]
    check("final_wealth shape",    r["final_wealth"].shape == (N,))
    check("ruined shape",          r["ruined"].shape == (N,))
    check("time_to_ruin shape",    r["time_to_ruin"].shape == (N,))
    check("n_months stored",       r["n_months"] == BASE["years"] * 12)


def test_dead_paths_stay_zero():
    """Once a path hits ruin, final wealth must be exactly 0."""
    r = make_results()
    ruined_wealth = r["final_wealth"][r["ruined"]]
    check("ruined paths have zero wealth", np.all(ruined_wealth == 0.0),
          f"non-zero ruined count: {(ruined_wealth != 0).sum()}")


def test_ttr_only_for_ruined():
    """time_to_ruin should be NaN iff the path survived."""
    r = make_results()
    ttr_nan    = np.isnan(r["time_to_ruin"])
    check("ttr NaN ↔ survived",   np.all(ttr_nan == ~r["ruined"]))


def test_ttr_in_valid_range():
    """All recorded ruin times must fall within [1, n_months]."""
    r = make_results()
    ttr_vals = r["time_to_ruin"][~np.isnan(r["time_to_ruin"])]
    if ttr_vals.size > 0:
        check("ttr ≥ 1",           ttr_vals.min() >= 1)
        check("ttr ≤ n_months",    ttr_vals.max() <= r["n_months"])
    else:
        check("ttr range (no ruin)", True)


def test_reproducibility():
    """Same seed → identical results."""
    r1 = make_results(seed=42)
    r2 = make_results(seed=42)
    check("reproducibility with seed", np.array_equal(r1["final_wealth"], r2["final_wealth"]))


def test_different_seeds_differ():
    r1 = make_results(seed=1)
    r2 = make_results(seed=2)
    check("different seeds produce different results", not np.array_equal(r1["final_wealth"], r2["final_wealth"]))


def test_high_burn_raises_ruin():
    """Extreme burn rate should produce near-100% ruin."""
    r = make_results(monthly_burn=50_000, seed=7)
    prob = r["ruined"].mean() * 100
    check(f"extreme burn → high ruin ({prob:.1f}%)", prob > 80,
          f"got {prob:.1f}%")


def test_near_zero_burn_rarely_ruins():
    """Trivially low burn should almost never ruin."""
    r = make_results(monthly_burn=100, seed=7)
    prob = r["ruined"].mean() * 100
    check(f"minimal burn → low ruin ({prob:.1f}%)", prob < 5,
          f"got {prob:.1f}%")


def test_metrics_keys():
    r    = make_results()
    snap = dict(
        networth      = BASE["networth"],
        monthly_burn  = BASE["monthly_burn"],
        years         = BASE["years"],
        weights       = BASE["weights"].tolist(),
        annual_returns= BASE["annual_returns"].tolist(),
        annual_vols   = BASE["annual_vols"].tolist(),
        inflation     = BASE["inflation"],
    )
    m = engine.compute_metrics(r, snap)
    required = {
        "prob_ruin", "median_wealth", "p10_wealth", "p90_wealth",
        "min_wealth", "median_ttr_years", "withdrawal_rate",
        "blended_return", "blended_vol", "early_ruin_pct", "n_ruined",
    }
    missing = required - m.keys()
    check("all metric keys present", not missing, f"missing: {missing}")
    check("prob_ruin in [0,100]",    0 <= m["prob_ruin"] <= 100)
    check("p10 ≤ median ≤ p90",
          m["p10_wealth"] <= m["median_wealth"] <= m["p90_wealth"])


def test_insights_non_empty():
    r    = make_results()
    snap = dict(
        networth      = BASE["networth"],
        monthly_burn  = BASE["monthly_burn"],
        years         = BASE["years"],
        weights       = BASE["weights"].tolist(),
        annual_returns= BASE["annual_returns"].tolist(),
        annual_vols   = BASE["annual_vols"].tolist(),
        inflation     = BASE["inflation"],
    )
    m = engine.compute_metrics(r, snap)
    ins = engine.generate_insights(m, snap)
    check("insights is a non-empty list", isinstance(ins, list) and len(ins) > 0)
    check("insights are strings",         all(isinstance(i, str) for i in ins))


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suites = [
        ("Output shapes",           test_output_shapes),
        ("Dead paths stay zero",     test_dead_paths_stay_zero),
        ("TTR only for ruined",      test_ttr_only_for_ruined),
        ("TTR in valid range",       test_ttr_in_valid_range),
        ("Reproducibility",         test_reproducibility),
        ("Different seeds differ",  test_different_seeds_differ),
        ("High burn → high ruin",   test_high_burn_raises_ruin),
        ("Low burn → low ruin",     test_near_zero_burn_rarely_ruins),
        ("Metrics keys & ranges",   test_metrics_keys),
        ("Insights generated",      test_insights_non_empty),
    ]

    print(f"\n{'─'*42}")
    print("  MONTE CARLO ENGINE — TEST SUITE")
    print(f"{'─'*42}")

    for name, fn in suites:
        print(f"\n  [{name}]")
        fn()

    print(f"\n{'─'*42}")
    if _failures == 0:
        print(f"  {PASS}  All tests passed.")
    else:
        print(f"  {FAIL}  {_failures} test(s) failed.")
    print(f"{'─'*42}\n")

    sys.exit(_failures)
