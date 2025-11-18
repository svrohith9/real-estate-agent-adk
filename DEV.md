# Developer Guide

This project is an ADK-based real estate deal analyst with pluggable comps providers (ATTOM, Estated) plus a Streamlit UI and ADK CLI/web interfaces.

## Prerequisites
- Python 3.11+
- API keys (optional): `GOOGLE_API_KEY` (Gemini), `ATTOM_API_KEY`, `ESTATED_API_KEY`
- Recommended: `virtualenv` or `python -m venv`

## Setup
```bash
cd ~/repos/real-estate-agent-adk
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment
Use a `.env` in `real_estate_agent/` or export in your shell:
```
GOOGLE_API_KEY="your_gemini_key"
ATTOM_API_KEY="your_attom_key"       # optional
ESTATED_API_KEY="your_estated_key"   # optional
```

## Running
- CLI interactive:  
  `TMPDIR=./tmp adk run real_estate_agent`
- CLI replay (scripted):  
  `TMPDIR=./tmp adk run --replay replay.json real_estate_agent`
- Streamlit UI:  
  `TMPDIR=./tmp streamlit run ui.py`
- ADK web UI:  
  `TMPDIR=./tmp adk web --port 8000`

## Comps providers
- `preferred_source` parameter (and UI select): `auto` (default) tries ATTOM → Estated → demo CSV.
- To force: set `preferred_source="attom"` or `"estated"` or `"demo"`.
- No keys => demo CSV fallback.

## GitHub secrets (recommendation)
Store API keys in repo secrets and load into CI/CD:
- `GOOGLE_API_KEY`
- `ATTOM_API_KEY`
- `ESTATED_API_KEY`

Example GitHub Actions step (not added here):
```yaml
- name: Run replay
  env:
    GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
    ATTOM_API_KEY: ${{ secrets.ATTOM_API_KEY }}
    ESTATED_API_KEY: ${{ secrets.ESTATED_API_KEY }}
    TMPDIR: ./tmp
  run: |
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    adk run --replay replay.json real_estate_agent
```

## Testing/regression
- Use `replay.json` (and add more) to keep behavior stable.
- For UI sanity: run `streamlit run ui.py` and verify provider switching.

## Production notes
- Add auth/RBAC and metering around tool calls.
- Persist sessions/exports (PDF/CSV) under user/tenant scopes.
- Centralize secrets (vault/KMS), add structured logs/metrics/traces.
- Rate-limit external API calls; cache read-heavy endpoints.
