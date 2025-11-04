# Escenario.py  → Portada (se muestra como "Inicio" con CSS)
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Inicio – GreenScore", page_icon="🌿", layout="wide")

# — CSS robusto: cambia el texto del primer ítem del nav multipágina a "Inicio"
st.markdown("""
<style>
/* En el sidebar multipágina, forzamos el label del primer item a "Inicio" */
section[data-testid="stSidebarNav"] ul li:first-child a * { 
  visibility: hidden !important; 
  position: relative; 
}
section[data-testid="stSidebarNav"] ul li:first-child a::after {
  content: "Inicio";
  visibility: visible; 
  position: absolute; 
  left: 0; 
  top: 0;
  color: inherit;
}
/* Reducir padding superior general y evitar banners */
.block-container { padding-top: 1.25rem !important; }
/* Evitar línea divisoria arriba en algunos temas */
div[data-testid="stDecoration"] { display:none !important; }
</style>
""", unsafe_allow_html=True)

# — Portada limpia
st.title("GreenScore")
st.write(
    "Evaluación ambiental de edificios y portafolios con un enfoque práctico. "
    "Integra scoring tipo **LEED/EDGE**, análisis por tipologías y el módulo "
    "**Energy Management (ISO 50001)** para cargar fotos, facturas/mediciones, "
    "definir línea de base y EnPIs, contemplar número de usuarios y generar un "
    "**reporte institucional** con LLM de OpenAI (HTML descargable) con estimación de ahorros."
)

# Imagen institucional: usa assets/portada.jpg si existe; caso contrario, fallback
img_path = Path("assets/portada.jpg")
img_url = (
    str(img_path)
    if img_path.exists()
    else "https://images.unsplash.com/photo-1509395176047-4a66953fd231?q=80&w=1920&auto=format&fit=crop"
)

# Imagen sin scroll (recorte con object-fit: cover)
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
