"""Streamlit Community Cloud portfolio adapter for universal-ai-futures-bot.

This does not replace the original implementation.
"""
from pathlib import Path

import streamlit as st

TITLE = "ApexQuant ML Research"
ICON = "📈"
DESC = "A Streamlit and XGBoost prototype studying candlestick features and machine-learning market research."
CATEGORY = "Experimental ML market dashboard"
NOTICE = "This Streamlit Cloud entrypoint is a research showcase, not the original trading interface. It does not connect to exchanges, accept credentials or issue trading signals. Do not make real trading decisions from unvalidated models."
GITHUB = "https://github.com/mohsinattasial/universal-ai-futures-bot"
VERCEL = "https://mohsin-apexquant-research.vercel.app"
LOCAL_COMMAND = "python -m streamlit run app.py"
FEATURES = ["Technical feature engineering","XGBoost model experiments","Dashboard UI and simulations"]

st.set_page_config(page_title=TITLE + " | Mohsin Atta", page_icon=ICON, layout="wide")
st.caption("Mohsin Atta · GitHub Portfolio · Streamlit Cloud edition")
st.title(ICON + " " + TITLE)
st.write(DESC)
st.caption(CATEGORY)

left, right = st.columns(2)
with left:
    st.link_button("GitHub source code", GITHUB, use_container_width=True)
with right:
    st.link_button("Existing browser version", VERCEL, use_container_width=True)

st.info(NOTICE)
with st.expander("Original project and features", expanded=False):
    for feature in FEATURES:
        st.write("• " + feature)
    st.code(LOCAL_COMMAND, language="bash")

st.subheader("Project overview")
st.write("This page is a deployable portfolio presentation of the original repository. Use the GitHub link above to inspect the code and run it in its intended local environment.")

st.divider()
st.caption("© 2026 Mohsin Atta · Educational portfolio · MIT-licensed original code where applicable")
