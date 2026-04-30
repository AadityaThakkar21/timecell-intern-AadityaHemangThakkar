# Portfolio Risk Calculator

A tool that computes key risk metrics a wealth manager would use
to assess whether a portfolio is safe — including crash scenarios, runway
analysis, and concentration warnings.

---

## The Example Portfolio

All default calculations use the following 1 Crore (₹10,000,000) portfolio
with monthly living expenses of ₹80,000:

| Asset   | Allocation | Expected Crash Loss | Rationale                                               |
|---------|------------|---------------------|---------------------------------------------------------|
| BTC     | 30 %       | −80 %               | Crypto is highly volatile; historic bear markets have seen 80 %+ drawdowns |
| NIFTY50 | 40 %       | −40 %               | Indian large-cap index; a severe crash (e.g. 2008) could halve its value   |
| GOLD    | 20 %       | −15 %               | Safe-haven asset; typically falls less but is not crash-immune              |
| CASH    | 10 %       |  0 %                | Held in savings / FD; suffers no crash loss                                 |

```python
portfolio = {
    "total_value_inr":      10_000_000,   # ₹1 Crore
    "monthly_expenses_inr":     80_000,   # ₹80,000 / month
    "assets": [
        {"name": "BTC",     "allocation_pct": 30, "expected_crash_pct": -80},
        {"name": "NIFTY50", "allocation_pct": 40, "expected_crash_pct": -40},
        {"name": "GOLD",    "allocation_pct": 20, "expected_crash_pct": -15},
        {"name": "CASH",    "allocation_pct": 10, "expected_crash_pct":   0},
    ],
}
```

---

## Crash Scenarios

The calculator models two scenarios to bracket the range of outcomes — a
catastrophic worst case and a painful-but-survivable moderate downturn.

### Full Crash (magnitude = 100 %)

Every asset loses its full `expected_crash_pct`. This represents a black-swan
event — a simultaneous crypto collapse, equity bear market, and commodities
sell-off, similar in severity to 2008 or the 2022 crypto winter.

**Formula per asset:**

```
post_crash_asset_value = (allocation_pct / 100) × total_value × (1 + expected_crash_pct / 100)
```

**Worked example — Full Crash on the sample portfolio:**

| Asset   | Pre-Crash Value | Crash Factor | Post-Crash Value |
|---------|-----------------|:------------:|------------------|
| BTC     | ₹3,000,000      | × 0.20       | ₹600,000         |
| NIFTY50 | ₹4,000,000      | × 0.60       | ₹2,400,000       |
| GOLD    | ₹2,000,000      | × 0.85       | ₹1,700,000       |
| CASH    | ₹1,000,000      | × 1.00       | ₹1,000,000       |
| **Total** | **₹10,000,000** |            | **₹5,700,000**   |

The portfolio loses **43 %** of its value in a full crash.

### Moderate Crash (magnitude = 50 %)

Every asset loses **half** of its expected crash magnitude. This models a
sharp but not catastrophic correction — think a single-sector downturn or a
recession that stops short of a full depression.

**Formula:**

```
effective_loss_pct     = expected_crash_pct × 0.5
post_crash_asset_value = (allocation_pct / 100) × total_value × (1 + effective_loss_pct / 100)
```

**Worked example — Moderate Crash on the sample portfolio:**

| Asset   | Pre-Crash Value | Effective Loss | Crash Factor | Post-Crash Value |
|---------|-----------------|:--------------:|:------------:|------------------|
| BTC     | ₹3,000,000      | −40 %          | × 0.60       | ₹1,800,000       |
| NIFTY50 | ₹4,000,000      | −20 %          | × 0.80       | ₹3,200,000       |
| GOLD    | ₹2,000,000      | −7.5 %         | × 0.925      | ₹1,850,000       |
| CASH    | ₹1,000,000      |  0 %           | × 1.00       | ₹1,000,000       |
| **Total** | **₹10,000,000** |              |              | **₹7,850,000**   |

The portfolio loses **21.5 %** of its value in a moderate crash.

---

## Metrics Explained

### `post_crash_value`

The total INR value of the portfolio immediately after the crash plays out.
Each asset's post-crash value is calculated individually and summed.

- Sample **full crash**: **₹5,700,000** (lost ₹4.3 lakh)
- Sample **moderate crash**: **₹7,850,000** (lost ₹2.15 lakh)

---

### `runway_months`

How many months the surviving portfolio can cover household expenses, assuming
no further income or investment gains after the crash.

```
runway_months = post_crash_value / monthly_expenses_inr
```

- Sample (full crash): 5,700,000 ÷ 80,000 = **71.25 months** (~5.9 years)
- Sample (moderate): 7,850,000 ÷ 80,000 = **98.1 months** (~8.2 years)

If `monthly_expenses_inr` is zero, runway is reported as `∞` (infinite).

A high runway means the portfolio owner can weather the crash and live off
savings for years without being forced to sell at distressed prices or urgently
find new income.

---

### `ruin_test`

A simple solvency gate: **PASS** if `runway_months > 12`, **FAIL** otherwise.

The 12-month threshold represents one full year of expenses — a standard
financial planning buffer. A portfolio that cannot cover 12 months of expenses
after a crash is considered at risk of ruin (forced selling, debt, or default).

| Result | Meaning                                                              |
|--------|----------------------------------------------------------------------|
| `PASS` | Portfolio survives the crash with more than 1 year of runway         |
| `FAIL` | Post-crash value is dangerously low relative to monthly expenses     |

- Sample (full crash): **PASS** — 71.25 months is far above the 12-month gate
- Sample (moderate): **PASS** — 98.1 months

A portfolio fails when expenses are very high relative to the surviving value,
e.g. ₹2,000,000 total with ₹200,000/month expenses and 90 % in a −70 %
crash asset → only 3.7 months of runway → **FAIL**.

---

### `largest_risk_asset`

The asset that contributes the most absolute risk, ranked by:

```
risk_score = allocation_pct × |expected_crash_pct|
```

This combines *how much* is allocated with *how badly* it would crash — a
small allocation to an extremely volatile asset can outrank a large allocation
to a stable one.

**Sample portfolio risk scores:**

| Asset   | allocation_pct | \|crash_pct\| | Risk Score          |
|---------|:--------------:|:------------:|---------------------|
| BTC     | 30             | 80           | **2400** ← highest  |
| NIFTY50 | 40             | 40           | 1600                |
| GOLD    | 20             | 15           | 300                 |
| CASH    | 10             | 0            | 0                   |

Result: **BTC** — despite being only 30 % of the portfolio, its catastrophic
downside makes it the dominant risk factor. Reducing BTC allocation or hedging
it would have the largest positive impact on crash outcomes.

---

### `concentration_warning`

A boolean flag set to `True` when any single asset exceeds **40 %** of the
portfolio. High concentration amplifies exposure to asset-specific risks
(regulatory action, company failure, sector collapse) beyond what the crash
percentage alone captures.

```
concentration_warning = any(asset.allocation_pct > 40 for asset in assets)
```

- Sample portfolio: **False** — NIFTY50 is exactly 40 %, which does not
  exceed the threshold.
- A portfolio with 60 % in a single stock: **True**.

---

## Full Results for the Sample Portfolio

```json
{
    "post_crash_value":           5700000.0,
    "runway_months":                  71.25,
    "ruin_test":                    "PASS",
    "largest_risk_asset":            "BTC",
    "concentration_warning":           false,

    "moderate_post_crash_value":  7850000.0,
    "moderate_runway_months":         98.12,
    "moderate_ruin_test":           "PASS"
}
```

**Interpretation:** Even in the worst-case full-crash scenario this portfolio
retains ₹57 lakh and covers nearly 6 years of expenses — the ruin test passes
comfortably. The primary risk to monitor is BTC; reducing that 30 % allocation
or hedging it would significantly improve the crash outcome across both
scenarios.

---

## API Reference

```python
from risk_metrics import compute_risk_metrics

metrics = compute_risk_metrics(portfolio_dict)
```

### Returned dictionary

| Key                         | Type  | Description                                           |
|-----------------------------|-------|-------------------------------------------------------|
| `post_crash_value`          | float | Portfolio value after full crash (INR)                |
| `runway_months`             | float | Months post-crash portfolio covers monthly expenses   |
| `ruin_test`                 | str   | `"PASS"` if runway > 12 months, `"FAIL"` otherwise   |
| `largest_risk_asset`        | str   | Asset with highest allocation × \|crash magnitude\|   |
| `concentration_warning`     | bool  | `True` if any single asset > 40 % of portfolio        |
| `moderate_post_crash_value` | float | Portfolio value after moderate crash (50 % magnitude) |
| `moderate_runway_months`    | float | Runway months under moderate crash                    |
| `moderate_ruin_test`        | str   | `"PASS"` / `"FAIL"` under moderate crash              |

---

## Edge Cases Handled

| Situation                      | Behaviour                                                  |
|--------------------------------|------------------------------------------------------------|
| Zero monthly expenses          | `runway_months` = `∞`; ruin test always `PASS`             |
| 100 % cash portfolio           | No crash loss in any scenario; concentration warning fires |
| Single highly concentrated asset | `concentration_warning = True`; ruin test may `FAIL`   |
| `total_value_inr ≤ 0`          | `ValueError` raised with a descriptive message            |
| Allocations do not sum to 100  | `ValueError` raised showing the actual sum                 |

---

## AI Usage Note

This project was developed using Claude and GitHub Copilot
as AI pair-programmers. AI was not used as a black box — every suggestion was
read, understood, questioned, and validated before being accepted into the
codebase.
Tools Used
ToolPrimary RoleClaude (Anthropic)Architecture design, logic reasoning, test generation, docsGitHub CopilotInline autocomplete, boilerplate acceleration, refactoring

Prompting Approach
Rather than asking vague questions, prompts were crafted to be
specific, constrained, and iterative — treating the AI as a junior engineer
who needs clear requirements.
1. Context framing
Prompts opened by establishing the domain and constraints upfront, so the
model had full context before generating anything:

"You are helping build a financial risk calculator in Python 3.10+. No
external libraries. The core function must accept a portfolio dict and return
specific keys. Here is the input schema…"

This avoided generic solutions and kept output tightly scoped to the task.
2. Asking for reasoning, not just code
Before accepting any formula or design, the model was asked to explain its
logic:

This caught an early ambiguity in how magnitude should interact with
expected_crash_pct, which was resolved in discussion before a single line
of code was written.
3. Structured output requests
For the data model, the prompt specified the exact structure expected rather
than leaving it open:

"Represent each asset as a dataclass with name, allocation_pct, and
expected_crash_pct. The Portfolio class should own the scenario
computation methods. Show me only the class definitions first, no main
function yet."

Breaking requests into small, reviewable pieces meant each chunk could be
verified before building on top of it.
4. Edge-case-first test generation
Instead of asking for "some unit tests", the prompt listed the specific
scenarios to cover:

"Write unittest cases for: (a) the worked example from the brief with
manually verified expected values, (b) zero monthly expenses producing
infinite runway, (c) a 100 % cash portfolio, (d) an invalid total value
raising ValueError. Assert exact values, not just types."

5. Copilot for speed, Claude for reasoning
GitHub Copilot was used for repetitive or mechanical code — filling out
dataclass fields, completing f-string formatting, and generating the Unicode
bar-chart loop once the pattern was established. Claude was used when
decisions required reasoning: choosing dataclasses over TypedDict,
deciding where validation should live, and structuring the two-scenario
return dictionary.
