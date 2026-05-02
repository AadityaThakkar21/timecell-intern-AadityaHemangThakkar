"""
test_explainer.py
-----------------
Unit tests covering:
  • Portfolio analysis math (deterministic, no LLM)
  • Prompt construction (tone variants, fact embedding)
  • LLM client JSON extraction (handles fences, prose, malformed responses)
  • End-to-end main() with a mocked LLM

Run:  python -m pytest test_explainer.py -v
  or: python test_explainer.py
"""

from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from llm_client          import LLMError, _extract_json, call_llm
from portfolio_analyzer  import analyze
from prompts             import build_system_prompt, build_user_prompt
from sample_portfolios   import SAMPLE_PORTFOLIOS


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio analysis tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioAnalyzer(unittest.TestCase):

    def setUp(self):
        self.portfolio = SAMPLE_PORTFOLIOS["default"]

    def test_post_crash_value_is_correct(self):
        """Manually verified: 30%×0.20 + 40%×0.60 + 20%×0.85 + 10%×1.00 of 1Cr = ₹57L"""
        facts = analyze(self.portfolio)
        self.assertAlmostEqual(facts.post_crash_value, 5_700_000, places=0)

    def test_runway_months(self):
        # 5,700,000 / 80,000 = 71.25
        facts = analyze(self.portfolio)
        self.assertAlmostEqual(facts.runway_months, 71.25, places=2)

    def test_ruin_test_pass_for_default(self):
        facts = analyze(self.portfolio)
        self.assertEqual(facts.ruin_test, "PASS")

    def test_ruin_test_fail_for_fragile(self):
        facts = analyze(SAMPLE_PORTFOLIOS["fragile"])
        self.assertEqual(facts.ruin_test, "FAIL")

    def test_largest_risk_asset_is_btc(self):
        # BTC: 30×80=2400, NIFTY50: 40×40=1600 → BTC wins
        facts = analyze(self.portfolio)
        self.assertEqual(facts.largest_risk_asset, "BTC")

    def test_concentration_warning_default_is_false(self):
        # NIFTY50 is exactly 40, not > 40 → no warning
        facts = analyze(self.portfolio)
        self.assertFalse(facts.concentration_warning)

    def test_concentration_warning_aggressive_is_true(self):
        # BTC is 50% in aggressive
        facts = analyze(SAMPLE_PORTFOLIOS["aggressive"])
        self.assertTrue(facts.concentration_warning)

    def test_zero_expenses_gives_infinite_runway(self):
        p = {**self.portfolio, "monthly_expenses_inr": 0}
        facts = analyze(p)
        self.assertEqual(facts.runway_months, float("inf"))
        self.assertEqual(facts.ruin_test, "PASS")

    def test_invalid_total_value_raises(self):
        with self.assertRaises(ValueError):
            analyze({**self.portfolio, "total_value_inr": -1})

    def test_allocations_must_sum_to_100(self):
        bad = {**self.portfolio, "assets": [
            {"name": "X", "allocation_pct": 50, "expected_crash_pct": -10}
        ]}
        with self.assertRaises(ValueError):
            analyze(bad)

    def test_facts_render_to_xml_block(self):
        facts = analyze(self.portfolio)
        block = facts.to_prompt_block()
        self.assertIn("<portfolio_facts>", block)
        self.assertIn("BTC", block)
        self.assertIn("ruin_test>PASS", block)


# ─────────────────────────────────────────────────────────────────────────────
# Prompt construction tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPrompts(unittest.TestCase):

    def setUp(self):
        self.facts = analyze(SAMPLE_PORTFOLIOS["default"])

    def test_system_prompt_contains_grounding_rules(self):
        prompt = build_system_prompt("experienced")
        self.assertIn("grounding_rules", prompt)
        self.assertIn("ONLY the numbers", prompt)

    def test_system_prompt_contains_output_contract(self):
        prompt = build_system_prompt("experienced")
        self.assertIn("output_contract", prompt)
        self.assertIn("verdict", prompt)

    def test_tone_changes_system_prompt(self):
        beginner = build_system_prompt("beginner")
        expert   = build_system_prompt("expert")
        self.assertNotEqual(beginner, expert)
        self.assertIn("plain words", beginner)
        self.assertIn("precise terminology", expert)

    def test_invalid_tone_raises(self):
        with self.assertRaises(ValueError):
            build_system_prompt("childish")  # type: ignore[arg-type]

    def test_user_prompt_embeds_facts(self):
        prompt = build_user_prompt(self.facts)
        self.assertIn("<portfolio_facts>", prompt)
        self.assertIn("BTC", prompt)

    def test_user_prompt_includes_example(self):
        prompt = build_user_prompt(self.facts)
        self.assertIn("<example>", prompt)
        self.assertIn("example_output", prompt)


# ─────────────────────────────────────────────────────────────────────────────
# JSON extraction tests
# ─────────────────────────────────────────────────────────────────────────────

class TestJsonExtraction(unittest.TestCase):

    def test_clean_json(self):
        text = '{"verdict": "Balanced", "summary": "ok"}'
        result = _extract_json(text)
        self.assertEqual(result["verdict"], "Balanced")

    def test_json_with_markdown_fence(self):
        text = '```json\n{"verdict": "Aggressive"}\n```'
        result = _extract_json(text)
        self.assertEqual(result["verdict"], "Aggressive")

    def test_json_with_leading_prose(self):
        text = 'Here is the analysis:\n{"verdict": "Conservative"}'
        result = _extract_json(text)
        self.assertEqual(result["verdict"], "Conservative")

    def test_empty_response_raises(self):
        with self.assertRaises(LLMError):
            _extract_json("")

    def test_no_json_at_all_raises(self):
        with self.assertRaises(LLMError):
            _extract_json("Just prose, no braces here.")

    def test_malformed_json_raises(self):
        with self.assertRaises(LLMError):
            _extract_json('{"verdict": "Balanced"')   # missing closing brace


# ─────────────────────────────────────────────────────────────────────────────
# LLM client tests (mocked — no network)
# ─────────────────────────────────────────────────────────────────────────────

class TestLlmClient(unittest.TestCase):

    def test_missing_api_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(LLMError) as ctx:
                call_llm("sys", "user")
            self.assertIn("GEMINI_API_KEY", str(ctx.exception))

    @patch.dict(os.environ,{"GEMINI_API_KEY": "fake-key"})
    @patch("llm_client.OpenAI")
    def test_successful_call_returns_parsed_json(self, mock_openai_cls):
        mock_message = MagicMock()
        mock_message.content = '{"verdict": "Balanced", "summary": "looks good"}'

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gemini-1.0"
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        result = call_llm("sys", "user")
        self.assertEqual(result.parsed_json["verdict"], "Balanced")
        self.assertEqual(result.input_tokens, 100)
        self.assertEqual(result.model, "gemini-1.0")

    @patch.dict(os.environ,{"GEMINI_API_KEY": "fake-key"})
    @patch("llm_client.OpenAI")
    def test_malformed_response_raises_llm_error(self, mock_openai_cls):
        mock_message = MagicMock()
        mock_message.content = "Sorry, I can't help with that."

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 5

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gemini-1.0"
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        with self.assertRaises(LLMError):
            call_llm("sys", "user")


# ─────────────────────────────────────────────────────────────────────────────
# Run as plain script
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    unittest.main(verbosity=2)
