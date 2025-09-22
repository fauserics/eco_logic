import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="GreenScore Prototype",
    page_icon="🌿",
    layout="wide",
)

# ---------- helpers ----------
def load_config():
    cfg_path = Path(__file__).parent / "config" / "scoring_config.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

def clamp01(x: float) -> float:
    if x is None:
        return 0.0
    return max(0.0, min(1.0, float(x)))

def normalize(value, meta):
    target = meta.get("target", 1)
    typ = meta.get("type", "number")
    if typ == "bool":
        v = 1.0 if value else 0.0
        return clamp01(v / target if target else v)
    try:
        v = float(value)
    except Exception:
        v = 0.0
    if typ in ("pct", "number"):
        return clamp01(v / float(target)) if float(target) != 0 else 0.0
    return clamp01(v)

def compute_scores(inputs: dict, scheme_cfg: dict):
    weights = scheme_cfg["weights"]
    metrics = scheme_cfg["metrics"]
    cat_vals = {cat: [] for cat in weights.keys()}
    metric_rows = []

    for key, meta in metrics.items():
        cat = meta["category"]
        val = inputs.get(key, 0)
        norm = normalize(val, meta)
        cat_vals.setdefault(cat, []).append(norm)
        metric_rows.append({
            "metric": key,
            "label": meta.get("label", key),
            "category": cat,
            "value": val,
            "normalized": norm,
        })

    cat_scores = {
        cat: (sum(vals) / len(vals) if vals else 0.0) for cat, vals in cat_vals.items()
    }
    total = sum(cat_scores.get(cat, 0.0) * w for cat, w in weights.items()) * 100.0

    contribs = [
        {"Category": cat, "Contribution": cat_scores.get(cat, 0.0) * w * 100.0}
        for cat, w in weights.items()
    ]
    return total, pd.DataFrame(contribs), pd.DataFrame(metric_rows)

def label_tier(score: float):
    if score >= 85:
        return "Platinum (demo)"
    if score >= 75:
        return "Gold (demo)"
    if score >= 65:
        return "Silver (demo)"
    if score >= 50:
        return "Bronze (demo)"
    return "Starter (demo)"

# ---------- UI ----------
cfg = load_config()
schemes = list(cfg["schemes"].keys())

st.title("🌿 GreenScore Prototype")
st.caption("Demo simplificada de score ambiental para proyectos (LEED / EDGE). No oficial.")

with st.sidebar:
    st.image("https://raw.githubusercontent.com/streamlit/brand/main/logos/mark/streamlit-mark-color.png", width=60)
    st.header("Configuración")
    scheme = st.selectbox("Esquema de certificación", options=schemes, index=0)
    scheme_cfg = cfg["schemes"][scheme]

    st.markdown("**Ponderaciones**")
    wdf = pd.DataFrame([scheme_cfg["weights"]]).T.reset_index()
    wdf.columns = ["Categoría", "Peso"]
    st.dataframe(wdf, hide_index=True, use_container_width=True)

st.subheader(f"Evaluación rápida — {scheme}")
st.write("Ingresá valores estimativos para obtener un score orientativo:")

metrics = scheme_cfg["metrics"]
cols = st.columns(2)
inputs = {}

for i, (key, meta) in enumerate(metrics.items()):
    col = cols[i % 2]
    with col:
        typ = meta.get("type", "number")
        label = meta.get("label", key)
        if typ == "bool":
            inputs
