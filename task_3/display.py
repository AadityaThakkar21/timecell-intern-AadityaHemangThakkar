"""
display.py
----------
Stdout formatting for the explainer's output.

The brief explicitly requires:
  > Print the raw API response and the extracted structured output separately.

So this module has two clearly-named functions for the two outputs.
"""

from __future__ import annotations

import json
import shutil
from typing import Any

from critic     import Critique
from llm_client import LLMResponse

_WIDTH = min(shutil.get_terminal_size((80, 20)).columns, 90)


def _hr(char: str = "─") -> str:
    return char * _WIDTH


# ─────────────────────────────────────────────────────────────────────────────
# Per-section printers
# ─────────────────────────────────────────────────────────────────────────────

def print_facts_summary(facts) -> None:
    """One-line summary of the pre-computed facts (for context)."""
    print()
    print(_hr("═"))
    print("  PORTFOLIO FACT SHEET (computed in Python — exact numbers)")
    print(_hr("═"))
    print(f"  Total value           : ₹{facts.total_value_inr:,.0f}")
    print(f"  Monthly expenses      : ₹{facts.monthly_expenses_inr:,.0f}")
    print(f"  Post-crash value      : ₹{facts.post_crash_value:,.0f} "
          f"(loss of {facts.portfolio_loss_pct:.1f}%)")
    runway = "∞" if facts.runway_months == float("inf") else f"{facts.runway_months:.1f}"
    print(f"  Crash runway          : {runway} months  →  ruin test {facts.ruin_test}")
    print(f"  Largest risk asset    : {facts.largest_risk_asset} (score {facts.largest_risk_score:.0f})")
    print(f"  Most concentrated     : {facts.most_concentrated_asset} ({facts.most_concentrated_pct:.0f}%)")
    print(f"  Concentration warning : {'YES' if facts.concentration_warning else 'no'}")


def print_raw_response(resp: LLMResponse) -> None:
    """Print the raw LLM output exactly as returned (per brief requirement)."""
    print()
    print(_hr("═"))
    print(f"  RAW API RESPONSE  (model: {resp.model}, "
          f"in: {resp.input_tokens} tok, out: {resp.output_tokens} tok)")
    print(_hr("═"))
    print(resp.raw_text)


def print_parsed_output(parsed: dict[str, Any]) -> None:
    """Print the structured, parsed output in a clean human-readable form."""
    print()
    print(_hr("═"))
    print("  PARSED EXPLANATION  (extracted from JSON)")
    print(_hr("═"))

    summary    = parsed.get("summary", "(missing)")
    doing_well = parsed.get("doing_well", "(missing)")
    consider   = parsed.get("consider_changing", "(missing)")
    verdict    = parsed.get("verdict", "(missing)")

    print()
    print("  Summary:")
    print(f"    {summary}")
    print()
    print("  What you're doing well:")
    print(f"    {doing_well}")
    print()
    print("  Consider changing:")
    print(f"    {consider}")
    print()
    print(f"  Verdict: {verdict.upper()}")
    print()


def print_critique(crit: Critique) -> None:
    """Print the optional second-pass critique."""
    print()
    print(_hr("═"))
    print("  CRITIQUE  (second LLM pass auditing the first explanation)")
    print(_hr("═"))
    print(f"  Accuracy      : {crit.accuracy}/5")
    print(f"  Actionability : {crit.actionability}/5")
    print(f"  Tone match    : {crit.tone_match}/5")

    if crit.issues_found:
        print(f"\n  Issues flagged ({len(crit.issues_found)}):")
        for issue in crit.issues_found:
            print(f"    • {issue}")
    else:
        print("\n  Issues flagged: none ✓")

    print(f"\n  Reviewer says: {crit.overall}")
    print()
