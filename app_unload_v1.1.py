import streamlit as st # type: ignore
import streamlit.components.v1 as components
from streamlit.components.v1 import declare_component
from datetime import date, timedelta, datetime
import time
from io import BytesIO
import json
import html
import os
import streamlit.components.v1 as components
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# PDF (ReportLab)
from reportlab.lib.pagesizes import letter # type: ignore
from reportlab.pdfgen import canvas # type: ignore

st.set_page_config(page_title="Load Management", layout="wide")
st.title("Load Management")

# ...existing code continues...# app_unload_v1.1.py (copy)
# This is a copy of the working version as of 2026-02-11.

# ...existing code...
