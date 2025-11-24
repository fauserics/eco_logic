import streamlit as st
from greenscore_core import page_portfolio, language_selector

language_selector()

st.set_page_config(page_title="Portfolio – GreenScore", page_icon="🌿", layout="wide")
page_portfolio()
