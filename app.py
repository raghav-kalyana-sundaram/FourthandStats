"""FourthandStats — entry point.

Run with:
    streamlit run app.py
or:
    python app.py  (launches streamlit programmatically)
"""

import streamlit as st

st.set_page_config(
    page_title="FourthandStats",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("FourthandStats")
st.info(
    "Data layer not yet built. Run `python scripts/update_data.py --seasons 2024 2025` "
    "then `python scripts/rebuild_metrics.py` to get started."
)
