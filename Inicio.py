from pathlib import Path
import streamlit as st
rom greenscore_core import language_selector, _t

# Idiomas soportados
LANG_OPTIONS = {
    "Español": "es",
    "English": "en",
    "Français": "fr",
    "Português": "pt",
    "Italiano": "it",
    "Deutsch": "de",
}

if "lang" not in st.session_state:
    st.session_state["lang"] = "es"

st.set_page_config(page_title="Eco Logic / AInergy Score", page_icon="⚡", layout="wide")

with st.sidebar:
    label = "Idioma / Language"
    choice = st.selectbox(label, list(LANG_OPTIONS.keys()), index=0, key="__lang_select")
    st.session_state["lang"] = LANG_OPTIONS[choice]


st.set_page_config(page_title="Inicio – GreenScore", page_icon="🌿", layout="wide")

language_selector()


# Sidebar visible y diseño compacto
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
    "con OpenAI (HTML y PDF A4 con portada, índice dinámico y numeración)."
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

st.caption("© GreenScore - AUnergy Score · Demo con módulo ISO 50001, reporte LLM y exportación PDF.")
