"""
critic.py
---------
BONUS feature: a second LLM call that audits the first explanation for
accuracy, actionability, and tone-match.

This is a simple form of LLM-as-judge — useful for catching hallucinated
numbers or generic, non-actionable advice in the first response.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from llm_client          import LLMResponse, call_llm
from portfolio_analyzer  import PortfolioFacts
from prompts             import build_critique_system_prompt, build_critique_user_prompt


@dataclass
class Critique:
    accuracy:      int
    actionability: int
    tone_match:    int
    issues_found:  list[str]
    overall:       str
    raw:           LLMResponse


def critique_explanation(facts: PortfolioFacts, explanation_json: dict) -> Critique:
    """Run the auditor LLM call and parse the result."""
    system = build_critique_system_prompt()
    user   = build_critique_user_prompt(facts, json.dumps(explanation_json, indent=2))

    resp = call_llm(system, user, temperature=0.2)

    j = resp.parsed_json
    return Critique(
        accuracy      = int(j.get("accuracy", 0)),
        actionability = int(j.get("actionability", 0)),
        tone_match    = int(j.get("tone_match", 0)),
        issues_found  = list(j.get("issues_found", [])),
        overall       = str(j.get("overall", "")),
        raw           = resp,
    )
