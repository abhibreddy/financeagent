"""
core/ui.py — shared Streamlit UI helpers.

inject_css() reads the single stylesheet from an absolute path, replacing the copy-pasted
CSS-read/inject blocks (and their fragile .parent / .parent.parent depth handling).
"""
import streamlit as st
from core.config import CSS_PATH


def inject_css():
    st.markdown(f"<style>{CSS_PATH.read_text()}</style>", unsafe_allow_html=True)
