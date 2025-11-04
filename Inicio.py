# Inicio.py
import os
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Inicio – GreenScore", page_icon="🌿", layout="wide")

# ---- Estilos de portada (discreto y moderno) ----
st.markdown("""
<style>
.hero {
  border-radius: 18px;
  padding: 28px;
  background: radial-gradient(1200px 500px at 0% 0%, rgba(11,140,107,0.18), transparent 60%),
              linear-gradient(180deg, rgba(6,18,22,0.70), rgba(6,18,22,0.55));
  color: #f1f5f9;
  border: 1px solid rgba(255,255,255,0.06);
}
.hero h1 { margin: 0 0 8px 0; font-size: 36px; line-height: 1.2; }
.hero p  { margin: 0; font-size: 16px; color: #cbd5e1; }
.kpis { display:flex; gap:20px; margin-top:16px; }
.kpi  { background: rgba(255,255,255,0.06); padding:12px 14px; border-radius:12px; }
.kpi b { font-size: 18px; color:#fff; }
.caption { color:#64748b; font-size: 13px; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# ---- Portada ----
st.markdown('<div class="hero">', unsafe_allow_html=True)
st.markdown("""
<h1>GreenScore</h1>
<p>Evaluación ambiental de edificios y portafolios con un enfoque práctico. 
La app integra scoring tipo LEED/EDGE, análisis por tipologías y el nuevo módulo de 
<b>Energy Management (ISO 50001)</b>, que permite:</p>
<ul>
<li>Registrar organización, sitio, línea de base y EnPIs.</li>
<li>Subir <b>fotos</b> (características, usos y tipologías) y <b>facturas/mediciones</b> (CSV/XLSX; PDF/imagen como evidencia).</li>
<li>Considerar <b>número de usuarios</b>, perfiles de ocupación y usos significativos de energía (SEUs).</li>
<li>Generar un <b>reporte institucional</b> con LLM de OpenAI (HTML descargable), estimando ahorros por medidas recomendadas y contemplando ISO 50001.</li>
</ul>
<div class="kpis">
  <div class="kpi"><b>LEED/EDGE</b><div class="caption">Scoring y ponderaciones</div></div>
  <div class="kpi"><b>Portfolio</b><div class="caption">Comparables por tipologías</div></div>
  <div class="kpi"><b>ISO 50001</b><div class="caption">Planificar · Implementar · M&V</div></div>
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ---- Imagen de alta calidad: usa assets/portada.jpg si existe; sino, fallback Unsplash ----
assets_path = Path("assets/portada.jpg")
if assets_path.exists():
    st.image(str(assets_path), use_container_width=True, caption=None)
else:
    # Fallback libre: imagen alusiva de arquitectura/energía
    st.image(
        "https://images.unsplash.com/photo-1509395176047-4a66953fd231?q=80&w=1920&auto=format&fit=crop",
        use_column_width=True
    )

# Nota de versión mínima, sin instrucciones de navegación
st.caption("© EcoLogic – GreenScore · Demo de preventa con módulo ISO 50001 y reporte LLM.")
