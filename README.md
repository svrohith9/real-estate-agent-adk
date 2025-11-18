# Real Estate Deal Analyst (ADK)

[![CI](https://github.com/svrohith9/real-estate-agent-adk/actions/workflows/ci.yml/badge.svg)](https://github.com/svrohith9/real-estate-agent-adk/actions)

Monetization-ready ADK agent that analyzes residential deals (comps, mortgage math, rent-based valuation). Swap the demo data/tools for paid data feeds (MLS/comps APIs, rate sheets, tax/insurance APIs) and add auth/logging for billed tiers.

## Features
- `find_comps`: returns comparable properties from a sample CSV (replace with your data API).
- `mortgage_summary`: PITI + LTV + cashflow; plug in live rates/taxes/insurance.
- `rent_vs_price`: infers value from rent given a target cap and expense ratio.
- Replayable demo so you can run without typing.

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

## Monetization hooks
- Replace `data/comps.csv` with MLS/comps APIs or your own DB; add auth, logging, and metering.
- Built-in fallbacks: supports Estated (set `ESTATED_API_KEY`) and ATTOM (set `ATTOM_API_KEY`); otherwise uses demo CSV.
- Wrap financial tools with premium data (rate sheets, insurance, property tax services).
- Persist sessions and exports (PDF/CSV) for paid seats; add user roles and audit logs.
- Use replay files as regression tests for behavior guarantees (enterprise value prop).

## Tool signatures (keep simple for ADK)
- `find_comps(keyword: str, max_results: int = 3, preferred_source: str = "auto")`
- `mortgage_summary(price: float, down_payment: float, rate_percent: float, years: int, taxes_month: float = 0.0, insurance_month: float = 0.0, hoa_month: float = 0.0, rent_month: float = 0.0)`
- `rent_vs_price(rent_month: float, target_cap_rate: float = 5.0, expense_ratio: float = 0.35)`

## Sample data
`real_estate_agent/data/comps.csv` contains Springfield, IL sample comps. Swap with live feeds.

## Production hardening
- Keep tool signatures simple (already ADK-friendly). Validate numeric inputs (already in tools) and add region-specific caps/allowlists on live APIs.
- Centralize secrets (vault/KMS), never commit .env; enable audit logs for tool calls and user prompts.
- Add structured logging/metrics/tracing; hook replay files into CI for regression checks.
- Add rate limits and per-tenant auth if exposing as API/SaaS. Persist sessions and exports (PDF/CSV) under RBAC.

## Streamlit Cloud deploy notes
- Add secrets in the Streamlit dashboard: `GOOGLE_API_KEY`, `ATTOM_API_KEY`, `ESTATED_API_KEY` (if used).
- The UI auto-loads secrets into env on startup; providers will warn if a selected key is missing.
- `requirements.txt` already includes `streamlit` and `requests`; no extra steps needed.
