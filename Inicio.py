from pathlib import Path
import streamlit as st
from greenscore_core import language_selector, _t

# ⚙️ Config general de la app
st.set_page_config(page_title="Eco Logic / AInergy Score", page_icon="⚡", layout="wide")

# 🌐 Selector de idioma SIEMPRE visible en la barra lateral
language_selector()

# 💄 Sidebar visible y diseño compacto
st.markdown(
    """
    <style>
    section[data-testid="stSidebarNav"] { display:block !important; visibility:visible !important; }
    .block-container { padding-top: 1.2rem !important; }
    div[data-testid="stDecoration"] { display:none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# 🏠 Contenido de la página de inicio
st.title(_t("home_title"))

st.write(
    _t("home_intro")
)

# Imagen portada (sin scroll)
img_path = Path("assets/portada.jpg")
img_url = (
    str(img_path)
    if img_path.exists()
    else "https://images.unsplash.com/photo-1509395176047-4a66953fd231?q=80&w=1920&auto=format&fit=crop"
)

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
    unsafe_allow_html=True,
)

st.caption(_t("home_caption"))
