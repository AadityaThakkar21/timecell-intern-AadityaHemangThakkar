"""
main.py
-------
CLI entry point for the AI-powered Portfolio Explainer.

Usage examples:
    # Default portfolio (the one from the task brief)
    python main.py

    # Pick a built-in sample by name
    python main.py --portfolio aggressive

    # Set the audience tone (bonus feature)
    python main.py --tone beginner
    python main.py --tone expert

    # Add a second LLM pass that critiques the first explanation (bonus)
    python main.py --critique

    # Load your own portfolio from a JSON file
    python main.py --portfolio-file my_portfolio.json

    # Show the prompts the script would send (no API call) — handy for review
    python main.py --show-prompt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from critic              import critique_explanation
from display             import (
    print_critique, print_facts_summary, print_parsed_output, print_raw_response,
)
from llm_client          import LLMError, call_llm
from portfolio_analyzer  import analyze
from prompts             import build_system_prompt, build_user_prompt
from sample_portfolios   import SAMPLE_PORTFOLIOS, get_portfolio


# ─────────────────────────────────────────────────────────────────────────────
# CLI parsing
# ─────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="AI-powered portfolio risk explainer (uses Gemini)."
    )
    p.add_argument(
        "--portfolio", default="default",
        choices=list(SAMPLE_PORTFOLIOS),
        help="Name of a built-in sample portfolio.",
    )
    p.add_argument(
        "--portfolio-file", type=Path, default=None,
        help="Path to a JSON file containing a custom portfolio (overrides --portfolio).",
    )
    p.add_argument(
        "--tone", default="experienced",
        choices=["beginner", "experienced", "expert"],
        help="Audience tone for the explanation (bonus feature).",
    )
    p.add_argument(
        "--critique", action="store_true",
        help="Run a second LLM call that audits the first explanation (bonus feature).",
    )
    p.add_argument(
        "--show-prompt", action="store_true",
        help="Print the system + user prompts that would be sent, then exit. No API call.",
    )
    return p


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_portfolio(args: argparse.Namespace) -> dict:
    if args.portfolio_file:
        if not args.portfolio_file.exists():
            raise FileNotFoundError(f"No such file: {args.portfolio_file}")
        return json.loads(args.portfolio_file.read_text())
    return get_portfolio(args.portfolio)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    args = _build_parser().parse_args()

    # ── Load + analyze ────────────────────────────────────────────────────────
    try:
        portfolio = _load_portfolio(args)
        facts = analyze(portfolio)
    except (KeyError, ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"\n[ERROR] Could not load portfolio: {exc}", file=sys.stderr)
        return 1

    # ── Build prompts ─────────────────────────────────────────────────────────
    system_prompt = build_system_prompt(tone=args.tone)
    user_prompt   = build_user_prompt(facts)

    # Show-prompt mode (no API call)
    if args.show_prompt:
        print("─" * 70)
        print("SYSTEM PROMPT")
        print("─" * 70)
        print(system_prompt)
        print()
        print("─" * 70)
        print("USER PROMPT")
        print("─" * 70)
        print(user_prompt)
        return 0

    # ── Always show the deterministic facts first (transparency) ─────────────
    print_facts_summary(facts)

    # ── Primary LLM call ──────────────────────────────────────────────────────
    print("\n  Calling LLM…", end="", flush=True)
    try:
        response = call_llm(system_prompt, user_prompt)
    except LLMError as exc:
        print(" failed.")
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        return 1
    print(" done.")

    # Required by brief: print raw response AND structured output separately
    print_raw_response(response)
    print_parsed_output(response.parsed_json)

    # ── Optional critique pass ────────────────────────────────────────────────
    if args.critique:
        print("\n  Running critique pass…", end="", flush=True)
        try:
            crit = critique_explanation(facts, response.parsed_json)
        except LLMError as exc:
            print(" failed.")
            print(f"\n[ERROR] critique pass failed: {exc}", file=sys.stderr)
            return 0   # primary call still succeeded
        print(" done.")
        print_critique(crit)

    return 0


if __name__ == "__main__":
    sys.exit(main())
