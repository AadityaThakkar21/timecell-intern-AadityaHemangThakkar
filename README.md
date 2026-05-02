# Portfolio Analysis Suite

A collection of Python tools for portfolio risk analysis, asset price fetching, AI-powered explanations, and Monte Carlo wealth simulations.

---

## Task 1: Portfolio Risk Calculator

**Functionality:** Computes key risk metrics for investment portfolios including crash scenarios, runway analysis, and concentration warnings.

**Expected Output:**
- Post-crash portfolio values (full and moderate scenarios)
- Runway months (how long expenses can be covered)
- Ruin test results (PASS/FAIL based on 12-month threshold)
- Largest risk asset identification
- Concentration warnings for assets >40%

**Usage:**
```bash
cd task_1
python main.py
```

---

## Task 2: Asset Price Fetcher

**Functionality:** Fetches live prices for stocks (NSE-listed) and crypto assets from free public APIs (Yahoo Finance, CoinGecko), with robust error handling and formatted table output.

**Expected Output:**
- Formatted table showing asset name, price, currency, source, and timestamp
- Error summary for any failed fetches
- Exit code 0 if at least one fetch succeeds, 1 if all fail

**Usage:**
```bash
cd task_2
pip install -r requirements.txt
python main.py              # Live fetch
python main.py --demo       # Offline demo with mock data
python main.py --verbose    # Show debug logs
```

---

## Task 3: AI-Powered Portfolio Explainer

**Functionality:** Generates plain-English explanations of portfolio risk using the Gemini API, with configurable audience tones and optional critique pass.

**Expected Output:**
- Deterministic fact sheet (computed in Python)
- Raw API response from LLM
- Parsed structured explanation with summary, strengths, suggestions, and verdict
- Optional critique scoring (accuracy, actionability, tone-match)

**Usage:**
```bash
cd task_3
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here

python main.py                          # Default portfolio
python main.py --portfolio aggressive   # Built-in sample
python main.py --tone beginner          # Adjust audience level
python main.py --critique               # Add second LLM audit pass
python main.py --show-prompt            # Inspect prompts without API call
```

**Prompting Techniques Used:**
1. **System/User Prompt Separation** — System prompt anchors role and rules; user prompt carries per-call data
2. **XML Tags for Structure** — Wraps sections in tags like `<portfolio_facts>`, `<grounding_rules>` for reliable parsing
3. **Pre-computed Facts** — All math done in Python; LLM does interpretation, not arithmetic (eliminates hallucination)
4. **Tone as First-Class Variable** — Three profiles (beginner/experienced/expert) adjust vocabulary and analogy density
5. **Strict JSON Schema with One-Shot Example** — Declares exact output keys and provides worked example to reduce formatting errors
6. **Explicit Grounding Rules** — Forbids inventing numbers, predictions, or legal advice; requires claims grounded in supplied facts

---

## Task 4: Monte Carlo Wealth Survival Analysis

**Functionality:** Runs Monte Carlo simulations to model portfolio survival over time, accounting for asset allocation, volatility, inflation, and monthly expenses.

**Expected Output:**
- Probability of ruin (percentage of paths where wealth hits zero)
- Median ending wealth and percentile ranges (10th, 90th)
- Time-to-ruin statistics for failed paths
- Blended return and volatility metrics
- Actionable insights based on simulation results

**Usage:**
```bash
cd task_4
python cli.py --networth 1000000 --monthly_burn 5000 --years 30 \
              --equity 0.6 --debt 0.3 --crypto 0.1 \
              --simulations 10000 --seed 42
```

---

## Common Setup

All tasks use Python 3.10+ with minimal dependencies. Each task folder contains its own requirements.txt where needed.

**Testing:**
```bash
# Task 1
cd task_1 && python test_risk_metrics.py

# Task 2
cd task_2 && python test_fetcher.py

# Task 3
cd task_3 && python test_explainer.py

# Task 4
cd task_4 && python tests.py
```

---

## AI Development Notes

These projects were developed using **Claude (Anthropic)** and **GitHub Copilot** as AI pair-programmers. Key practices:

- **Context Framing** — Prompts established domain, constraints, and architecture upfront
- **Reasoning Before Code** — Asked AI to explain tradeoffs before generating implementations
- **Structured Requests** — Specified module breakdowns and exact interfaces rather than vague asks
- **Edge-Case-First Testing** — Defined specific failure modes to cover rather than generic test requests
- **Critical Review** — Every suggestion was read, questioned, and validated before acceptance

AI was used for architecture design, boilerplate acceleration, and test generation.
