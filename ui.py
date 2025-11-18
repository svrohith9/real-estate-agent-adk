"""Streamlined Streamlit UI for Real Estate Deal Analyst."""

import os
import streamlit as st
from real_estate_agent.agent import find_comps, mortgage_summary, rent_vs_price

# Load secrets automatically on Streamlit Cloud
if hasattr(st, "secrets"):
    for key in ("GOOGLE_API_KEY", "ATTOM_API_KEY", "ESTATED_API_KEY"):
        if key in st.secrets and st.secrets[key]:
            os.environ[key] = str(st.secrets[key])

ATTOM_KEY_SET = bool(os.getenv("ATTOM_API_KEY"))
ESTATED_KEY_SET = bool(os.getenv("ESTATED_API_KEY"))

st.set_page_config(page_title="Real Estate Deal Analyst", layout="wide")


def as_float(label: str, default: float, min_val: float = 0.0, step: float = 0.01):
    return st.number_input(label, value=float(default), min_value=float(min_val), step=float(step))


def main():
    st.title("Real Estate Deal Analyst")
    st.caption("Comps, mortgage/PITI, and rent-based valuation using ATTOM/Estated or demo CSV.")

    # Inputs
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Property & Pricing")
        address = st.text_input("Address (include ZIP)", "1184 Lavaca Dr, Forney, TX 75126")
        price = as_float("Price assumption ($)", 350000, 0, 1000)
        fallback_price = as_float("Fallback price if comps have no price ($)", price, 0, 1000)
        down = as_float("Down payment ($)", price * 0.2, 0, 1000)
        rate = as_float("Rate (%)", 6.5, 0, 0.05)
        years = st.number_input("Term (years)", value=30, min_value=1, max_value=40, step=1)
        taxes = as_float("Taxes / mo ($)", 350, 0, 10)
        insurance = as_float("Insurance / mo ($)", 120, 0, 10)
        hoa = as_float("HOA / mo ($)", 0, 0, 10)
    with col2:
        st.subheader("Rent & Comps")
        rent = as_float("Rent / mo ($)", 2400, 0, 10)
        cap = as_float("Target cap rate (%)", 5.0, 0.1, 0.1)
        expense_ratio = as_float("Expense ratio (0-1)", 0.35, 0.0, 0.01)
        provider = st.selectbox(
            "Comps provider",
            options=["auto", "attom", "estated", "demo"],
            index=0,
            help="auto tries ATTOM, then Estated, then demo CSV.",
        )
        max_comps = int(st.number_input("Max comps", value=3, min_value=1, max_value=10, step=1))
        if provider == "attom" and not ATTOM_KEY_SET:
            st.info("ATTOM_API_KEY not set; will fall back.")
        if provider == "estated" and not ESTATED_KEY_SET:
            st.info("ESTATED_API_KEY not set; will fall back.")

    if st.button("Analyze", type="primary"):
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
            rent_result = rent_vs_price(rent_month=rent, target_cap_rate=cap, expense_ratio=expense_ratio)
        except Exception as e:
            st.error(f"Rent valuation error: {e}")

        # Highlights
        st.markdown("### Highlights")
        mcols = st.columns(3)
        if mort_result:
            mcols[0].metric("P&I", f"${mort_result['principal_interest']:,.0f}")
            mcols[1].metric("PITI", f"${mort_result['monthly_payment']:,.0f}")
            mcols[2].metric("Cashflow", f"${mort_result['cashflow']:,.0f}")
        if rent_result:
            st.metric("Implied value (rent-based)", f"${rent_result['implied_value']:,.0f}")

        # Details columns
        st.markdown("### Details")
        col_fin, col_comps = st.columns(2)
        with col_fin:
            st.markdown("**Mortgage & Cashflow**")
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

            st.markdown("**Rent-based valuation**")
            if rent_result:
                st.write(
                    f"NOI ${rent_result['noi']:,.0f} @ {rent_result['target_cap_rate']}% cap → "
                    f"Value ${rent_result['implied_value']:,.0f}"
                )
            else:
                st.info("No rent-based valuation (check inputs).")

        with col_comps:
            st.markdown("**Comparable properties**")
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
