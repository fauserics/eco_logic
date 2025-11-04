import streamlit as st
from greenscore_core import page_energy_management

st.set_page_config(page_title="ISO 50001 – GreenScore", page_icon="🌿", layout="wide")
page_energy_management()
