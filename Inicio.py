from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Inicio – GreenScore", page_icon="🌿", layout="wide")

# Asegurar que el nav multipágina esté visible (por si quedó CSS previo)
st.markdown("""
<style>
section[data-testid="stSidebarNav"] { display:block !important; visibility:visible !important; }
.block-container { padding-top: 1.2rem !important; }
div[data-testid="stDecoration"] { display:none !important; }
</style>
""", unsafe_allow_html=True)

st.title("GreenScore")
st.write(
    "Evaluación ambiental de edificios y portafolios con un enfoque práctico. "
    "Integra scoring tipo **LEED/EDGE**, análisis por tipologías y el módulo "
    "**Energy Management (ISO 50001)**: carga de fotos y facturas/mediciones, "
    "definición de línea de base y EnPIs, número de usuarios y **reporte institucional** "
    "con OpenAI (HTML descargable) con estimación de ahorros."
)

# Imagen portada (sin scroll)
img_path = Path("assets/portada.jpg")
img_url = str(img_path) if img_path.exists() else \
    "https://images.unsplash.com/photo-1509395176047-4a66953fd231?q=80&w=1920&auto=format&fit=crop"

st.markdown(
    f"""
    <div style="margin-top:14px;">
      <img src="{img_url}" alt="Portada GreenScore"
           style="width:100%;
                  max-height:40vh;
                  object-fit:cover;
                  object-position:center;
                  border-radius:16px;
                  display:block;">
    </div>
    """,
    unsafe_allow_html=True
)

st.caption("© EcoLogic – GreenScore · Demo con módulo ISO 50001 y reporte LLM.")
