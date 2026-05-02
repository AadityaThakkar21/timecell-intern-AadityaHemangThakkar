"""
cli.py — Argument parsing, validation, and formatted output.

Keeps all I/O and presentation logic separate from the simulation engine.
Run this file directly: python cli.py --networth 1000000 ...
"""

import argparse
import sys
import numpy as np

import engine


# ---------------------------------------------------------------------------
# ARGUMENT PARSING & VALIDATION
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="monte_carlo_wealth",
        description="Monte Carlo simulation for personal wealth survival analysis.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--networth",       type=float, required=True,  help="Initial portfolio value ($)")
    p.add_argument("--monthly_burn",   type=float, required=True,  help="Monthly expenses ($)")
    p.add_argument("--years",          type=int,   required=True,  help="Simulation horizon (years)")

    p.add_argument("--equity",  type=float, default=0.6,  help="Equity allocation [0–1]")
    p.add_argument("--debt",    type=float, default=0.3,  help="Debt/bond allocation [0–1]")
    p.add_argument("--crypto",  type=float, default=0.1,  help="Crypto allocation [0–1]")

    p.add_argument("--equity_return",  type=float, default=0.10, help="Equity expected annual return")
    p.add_argument("--equity_vol",     type=float, default=0.18, help="Equity annual volatility")
    p.add_argument("--debt_return",    type=float, default=0.05, help="Debt expected annual return")
    p.add_argument("--debt_vol",       type=float, default=0.06, help="Debt annual volatility")
    p.add_argument("--crypto_return",  type=float, default=0.30, help="Crypto expected annual return")
    p.add_argument("--crypto_vol",     type=float, default=0.80, help="Crypto annual volatility")

    p.add_argument("--inflation",    type=float, default=0.05,  help="Annual inflation rate")
    p.add_argument("--simulations",  type=int,   default=10000, help="Number of Monte Carlo paths")
    p.add_argument("--seed",         type=int,   default=None,  help="Random seed for reproducibility")
    return p


def validate(args: argparse.Namespace) -> None:
    total = round(args.equity + args.debt + args.crypto, 6)
    if abs(total - 1.0) > 1e-4:
        sys.exit(
            f"[ERROR] Allocations must sum to 1.0 "
            f"(equity={args.equity} + debt={args.debt} + crypto={args.crypto} = {total:.4f})"
        )
    if args.networth <= 0:
        sys.exit("[ERROR] --networth must be positive.")
    if args.monthly_burn <= 0:
        sys.exit("[ERROR] --monthly_burn must be positive.")
    if args.years <= 0:
        sys.exit("[ERROR] --years must be a positive integer.")
    if args.simulations <= 0:
        sys.exit("[ERROR] --simulations must be a positive integer.")


def args_to_snapshot(args: argparse.Namespace) -> dict:
    """Package CLI args into a plain dict for passing to engine functions."""
    return {
        "networth":      args.networth,
        "monthly_burn":  args.monthly_burn,
        "years":         args.years,
        "weights":       [args.equity, args.debt, args.crypto],
        "annual_returns":[args.equity_return, args.debt_return, args.crypto_return],
        "annual_vols":   [args.equity_vol,    args.debt_vol,    args.crypto_vol],
        "inflation":     args.inflation,
    }


# ---------------------------------------------------------------------------
# OUTPUT RENDERING
# ---------------------------------------------------------------------------

def _fmt(v: float) -> str:
    """Compact dollar formatting."""
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v:,.0f}"
    return f"${v:.2f}"


def _wrap(text: str, width: int = 72, indent: str = "    ") -> str:
    """Naive word-wrap for insight lines."""
    words, lines, line = text.split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = indent + word
        else:
            line = (line + " " + word).lstrip()
    if line:
        lines.append(line)
    return ("\n" + indent).join(lines)


def print_results(
    metrics:   dict,
    insights:  list[str],
    snap:      dict,
    n_sims:    int,
    seed:      int | None,
) -> None:
    BAR  = "─" * 42
    DBAR = "═" * 42

    def row(label, value, width=28):
        return f"  {label:<{width}}: {value}"

    print()
    print(DBAR)
    print("  MONTE CARLO WEALTH SURVIVAL ANALYSIS")
    print(DBAR)
    print(row("Initial Net Worth",  _fmt(snap["networth"])))
    print(row("Monthly Burn",       _fmt(snap["monthly_burn"])))
    print(row("Time Horizon",       f"{snap['years']} years  ({snap['years']*12} months)"))
    print(row("Simulations",        f"{n_sims:,}"))
    print(row("Seed",               str(seed) if seed is not None else "random"))
    print()
    alloc = snap["weights"]
    print(row("Allocations", f"Equity {alloc[0]*100:.0f}%  Debt {alloc[1]*100:.0f}%  Crypto {alloc[2]*100:.0f}%"))
    print(row("Blended Return",     f"{metrics['blended_return']*100:.2f}% / yr"))
    print(row("Blended Volatility", f"{metrics['blended_vol']*100:.2f}% / yr"))
    print(row("Inflation",          f"{snap['inflation']*100:.1f}% / yr"))
    print(row("Withdrawal Rate",    f"{metrics['withdrawal_rate']:.2f}% / yr"))

    print()
    print(BAR)
    print("  SURVIVAL METRICS")
    print(BAR)
    print(row("Probability of Ruin",
              f"{metrics['prob_ruin']:.2f}%  ({metrics['n_ruined']:,} / {n_sims:,} paths)"))
    print(row("Median Ending Wealth",  _fmt(metrics["median_wealth"])))
    print(row("10th Percentile",       _fmt(metrics["p10_wealth"])))
    print(row("90th Percentile",       _fmt(metrics["p90_wealth"])))
    print(row("Minimum Observed",      _fmt(metrics["min_wealth"])))

    print()
    print(BAR)
    print("  TIME TO RUIN")
    print(BAR)
    if metrics["median_ttr_years"] is not None:
        print(row("Median Time to Ruin",  f"{metrics['median_ttr_years']:.1f} years"))
        print(row(f"Early Ruin (<{snap['years']//3}yr) Share",
                  f"{metrics['early_ruin_pct']:.1f}% of ruined paths"))
    else:
        print("  No ruin events observed.")

    print()
    print(BAR)
    print("  INSIGHTS")
    print(BAR)
    for insight in insights:
        print(f"  • {_wrap(insight)}")
        print()

    print(DBAR)
    print()


# ---------------------------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()
    validate(args)

    snap = args_to_snapshot(args)

    print(f"\n[+] Running {args.simulations:,} simulations over {args.years}-year horizon…", flush=True)

    results  = engine.run(
        networth       = snap["networth"],
        monthly_burn   = snap["monthly_burn"],
        years          = snap["years"],
        weights        = np.array(snap["weights"]),
        annual_returns = np.array(snap["annual_returns"]),
        annual_vols    = np.array(snap["annual_vols"]),
        inflation      = snap["inflation"],
        n_sims         = args.simulations,
        seed           = args.seed,
    )

    metrics  = engine.compute_metrics(results, snap)
    insights = engine.generate_insights(metrics, snap)

    print_results(metrics, insights, snap, args.simulations, args.seed)


if __name__ == "__main__":
    main()
