import streamlit as st
from greenscore_core import page_metodologia, language_selector


st.set_page_config(page_title="Metodología – GreenScore", page_icon="🌿", layout="wide")

language_selector()
page_metodologia()
