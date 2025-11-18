# Real Estate Deal Analyst (ADK)

[![CI](https://github.com/svrohith9/real-estate-agent-adk/actions/workflows/ci.yml/badge.svg)](https://github.com/svrohith9/real-estate-agent-adk/actions)

Real estate deal analyst built with ADK: comps lookup (ATTOM/Estated or demo CSV), mortgage/PITI + cashflow, rent-based valuation, and a Streamlit UI.

## Features
- Comps: ATTOM or Estated if keys are set; falls back to demo CSV.
- Mortgage/PITI + LTV + cashflow; rent-based valuation.
- Streamlit UI with provider selector and fallback price for missing comp prices.
- Replayable demo for regression/quick tests.

## Project layout
```
real-estate-agent-adk/
├─ requirements.txt
├─ replay.json              # sample non-interactive prompt
└─ real_estate_agent/
   ├─ agent.py              # defines root_agent and tools
   ├─ .env.example          # set GOOGLE_API_KEY here
   ├─ __init__.py
   └─ data/comps.csv        # demo comps (swap for APIs/DB)
```

## Quickstart
1) Python 3.11+ recommended:
   ```bash
   cd ~/repos/real-estate-agent-adk
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2) Set your Gemini key:
   ```bash
   cp real_estate_agent/.env.example real_estate_agent/.env  # then edit
   # or export GOOGLE_API_KEY="YOUR_KEY" in your shell
   ```

3) Run the agent (interactive):
   ```bash
   TMPDIR=~/repos/real-estate-agent-adk/tmp adk run real_estate_agent
   # Type prompts; 'exit' to quit.
   ```

4) Run the replay (scripted prompt):
   ```bash
   TMPDIR=~/repos/real-estate-agent-adk/tmp adk run --replay replay.json real_estate_agent
   ```

5) Web UI (optional):
   ```bash
   TMPDIR=~/repos/real-estate-agent-adk/tmp adk web --port 8000
   # open http://localhost:8000
   ```

## Tool signatures (keep simple for ADK)
- `find_comps(keyword: str, max_results: int = 3, preferred_source: str = "auto")`
- `mortgage_summary(price: float, down_payment: float, rate_percent: float, years: int, taxes_month: float = 0.0, insurance_month: float = 0.0, hoa_month: float = 0.0, rent_month: float = 0.0)`
- `rent_vs_price(rent_month: float, target_cap_rate: float = 5.0, expense_ratio: float = 0.35)`

## Sample data
`real_estate_agent/data/comps.csv` contains Springfield, IL sample comps. Swap with live feeds.

## Streamlit Cloud deploy notes
- Add secrets in the Streamlit dashboard: `GOOGLE_API_KEY`, `ATTOM_API_KEY`, `ESTATED_API_KEY` (if used).
- The UI auto-loads secrets into env on startup; providers will warn if a selected key is missing.
- `requirements.txt` already includes `streamlit` and `requests`; no extra steps needed.

## Logging
- Set `LOG_LEVEL` (default INFO) to see provider choices and API fallbacks in logs.
- ADK run logs to `tmp/agents_log/...` locally; Streamlit logs appear in the Cloud console.
