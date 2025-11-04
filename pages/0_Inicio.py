from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Inicio – GreenScore", page_icon="🌿", layout="wide")

# Compactar top y evitar decoraciones
st.markdown("""
<style>
.block-container { padding-top: 1.2rem !important; }
div[data-testid="stDecoration"] { display:none !important; }
</style>
""", unsafe_allow_html=True)

st.title("GreenScore")
st.write(
    "Evaluación ambiental de edificios y portafolios con un enfoque práctico. "
    "Integra scoring tipo **LEED/EDGE**, análisis por tipologías y el módulo "
    "**Energy Management (ISO 50001)** para cargar fotos, facturas/mediciones, "
    "definir línea de base y EnPIs, contemplar número de usuarios y generar un "
    "**reporte institucional** con LLM de OpenAI (HTML descargable) con estimación de ahorros."
)

# Imagen: sin scroll (limitada a la altura de la ventana)
img_path = Path("assets/portada.jpg")
img_url = str(img_path) if img_path.exists() else \
    "https://images.unsplash.com/photo-1509395176047-4a66953fd231?q=80&w=1920&auto=format&fit=crop"

st.markdown(
    f"""
    <div style="margin-top:14px;">
      <img src="{img_url}" alt="Portada GreenScore"
           style="width:100%;
                  max-height:48vh;        /* ajustá si querés 40–55vh */
                  object-fit:cover;
                  border-radius:16px;
                  display:block;">
    </div>
    """,
    unsafe_allow_html=True
)

st.caption("© EcoLogic – GreenScore · Demo con módulo ISO 50001 y reporte LLM.")
