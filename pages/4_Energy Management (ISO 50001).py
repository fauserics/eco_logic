import streamlit as st
from greenscore_core import page_energy_management

st.set_page_config(page_title="AInergy Score Audit", page_icon="🌿", layout="wide")
page_energy_management()
