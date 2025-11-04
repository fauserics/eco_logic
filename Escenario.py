import streamlit as st
st.set_page_config(page_title="Inicio – GreenScore", page_icon="🌿", layout="wide")

# Ocultar el item "Escenario" del menú multipágina (varias reglas por compatibilidad)
st.markdown("""
<style>
section[data-testid="stSidebarNav"] ul li:first-child { display:none !important; }
section[data-testid="stSidebarNav"] a[title="Escenario"] { display:none !important; }
section[data-testid="stSidebarNav"] li a span:has(> span:contains("Escenario")) { display:none !important; }
</style>
""", unsafe_allow_html=True)

# Redirigir automáticamente a Inicio
try:
    st.switch_page("pages/0_Inicio.py")
except Exception:
    st.title("GreenScore")
    st.write("Redirigiendo a **Inicio**… Si no ocurre, elegí *Inicio* en el menú.")
