"""Streamlit dashboard. M0 stub: confirms the router/QA services are reachable.
Gauges, routing mix, cost-vs-always-cloud, latency, QA stats, simulate sliders and the chat tab
land in M7 once there is real decision/answer traffic to visualize.
"""
from __future__ import annotations

import httpx
import streamlit as st

from app.core.config import get_settings

st.set_page_config(page_title="AMYPO Platform Dashboard", layout="wide")
st.title("AMYPO Platform Dashboard")
st.caption("M0 skeleton — full gauges, routing mix, cost/latency charts and chat tab land in M7.")

settings = get_settings()
router_url = "http://router:8000"
qa_url = "http://qa:8001"

col1, col2 = st.columns(2)

for col, name, url in ((col1, "Router", router_url), (col2, "Q&A", qa_url)):
    with col:
        st.subheader(f"{name} service")
        try:
            resp = httpx.get(f"{url}/api/v1/health", timeout=2.0)
            resp.raise_for_status()
            st.success(f"status: {resp.json().get('status')}")
            st.json(resp.json())
        except Exception as exc:  # noqa: BLE001 - dashboard best-effort status display
            st.error(f"unreachable: {exc}")
