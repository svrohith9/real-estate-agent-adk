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

ATTOM_KEY_SET = bool(os.getenv("ATTOM_API_KEY"))
ESTATED_KEY_SET = bool(os.getenv("ESTATED_API_KEY"))

st.set_page_config(page_title="Real Estate Deal Analyst", layout="wide")
st.title("Real Estate Deal Analyst")
st.caption("Demo UI powered by the ADK tools. Swap data/APIs for production.")

def as_float(label: str, default: float, min_val: float = 0.0, step: float = 0.01):
    return st.number_input(label, value=float(default), min_value=float(min_val), step=float(step))

def main():
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Property & Pricing")
        address = st.text_input("Address keyword", "123 Maple St, Springfield")
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
        max_comps = int(st.number_input("Max comps", value=3, min_value=1, max_value=10, step=1))
        provider = st.selectbox(
            "Comps provider",
            options=["auto", "attom", "estated", "demo"],
            index=0,
            help="auto tries ATTOM, then Estated, then demo CSV.",
        )
        if provider == "attom" and not ATTOM_KEY_SET:
            st.warning("ATTOM provider selected but ATTOM_API_KEY is not set; expect fallback to next available source.")
        if provider == "estated" and not ESTATED_KEY_SET:
            st.warning("Estated provider selected but ESTATED_API_KEY is not set; expect fallback to next available source.")

    if st.button("Analyze", type="primary"):
        # Comps
        comps_result = None
        try:
            comps_result = find_comps(address, max_results=max_comps, preferred_source=provider)
        except Exception as e:
            st.error(f"Comps lookup error: {e}")

        # Mortgage
        mort_result = None
        try:
            mort_result = mortgage_summary(
                price=price,
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

        # Results layout
        colA, colB = st.columns(2)
        with colA:
            st.markdown("### Cashflow & Mortgage")
            if mort_result:
                st.metric("P&I", f"${mort_result['principal_interest']:,.0f}")
                st.metric("PITI", f"${mort_result['monthly_payment']:,.0f}")
                st.metric("Cashflow (rent - PITI)", f"${mort_result['cashflow']:,.0f}")
                st.caption(
                    f"LTV {mort_result['ltv_percent']}%, Loan ${mort_result['loan_amount']:,.0f}, "
                    f"Down ${mort_result['down_payment']:,.0f}"
                )

            st.markdown("### Rent-based valuation")
            if rent_result:
                st.metric("Implied value", f"${rent_result['implied_value']:,.0f}")
                st.caption(
                    f"NOI ${rent_result['noi']:,.0f} @ {rent_result['target_cap_rate']}% cap, "
                    f"expense ratio {rent_result['expense_ratio']:.2f}"
                )

        with colB:
            st.markdown("### Comps")
            if comps_result:
                source = comps_result.get("source", "unknown")
                st.write(f"Source: {source} — Found {comps_result['count']} comps (showing up to {max_comps})")
                if comps_result["results"]:
                    st.dataframe(comps_result["results"], use_container_width=True)
                else:
                    st.info("No comps found for this keyword in current source.")

if __name__ == "__main__":
    main()
