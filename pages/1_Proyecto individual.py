import streamlit as st
import greenscore_core as gc  # 👈 importamos el módulo entero

# Config de la página
st.set_page_config(
    page_title="Proyectos individual",
    page_icon="🏗️",
    layout="wide",
)

# Selector de idioma SIEMPRE visible en la barra lateral
gc.language_selector()
lang = gc.get_lang()

# (Si más adelante traducís textos, podés usar `lang` aquí)
st.title("Proyecto individual")

# Render de la página usando la función del core
gc.page_proyecto_individual()
