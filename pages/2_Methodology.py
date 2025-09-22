import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.header("🧭 Metodología")
st.caption("Documento de referencia del prototipo. No sustituye la evaluación oficial LEED/EDGE por profesionales acreditados.")

# ---------------- helpers ----------------
def load_config():
    cfg_path = Path(__file__).parents[1] / "config" / "scoring_config.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_weights_table(scheme_cfg: dict) -> pd.DataFrame:
    w = scheme_cfg.get("weights", {})
    df = pd.DataFrame([w]).T.reset_index()
    df.columns = ["Categoría", "Peso"]
    df["Peso (%)"] = (df["Peso"] * 100).round(1)
    return df[["Categoría", "Peso", "Peso (%)"]].sort_values("Peso", ascending=False)

def build_metrics_table(scheme_cfg: dict) -> pd.DataFrame:
    rows = []
    for key, meta in scheme_cfg.get("metrics", {}).items():
        rows.append({
            "Clave": key,
            "Etiqueta": meta.get("label", key),
            "Categoría": meta.get("category", ""),
            "Tipo": meta.get("type", ""),
            "Meta/Target": meta.get("target", ""),
            "Rango (min–max)": f"{meta.get('min','')}{'–'+str(meta.get('max')) if 'max' in meta else ''}",
        })
    df = pd.DataFrame(rows)
    # Ordenamos por categoría y por etiqueta para lectura más cómoda
    return df.sort_values(["Categoría", "Etiqueta"]).reset_index(drop=True)

cfg = load_config()
schemes = list(cfg.get("schemes", {}).keys())
scheme = st.selectbox("Esquema de referencia", options=schemes, index=0)
scheme_cfg = cfg["schemes"][scheme]

st.markdown("### 1) Objetivo")
st.write(
    """
Este prototipo estima un **score ambiental (0–100)** de prefactibilidad para apoyar **decisiones tempranas** y priorización de **oportunidades**.
Integra conceptualmente **LEED** y **EDGE** con un set **simplificado de métricas** y **pesos por categoría**.
"""
)

st.markdown("### 2) Cómo se calcula el score")
st.write(
    """
1. Cada **métrica** se **normaliza** contra su **meta** (`valor / target`), truncada a **[0, 1]**.
2. Cada **categoría** promedia sus métricas normalizadas → **score de categoría** ∈ [0, 1].
3. El **score total** es la **suma ponderada** de los scores de categoría → **0 a 100**.
4. Se asigna una **etiqueta demo** (Starter/Bronze/Silver/Gold/Platinum) a modo orientativo.
"""
)

st.markdown("### 3) Pesos por categoría")
wdf = build_weights_table(scheme_cfg)
st.dataframe(wdf, hide_index=True, use_container_width=True)

st.markdown("### 4) Métricas activas en el esquema")
mdf = build_metrics_table(scheme_cfg)
st.dataframe(mdf, hide_index=True, use_container_width=True)

with st.expander("🔎 Interpretación práctica de las métricas"):
    st.write(
        """
- **Energy**: ahorro energético vs. baseline, renovables on-site / ready.
- **Water**: ahorro de agua vs. baseline, eficiencia de artefactos.
- **Materials**: % contenido reciclado, reducción de carbono incorporado, materiales locales.
- **IEQ (Indoor Environmental Quality)**: luz natural, materiales bajo VOC.
- **Transport**: cercanía a transporte público, bicicleteros/duchas.
- **Site**: cubierta verde/reflectiva, reciclado de residuos de obra.
- **Innovation**: puntos por innovaciones relevantes al caso.
"""
    )

st.markdown("### 5) Supuestos y límites (demo)")
st.info(
    """
- **No es una certificación oficial.** Es un **indicador temprano** para conversaciones con cliente.
- **Metas/targets** y **pesos** son **aproximaciones**; deben **calibrarse** por **tipología** y **ubicación**.
- No calcula cargas térmicas/energéticas con modelos completos (p.ej., **ASHRAE/DOE2**); usa **inputs simplificados**.
- No evalúa **pre-requisitos** ni **créditos obligatorios**; puede añadirse en versiones siguientes.
"""
)

st.markdown("### 6) Buenas prácticas de uso comercial")
st.write(
    """
- Empezá con **valores conservadores** y mostrá la **sensibilidad** del score a 2–3 decisiones tempranas (envolvente, HVAC, agua).
- Presentá **2 escenarios** por proyecto (base vs. eficiente) para mostrar **brechas** y trazar **hoja de ruta**.
- Usá la página **Portfolio** para priorizar **qué proyectos** atacar primero y justificar impactos.
"""
)

st.markdown("### 7) Roadmap propuesto")
st.write(
    """
- **Tipologías**: duplicar esquemas (LEED_Oficinas, EDGE_Residencial, Hospitalidad, Retail).
- **Pre-requisitos**: checklist y bloqueo de score si faltan.
- **Cálculo energético**: enlace a motores/planillas (p.ej., EnergyPlus u hojas ASHRAE).
- **IFC/BIM**: lectura de superficies/uso/EE para precargar métricas.
- **Reportes**: exportar PDF con branding y narrativa ejecutiva.
- **Datos externos**: factores de carbono por país/material, clima, transporte.
"""
)

st.caption("© EcoLogic – Metodología de prototipo orientada a preventa. Ajustable por cliente, tipología y estándar.")
