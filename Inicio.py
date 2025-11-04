# Inicio.py
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Inicio – GreenScore", page_icon="🌿", layout="wide")

# --- Renombrar el primer ítem del menú multipágina a "Inicio" y limpiar estilos ---
st.markdown("""
<style>
/* Cambia el texto del primer link del nav multipágina (suele ser el main script) */
section[data-testid="stSidebarNav"] ul li:first-child a span {
  visibility: hidden !important;
  position: relative;
}
section[data-testid="stSidebarNav"] ul li:first-child a span::after {
  content: "Inicio";
  visibility: visible;
  position: absolute;
  left: 0;
}
/* Quitar cualquier banner/padding visual extra arriba */
.block-container { padding-top: 2rem !important; }
</style>
""", unsafe_allow_html=True)

# --- Portada limpia (sin banner) ---
st.title("GreenScore")
st.write(
    "Evaluación ambiental de edificios y portafolios con un enfoque práctico. "
    "Integra scoring tipo **LEED/EDGE**, análisis por tipologías y el nuevo módulo de "
    "**Energy Management (ISO 50001)** que permite cargar fotos, facturas/mediciones, "
    "definir línea de base y EnPIs, considerar número de usuarios y generar un **reporte institucional** "
    "con LLM de OpenAI (HTML descargable) estimando ahorros y plan de implementación."
)

# Imagen: usa assets/portada.jpg si existe; si no, fallback
img_path = Path("assets/portada.jpg")
img_url = (
    str(img_path)
    if img_path.exists()
    else "https://images.unsplash.com/photo-1509395176047-4a66953fd231?q=80&w=1920&auto=format&fit=crop"
)

# HTML para limitar altura y evitar scroll; recorte con object-fit: cover
st.markdown(
    f"""
    <div style="margin-top:14px;">
      <img src="{img_url}" alt="Portada GreenScore"
           style="width:100%;max-height:420px;object-fit:cover;border-radius:16px;display:block;">
    </div>
    """,
    unsafe_allow_html=True
)

st.caption("© EcoLogic – GreenScore · Demo con módulo ISO 50001 y reporte LLM.")
