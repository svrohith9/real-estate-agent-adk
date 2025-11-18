"""Streamlit UI for the Real Estate Deal Analyst.

- Calls the existing ADK tools directly (does not re-implement LLM logic).
- Useful for demo/monetization pitch: comps table + mortgage + rent-based value + cashflow.
"""

import os
from pathlib import Path
from typing import List, Dict

import streamlit as st

from real_estate_agent.agent import (
    find_comps,
    mortgage_summary,
    rent_vs_price,
    DATA_DIR,
)

def _hydrate_env_from_streamlit_secrets() -> None:
    """If running on Streamlit Cloud, copy secrets into env so tools can read them."""
    if not hasattr(st, "secrets"):
        return
    for key in ("GOOGLE_API_KEY", "ATTOM_API_KEY", "ESTATED_API_KEY"):
        if key in st.secrets and st.secrets[key]:
            os.environ[key] = str(st.secrets[key])


_hydrate_env_from_streamlit_secrets()

ATTOM_KEY_SET = bool(os.getenv("ATTOM_API_KEY"))
ESTATED_KEY_SET = bool(os.getenv("ESTATED_API_KEY"))

st.set_page_config(page_title="Real Estate Deal Analyst", layout="wide")

# Minimal styling for cards/spacing.
st.markdown(
    """
    <style>
    .metric-card {padding: 1rem; border-radius: 0.5rem; background: #0f1116;
                  border: 1px solid rgba(255,255,255,0.08); margin-bottom: 0.75rem;}
    .muted {color: rgba(255,255,255,0.7);}
    </style>
    """,
    unsafe_allow_html=True,
)

def as_float(label: str, default: float, min_val: float = 0.0, step: float = 0.01):
    return st.number_input(label, value=float(default), min_value=float(min_val), step=float(step))

def main():
    st.title("Real Estate Deal Analyst")
    st.caption("Comps + mortgage/PITI + rent-based valuation. Sources: ATTOM, Estated, or demo CSV.")

    # Sidebar controls
    st.sidebar.header("Data & Providers")
    provider = st.sidebar.selectbox(
        "Comps provider",
        options=["auto", "attom", "estated", "demo"],
        index=0,
        help="auto tries ATTOM, then Estated, then demo CSV.",
    )
    max_comps = int(st.sidebar.number_input("Max comps", value=3, min_value=1, max_value=10, step=1))
    fallback_price = as_float("Fallback price if comps have no price ($)", 350000, 0, 1000)
    if provider == "attom" and not ATTOM_KEY_SET:
        st.sidebar.warning("ATTOM_API_KEY not set; will fall back.")
    if provider == "estated" and not ESTATED_KEY_SET:
        st.sidebar.warning("ESTATED_API_KEY not set; will fall back.")

    # Main inputs
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Property & Pricing")
        address = st.text_input("Address (include ZIP for best match)", "1184 Lavaca Dr, Forney, TX 75126")
        price = as_float("Price assumption ($)", 350000, 0, 1000)
        down = as_float("Down payment ($)", price * 0.2, 0, 1000)
        rate = as_float("Rate (%)", 6.5, 0, 0.05)
        years = st.number_input("Term (years)", value=30, min_value=1, max_value=40, step=1)
        taxes = as_float("Taxes / mo ($)", 350, 0, 10)
        insurance = as_float("Insurance / mo ($)", 120, 0, 10)
        hoa = as_float("HOA / mo ($)", 0, 0, 10)
    with col2:
        st.subheader("Rent & Valuation")
        rent = as_float("Rent / mo ($)", 2400, 0, 10)
        cap = as_float("Target cap rate (%)", 5.0, 0.1, 0.1)
        expense_ratio = as_float("Expense ratio (0-1)", 0.35, 0.0, 0.01)

    if st.button("Analyze", type="primary", use_container_width=True):
        # Comps
        comps_result = None
        try:
            comps_result = find_comps(address, max_results=max_comps, preferred_source=provider)
        except Exception as e:
            st.error(f"Comps lookup error: {e}")

        price_for_calc = price
        comps = []
        if comps_result:
            comps = comps_result.get("results") or []
            if comps and all(not c.get("price") for c in comps) and fallback_price:
                price_for_calc = fallback_price

        # Mortgage
        mort_result = None
        try:
            mort_result = mortgage_summary(
                price=price_for_calc,
                down_payment=down,
                rate_percent=rate,
                years=int(years),
                taxes_month=taxes,
                insurance_month=insurance,
                hoa_month=hoa,
                rent_month=rent,
            )
        except Exception as e:
            st.error(f"Mortgage calc error: {e}")

        # Rent-based valuation
        rent_result = None
        try:
            rent_result = rent_vs_price(
                rent_month=rent,
                target_cap_rate=cap,
                expense_ratio=expense_ratio,
            )
        except Exception as e:
            st.error(f"Rent valuation error: {e}")

        # Summary
        st.markdown("### Highlights")
        mcols = st.columns(3)
        if mort_result:
            mcols[0].metric("P&I", f"${mort_result['principal_interest']:,.0f}")
            mcols[1].metric("PITI", f"${mort_result['monthly_payment']:,.0f}")
            mcols[2].metric("Cashflow", f"${mort_result['cashflow']:,.0f}")

        if rent_result:
            st.markdown(
                f"<div class='metric-card'>Implied value from rent: "
                f"<strong>${rent_result['implied_value']:,.0f}</strong> "
                f"(@ {rent_result['target_cap_rate']}% cap, exp ratio {rent_result['expense_ratio']:.2f})</div>",
                unsafe_allow_html=True,
            )

        # Tabs for details
        tab_fin, tab_comps = st.tabs(["Financials", "Comps"])
        with tab_fin:
            st.markdown("#### Mortgage & Cashflow")
            if mort_result:
                st.write(
                    f"LTV {mort_result['ltv_percent']}% · Loan ${mort_result['loan_amount']:,.0f} · "
                    f"Down ${mort_result['down_payment']:,.0f} · Rate {mort_result['inputs']['rate_percent']}% · "
                    f"Term {mort_result['inputs']['years']} years"
                )
                st.write(
                    f"Taxes ${mort_result['inputs']['taxes_month']:,.0f} · "
                    f"Insurance ${mort_result['inputs']['insurance_month']:,.0f} · "
                    f"HOA ${mort_result['inputs']['hoa_month']:,.0f}"
                )
            else:
                st.info("No mortgage result (check inputs).")

            st.markdown("#### Rent-based valuation")
            if rent_result:
                st.write(
                    f"NOI ${rent_result['noi']:,.0f} @ {rent_result['target_cap_rate']}% cap → "
                    f"Value ${rent_result['implied_value']:,.0f}"
                )
            else:
                st.info("No rent-based valuation (check inputs).")

        with tab_comps:
            st.markdown("#### Comparable properties")
            if comps_result:
                source = comps_result.get("source", "unknown")
                st.write(f"Source: {source} — Found {comps_result['count']} (max {max_comps} shown)")
                if comps:
                    st.dataframe(comps, use_container_width=True)
                else:
                    st.info("No comps found for this keyword in current source.")
                if comps and all(not c.get("price") for c in comps) and fallback_price:
                    st.caption(f"Comps missing price; using fallback price ${fallback_price:,.0f} for analysis.")
            else:
                st.info("No comps yet. Enter an address and click Analyze.")

if __name__ == "__main__":
    main()
