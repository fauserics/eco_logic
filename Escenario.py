# eco_logic/Escenario.py
import streamlit as st

st.set_page_config(page_title="Inicio – GreenScore", page_icon="🌿", layout="wide")

# --- Ocultar por completo el primer item "Escenario" del menú multipágina ---
st.markdown("""
<style>
/* Ocultar cualquier enlace o entrada que apunte a Escenario */
section[data-testid="stSidebarNav"] a[title="Escenario"],
section[data-testid="stSidebarNav"] a[href*="Escenario"],
section[data-testid="stSidebarNav"] ul li:first-child {
    display: none !important;
}
/* Quitar espacio sobrante si desaparece el primer ítem */
section[data-testid="stSidebarNav"] ul { margin-top: 0 !important; }

/* Compactar el cuerpo y eliminar decoración */
.block-container { padding-top: 1rem !important; }
div[data-testid="stDecoration"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# --- Redirigir automáticamente a la portada real ---
try:
    st.switch_page("pages/0_Inicio.py")
except Exception:
    st.write("Redirigiendo a **Inicio**… Si no ocurre automáticamente, seleccioná *Inicio* en el menú.")
