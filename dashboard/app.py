"""
MPF-PD Streamlit Research Dashboard -- Main Entry Point.

RESEARCH PROTOTYPE ONLY. NOT A CLINICAL DIAGNOSTIC DEVICE.
No clinical claims are made. Risk scores are investigational estimates only.
"""

import sys
import os
from pathlib import Path

# Ensure project root is importable
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

# -- page config (must be first Streamlit call) ------------------------------
st.set_page_config(
    page_title="MPF-PD Research Dashboard",
    page_icon="u'\U0001F9E0'",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboard.components.styles import inject_css
from dashboard.components.header import render_header
from dashboard.components.disclaimer import render_disclaimer
from dashboard.components.participant_input import render_participant_input
from dashboard.components.smell_input import render_smell_input
from dashboard.components.rbd_input import render_rbd_input
from dashboard.components.voice_upload import render_voice_upload
from dashboard.components.motor_upload import render_motor_upload
from dashboard.components.retinal_upload import render_retinal_upload
from dashboard.components.analysis_button import render_analysis_button
from dashboard.components.modality_results import render_modality_results
from dashboard.components.multimodal_result import render_multimodal_result
from dashboard.components.explainability import render_explainability
from dashboard.components.missing_modality import render_missing_modality_indicator

# -- inject global CSS -------------------------------------------------------
inject_css()

# -- page header ------------------------------------------------------------
render_header()

# -- sidebar -- research disclaimer -----------------------------------------
with st.sidebar:
    render_disclaimer()

# ===========================================================================
# SECTION 1 -- INPUT COLLECTION
# ===========================================================================
st.markdown("## Participant & Modality Input")
st.markdown("---")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    participant_data = render_participant_input()
    smell_data = render_smell_input()
    rbd_data = render_rbd_input()

with col_right:
    voice_data = render_voice_upload()
    motor_data = render_motor_upload()
    retinal_data = render_retinal_upload()

# ===========================================================================
# SECTION 2 -- RUN ANALYSIS
# ===========================================================================
st.markdown("---")
result = render_analysis_button(
    participant_data=participant_data,
    smell_data=smell_data,
    rbd_data=rbd_data,
    voice_data=voice_data,
    motor_data=motor_data,
    retinal_data=retinal_data,
)

# ===========================================================================
# SECTION 3 -- RESULTS (only rendered after analysis)
# ===========================================================================
if result is not None:
    st.markdown("---")
    render_missing_modality_indicator(result)

    st.markdown("---")
    render_modality_results(result)

    st.markdown("---")
    render_multimodal_result(result)

    st.markdown("---")
    render_explainability(result)

    st.markdown("---")
    render_disclaimer(inline=True)
