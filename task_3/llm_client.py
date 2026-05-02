"""
llm_client.py
-------------
Thin wrapper around the Gemini-compatible LLM API.

Responsibilities:
  • Make the API call with sensible defaults.
  • Return BOTH the raw response (for printing per the brief) and the parsed JSON.
  • Handle missing API key, network failures, and malformed JSON gracefully.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, rely on system env vars

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    GENAI_AVAILABLE = False

try:
    from openai import OpenAI, APIError
except ImportError:                                       # pragma: no cover
    OpenAI   = None  # type: ignore[assignment,misc]
    APIError = Exception  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

# ── Default model + parameters ───────────────────────────────────────────────
# Gemini model name used for explanation generation.
DEFAULT_MODEL       = "gemini-flash-lite-latest"  # Lighter model with potentially different quota
DEFAULT_MAX_TOKENS  = 1024
DEFAULT_TEMPERATURE = 0.4   # low-medium: consistent across calls but not robotic


# ── Domain types ─────────────────────────────────────────────────────────────

@dataclass
class LLMResponse:
    raw_text:      str            # exactly what the model returned, for printing
    parsed_json:   dict[str, Any] # extracted + parsed JSON object
    model:         str
    input_tokens:  int
    output_tokens: int


class LLMError(Exception):
    """Raised when the LLM call fails or output is unusable."""


# ── Core call ────────────────────────────────────────────────────────────────

def call_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
) -> LLMResponse:
    """
    Send the prompt to Gemini and return both the raw text and parsed JSON.

    Raises
    ------
    LLMError : if the API key is missing, the network call fails, or the
               response cannot be parsed as JSON.
    """
    if not os.environ.get("GEMINI_API_KEY"):
        raise LLMError(
            "GEMINI_API_KEY not set. "
            "Set your Gemini key and run: "
            "export GEMINI_API_KEY=..."
        )

    api_key = os.environ["GEMINI_API_KEY"]
    
    # Use native Google Generative AI SDK if available
    if GENAI_AVAILABLE and api_key.startswith("AIza"):
        return _call_native_gemini(system_prompt, user_prompt, model, max_tokens, temperature, api_key)
    
    # Fall back to OpenAI-compatible endpoint
    return _call_openai_compatible(system_prompt, user_prompt, model, max_tokens, temperature, api_key)


def _call_native_gemini(
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
    api_key: str,
) -> LLMResponse:
    """Call Gemini using the native Google Generative AI SDK."""
    if not GENAI_AVAILABLE:
        raise LLMError("google-generativeai not installed — run: pip install google-generativeai")
    
    try:
        genai.configure(api_key=api_key)
        
        # Combine system and user prompts for Gemini
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        model_instance = genai.GenerativeModel(model)
        response = model_instance.generate_content(
            combined_prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
        )
        
        raw_text = response.text.strip()
        parsed = _extract_json(raw_text)
        
        # Gemini doesn't provide token counts in the same way
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, 'usage_metadata'):
            input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
        
        return LLMResponse(
            raw_text=raw_text,
            parsed_json=parsed,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    except Exception as exc:
        raise LLMError(f"Gemini API error: {exc}") from exc


def _call_openai_compatible(
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
    api_key: str,
) -> LLMResponse:
    """Call using OpenAI-compatible endpoint."""
    if OpenAI is None:
        raise LLMError("openai SDK not installed — run: pip install openai")
    
    gemini_base_url = os.environ.get("GEMINI_API_BASE_URL")
    
    if not gemini_base_url:
        raise LLMError(
            "For OpenAI-compatible mode, set GEMINI_API_BASE_URL to your proxy endpoint "
            "(e.g., LiteLLM, OpenRouter). Or install google-generativeai for native support."
        )

    client_kwargs = {"api_key": api_key}
    if gemini_base_url:
        client_kwargs["base_url"] = gemini_base_url

    # Some client libraries still read OPENAI_API_KEY internally.
    os.environ["OPENAI_API_KEY"] = api_key
    client = OpenAI(**client_kwargs)

    try:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        )
    except APIError as exc:
        raise LLMError(f"LLM API error: {exc}") from exc
    except Exception as exc:
        raise LLMError(f"Unexpected error calling LLM: {exc}") from exc

    # Chat Completions returns choices[0].message.content
    raw_text = (resp.choices[0].message.content or "").strip()

    parsed = _extract_json(raw_text)

    return LLMResponse(
        raw_text=raw_text,
        parsed_json=parsed,
        model=resp.model,
        input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
        output_tokens=resp.usage.completion_tokens if resp.usage else 0,
    )


# ── JSON extraction (defensive) ──────────────────────────────────────────────

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json(text: str) -> dict[str, Any]:
    """
    Extract a JSON object from the model's text response.

    The prompt instructs the model to return JSON only, but we defend against:
      • markdown code fences (```json ... ```)
      • leading/trailing prose
    """
    if not text:
        raise LLMError("LLM returned an empty response.")

    # 1. Try a fenced block first
    match = _JSON_FENCE_RE.search(text)
    candidate = match.group(1) if match else text

    # 2. Fall back to grabbing from first '{' to last '}'
    if not match:
        first, last = candidate.find("{"), candidate.rfind("}")
        if first == -1 or last == -1 or last <= first:
            raise LLMError(f"Could not find a JSON object in response:\n{text}")
        candidate = candidate[first : last + 1]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise LLMError(
            f"LLM response was not valid JSON: {exc}\n--- raw ---\n{text}"
        ) from exc
