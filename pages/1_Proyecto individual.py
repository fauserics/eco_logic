import streamlit as st
from greenscore_core import language_selector, get_lang, page_proyecto_individual

st.set_page_config(page_title="Proyecto individual – GreenScore", page_icon="🌿", layout="wide")

# Si querés un título arriba de la subpágina:
if lang == "en":
    st.title("AInergy Score Audit")
else:
    st.title("AInergy Score Audit")



# Selector de idioma en el sidebar
lang = get_lang()
page_proyecto_individual()
