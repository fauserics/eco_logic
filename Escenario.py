import streamlit as st

st.set_page_config(page_title="Inicio – GreenScore", page_icon="🌿", layout="wide")

# Oculta el primer item del nav multipágina (el main file)
st.markdown("""
<style>
section[data-testid="stSidebarNav"] ul li:first-child { display: none !important; }
</style>
""", unsafe_allow_html=True)

# Redirige automáticamente a la portada real
try:
    st.switch_page("pages/0_Inicio.py")
except Exception:
    st.title("GreenScore")
    st.write("Redirigiendo a **Inicio**… si no ocurre, entrá por el menú a la izquierda.")
