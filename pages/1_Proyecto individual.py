import streamlit as st
from greenscore_core import page_proyecto_individual, language_selector, _t

language_selector()

st.set_page_config(page_title="Proyecto individual – GreenScore", page_icon="🌿", layout="wide")
page_proyecto_individual()
