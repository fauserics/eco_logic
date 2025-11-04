# eco_logic/Escenario.py  → Main (oculto en el menú) que redirige a Inicio
import streamlit as st

st.set_page_config(page_title="Inicio – GreenScore", page_icon="🌿", layout="wide")

# ---- Ocultar "Escenario" del menú multipágina (varias reglas por compatibilidad) ----
st.markdown("""
<style>
/* Oculta por título */
section[data-testid="stSidebarNav"] a[title="Escenario"] { display:none !important; }
/* Oculta por ruta que termine o contenga Escenario.py (según cómo monte el repo) */
section[data-testid="stSidebarNav"] a[href$="Escenario.py"] { display:none !important; }
section[data-testid="stSidebarNav"] a[href*="/Escenario.py"] { display:none !important; }
section[data-testid="stSidebarNav"] a[href*="eco_logic/Escenario.py"] { display:none !important; }
/* Fallback: si quedara como primer ítem, ocultar el primer li */
section[data-testid="stSidebarNav"] ul li:first-child { display:none !important; }

/* Compactar parte superior y quitar decoración de cabecera */
.block-container { padding-top: 1.1rem !important; }
div[data-testid="stDecoration"] { display:none !important; }
</style>
""", unsafe_allow_html=True)

# ---- Redirigir automáticamente a la portada real ----
try:
    st.switch_page("pages/0_Inicio.py")
except Exception:
    st.title("GreenScore")
    st.write("Redirigiendo a **Inicio**… Si no ocurre, seleccioná *Inicio* en el menú de la izquierda.")
