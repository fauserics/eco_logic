import streamlit as st
import greenscore_core as gc  # núcleo común

st.set_page_config(
    page_title="Portfolio con tipologías",
    page_icon="📊",
    layout="wide",
)

# Selector de idioma siempre visible en la barra lateral
gc.language_selector()
lang = gc.get_lang()  # por si luego querés usarlo en textos adicionales

st.title("Portfolio con tipologías")

# Contenido principal desde el core
gc.page_portfolio()
