"""Real Estate Deal Analyst agent for ADK.

Monetization-ready: swap the demo data/tool internals for paid MLS/comps APIs,
credit pulls, or financial calculators; add auth and logging around these tools.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Dict, List, Optional

from google.adk.agents.llm_agent import Agent

DATA_DIR = Path(__file__).resolve().parent / "data"
COMPS_FILE = DATA_DIR / "comps.csv"
MAX_RESULTS_HARD_LIMIT = 10
ESTATED_API_KEY = os.getenv("ESTATED_API_KEY")
ATTOM_API_KEY = os.getenv("ATTOM_API_KEY")


def _load_comps() -> List[Dict[str, str]]:
    with COMPS_FILE.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _clamp_max_results(max_results: int | None) -> int:
    """Keep result counts reasonable to avoid runaway queries."""
    if not max_results or max_results < 1:
        return 3
    return min(max_results, MAX_RESULTS_HARD_LIMIT)


def _require_positive(value: float, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be >= 0.")


def _provider_priority(preferred: str) -> List[str]:
    """Return ordered providers based on a preferred value."""
    preferred = preferred.lower()
    valid = {"auto", "attom", "estated", "demo"}
    if preferred not in valid:
        preferred = "auto"

    if preferred == "attom":
        return ["attom", "estated", "demo"]
    if preferred == "estated":
        return ["estated", "attom", "demo"]
    if preferred == "demo":
        return ["demo"]
    # auto
    return ["attom", "estated", "demo"]


def find_comps(
    keyword: str,
    max_results: int = 3,
    preferred_source: str = "auto",
) -> Dict[str, object]:
    """Return comparable properties that match an address keyword.

    Monetize: replace with an MLS/ATS/Prop data API; add auth and metering.
    """

    if not keyword or len(keyword.strip()) < 3:
        raise ValueError("keyword must be at least 3 characters of address text.")

    limited = _clamp_max_results(max_results)
    provider_order = _provider_priority(preferred_source)

    for provider in provider_order:
        if provider == "attom" and ATTOM_API_KEY:
            api_results = _fetch_attom(keyword, limited)
            if api_results is not None:
                return api_results
        if provider == "estated" and ESTATED_API_KEY:
            api_results = _fetch_estated(keyword, limited)
            if api_results is not None:
                return api_results
        if provider == "demo":
            break

    comps = _load_comps()
    keyword_lower = keyword.lower()
    matches = [c for c in comps if keyword_lower in c["address"].lower()]
    top = matches[:limited]
    return {"count": len(top), "source": "demo_csv", "results": top}


def mortgage_summary(
    price: float,
    down_payment: float,
    rate_percent: float,
    years: int,
    taxes_month: float = 0.0,
    insurance_month: float = 0.0,
    hoa_month: float = 0.0,
    rent_month: float = 0.0,
) -> Dict[str, float]:
    """Compute monthly PITI and simple cashflow.

    Monetize: tie into real rate sheets, insurance, and property tax APIs.
    """

    for v, name in [
        (price, "price"),
        (down_payment, "down_payment"),
        (rate_percent, "rate_percent"),
        (years, "years"),
        (taxes_month, "taxes_month"),
        (insurance_month, "insurance_month"),
        (hoa_month, "hoa_month"),
        (rent_month, "rent_month"),
    ]:
        _require_positive(v, name)

    if years < 1:
        raise ValueError("years must be >= 1.")
    if down_payment > price:
        raise ValueError("down_payment cannot exceed price.")

    loan = max(price - down_payment, 0)
    r = rate_percent / 100 / 12
    n = years * 12
    if r == 0:
        principal_interest = loan / n if n else 0
    else:
        principal_interest = loan * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    monthly = principal_interest + taxes_month + insurance_month + hoa_month
    cashflow = rent_month - monthly if rent_month else -monthly
    ltv = (loan / price) * 100 if price else 0

    return {
        "price": round(price, 2),
        "down_payment": round(down_payment, 2),
        "loan_amount": round(loan, 2),
        "ltv_percent": round(ltv, 2),
        "principal_interest": round(principal_interest, 2),
        "monthly_payment": round(monthly, 2),
        "cashflow": round(cashflow, 2),
        "inputs": {
            "rate_percent": rate_percent,
            "years": years,
            "taxes_month": taxes_month,
            "insurance_month": insurance_month,
            "hoa_month": hoa_month,
            "rent_month": rent_month,
        },
    }


def rent_vs_price(
    rent_month: float,
    target_cap_rate: float = 5.0,
    expense_ratio: float = 0.35,
) -> Dict[str, float]:
    """Estimate value from rent using a target cap rate and expense ratio.

    Monetize: connect to market rent APIs; make cap/expense data region-specific.
    """

    _require_positive(rent_month, "rent_month")
    if not (0 < target_cap_rate <= 25):
        raise ValueError("target_cap_rate must be between 0 and 25.")
    if not (0 <= expense_ratio < 1):
        raise ValueError("expense_ratio must be between 0 and 1 (exclusive of 1).")

    noi = rent_month * (1 - expense_ratio) * 12
    implied_value = noi / (target_cap_rate / 100)
    return {
        "rent_month": round(rent_month, 2),
        "noi": round(noi, 2),
        "implied_value": round(implied_value, 2),
        "target_cap_rate": target_cap_rate,
        "expense_ratio": expense_ratio,
    }


root_agent = Agent(
    model="gemini-2.5-flash",
    name="real_estate_deal_analyst",
    description="Analyzes residential deals: comps, pricing, rent/cap math, mortgage impacts.",
    instruction=(
        "You are a cautious real estate analyst. Always call tools before making claims. "
        "Use find_comps for pricing context, mortgage_summary for affordability, and "
        "rent_vs_price for rent-based valuation. Return concise deal notes with assumptions."
    ),
    tools=[find_comps, mortgage_summary, rent_vs_price],
)


# --- External API helper (Estated) ---
def _fetch_estated(keyword: str, max_results: int) -> Optional[Dict[str, object]]:
    """Query Estated property API; return None on failure so we can fall back to CSV."""
    import requests  # local import to avoid dependency if not used

    token = ESTATED_API_KEY
    if not token:
        return None

    params = {
        "token": token,
        "address": keyword,
    }
    try:
        resp = requests.get(
            "https://api.estated.com/property/v3",
            params=params,
            timeout=8,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return None

    data = payload.get("data")
    if not data:
        return None

    sales = data.get("sales", [])
    valuation = data.get("valuation", {})
    price = valuation.get("value")
    primary = {
        "address": _format_address(data),
        "city": data.get("address", {}).get("city"),
        "state": data.get("address", {}).get("state"),
        "beds": data.get("structure", {}).get("beds"),
        "baths": data.get("structure", {}).get("baths"),
        "sqft": data.get("structure", {}).get("square_feet"),
        "price": price,
        "list_date": sales[0].get("sale_date") if sales else None,
    }
    # Only one record returned per query; wrap as list for consistency.
    return {
        "count": 1 if price else 0,
        "source": "estated",
        "results": [primary] if price else [],
    }


def _format_address(data: Dict[str, object]) -> str:
    a = data.get("address", {}) or {}
    parts = [a.get("street_number"), a.get("street_name"), a.get("street_suffix")]
    return " ".join(str(p) for p in parts if p)


# --- External API helper (ATTOM) ---
def _fetch_attom(keyword: str, max_results: int) -> Optional[Dict[str, object]]:
    """Query ATTOM property API; return None on failure so we can fall back."""
    import requests  # local import to avoid dependency if not used

    api_key = ATTOM_API_KEY
    if not api_key:
        return None

    # ATTOM address endpoint expects free-form address; adjust endpoint as needed.
    url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/address"
    headers = {"apikey": api_key}
    params = {"address": keyword}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=8)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return None

    props = (payload.get("property") or [])[:max_results]
    if not props:
        return None

    results: List[Dict[str, object]] = []
    for p in props:
        addr = p.get("address", {}) or {}
        bldg = (p.get("building") or {})
        summary = (p.get("summary") or {})
        sales = (p.get("sale") or {})
        results.append(
            {
                "address": " ".join(
                    str(x)
                    for x in [
                        addr.get("line1"),
                        addr.get("line2"),
                    ]
                    if x
                ).strip(),
                "city": addr.get("locality"),
                "state": addr.get("countrySubd"),
                "beds": bldg.get("bedrooms"),
                "baths": bldg.get("bathrooms"),
                "sqft": bldg.get("size", {}).get("livingsize"),
                "price": sales.get("amount"),
                "list_date": sales.get("saleDate") or summary.get("propLandUse"),
            }
        )

    return {
        "count": len(results),
        "source": "attom",
        "results": results,
    }
