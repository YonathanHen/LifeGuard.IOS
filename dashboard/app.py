"""
SignalFlow — Streamlit Dashboard (MVP)
StatusBar + DecisionCard only — per PLANNING section 13
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import requests

API_BASE = "http://localhost:8000"  # Run: uvicorn api.main:app --reload


def status_bar(
    symbol: str,
    horizon: str,
    has_edge: bool,
    regime: str = "—",
    cooldown: bool = False,
    cooldown_day: int = 0,
    cooldown_total: int = 0,
):
    """Status bar — always visible."""
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Symbol:** {symbol}")
        st.markdown(f"**Horizon:** {horizon}")
    with col2:
        st.markdown(f"**Regime:** {regime}")
    with col3:
        if cooldown and cooldown_total > 0:
            status = f"🕐 Cooling down: Day {cooldown_day}/{cooldown_total}"
        else:
            status = "✔ Statistical Edge" if has_edge else "⚠ No statistical edge"
        st.markdown(f"**System Status:** {status}")
    st.markdown("---")


def decision_card(data: dict):
    """Decision card — one card, no action buttons."""
    direction_symbol = {"up": "↑", "down": "↓", "flat": "→"}[data.get("direction", "flat")]
    direction_label = {"up": "Up", "down": "Down", "flat": "Flat"}[data.get("direction", "flat")]

    st.markdown("### DECISION CARD")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Direction Expectation:**")
        st.markdown(f"## {direction_symbol} {direction_label} ({data.get('magnitude', '—')})")
    with col2:
        st.markdown("**Volatility / Risk:**")
        st.markdown(f"**{data.get('volatility_bucket', '—').title()}**")
        st.markdown(f"Risk Score: {data.get('risk_score', 0)} / 100")

    st.markdown("")
    st.markdown("**System Assessment:**")
    st.info(data.get("system_assessment", "—"))

    if data.get("ml_available") and data.get("ml_probs"):
        st.markdown("**ML Layer (LSTM):**")
        mp = data["ml_probs"]
        st.markdown(f"P(up)={mp.get('P_up', 0):.2f} | P(down)={mp.get('P_down', 0):.2f} | P(flat)={mp.get('P_flat', 0):.2f}")
    elif data.get("ml_available") is False:
        st.caption("ML model not trained. Run: python scripts/train_lstm.py")

    st.markdown("---")


def confidence_panel(factors: list):
    """Confidence — explained, not a number."""
    st.markdown("**Confidence Breakdown**")
    for name, passed in factors:
        icon = "✔" if passed else "✖"
        st.markdown(f"{icon} {name}")


def main():
    st.set_page_config(page_title="SignalFlow", layout="wide")
    st.title("SignalFlow — Market Decision Support")

    symbol = st.sidebar.text_input("Symbol", value="AAPL").upper()
    horizon = st.sidebar.selectbox("Horizon", ["daily", "weekly"], index=0)

    if st.sidebar.button("Get Prediction"):
        try:
            r = requests.get(f"{API_BASE}/predict/{symbol}", params={"horizon": horizon}, timeout=30)
            r.raise_for_status()
            data = r.json()
        except requests.exceptions.ConnectionError:
            st.error("API not running. Start with: uvicorn api.main:app --reload")
            return
        except Exception as e:
            st.error(str(e))
            return

        status_bar(
            symbol,
            horizon,
            data.get("has_edge", False),
            data.get("regime", "—"),
            cooldown=data.get("cooldown", False),
            cooldown_day=data.get("cooldown_day", 0),
            cooldown_total=data.get("cooldown_total", 0),
        )
        if not data.get("external_features_available", True):
            st.warning("External features (FRED) unavailable — Stat Core only. Set FRED_API_KEY for Credit Spreads.")
        decision_card(data)
        confidence_panel(data.get("confidence_factors", []))

    st.markdown("---")
    st.caption("*This system provides probabilistic decision support. No market direction is guaranteed.*")


if __name__ == "__main__":
    main()
