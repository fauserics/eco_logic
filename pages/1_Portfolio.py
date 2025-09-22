import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# ---------- helpers ----------
def load_config():
    cfg_path = Path(__file__).parents[1] / "config" / "scoring_config.json"
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
        v = 1.0 if value in (True, 1, "1", "true", "TRUE", "yes", "YES") else 0.0
        return clamp01(v / target if target else v)
    try:
        v = float(value)
    except Exception:
        v = 0.0
    if typ in ("pct", "number"):
        return clamp01(v / float(target)) if float(target) != 0 else 0.0
    return clamp01(v)

def compute_total(row, scheme_cfg):
    weights = scheme_cfg["weights"]
    metrics = scheme_cfg["metrics"]
    cat_vals = {cat: [] for cat in weights.keys()}
    for key, meta in metrics.items():
        cat = meta["category"]
        val = row.get(key, 0)
        norm = normalize(val, meta)
        cat_vals.setdefault(cat, []).append(norm)
    cat_scores = {cat: (sum(vals) / len(vals) if vals else 0.0) for cat, vals in cat_vals.items()}
    return sum(cat_scores.get(cat, 0.0) * w for cat, w in weights.items()) * 100.0

# ---------- UI ----------
st.header("📊 Portfolio con Tipologías")
st.caption("Subí un CSV con tus proyectos y filtrá por **tipología**. El scoring es orientativo (demo).")

cfg = load_config()
schemes = list(cfg["schemes"].keys())
scheme = st.selectbox("Esquema de evaluación", options=schemes, index=0)
scheme_cfg = cfg["schemes"][scheme]
metrics = list(scheme_cfg["metrics"].keys())

with st.expander("📋 Columnas requeridas (además de `project_name` y opcional `typology`)", expanded=False):
    st.code(", ".join(["project_name", "typology (opcional)"] + metrics), language="text")

sample = Path(__file__).parents[1] / "data" / "sample_portfolio_with_typologies.csv"
if sample.exists():
    st.download_button("⬇️ Descargar plantilla con tipologías (CSV)", data=sample.read_bytes(),
                       file_name="sample_portfolio_with_typologies.csv")

file = st.file_uploader("Subir CSV de proyectos", type=["csv"])

if file:
    df = pd.read_csv(file)
    if "project_name" not in df.columns:
        st.error("El CSV debe incluir la columna `project_name`.")
        st.stop()
    if "typology" not in df.columns:
        df["typology"] = "Sin tipología"

    # Verificamos métricas que falten (solo advertimos)
    missing = [c for c in metrics if c not in df.columns]
    if missing:
        st.warning(f"Faltan métricas en el CSV: {', '.join(missing)}. Se considerarán en 0 para el cálculo.")

    # Garantizamos que todas las métricas existan (si no, las creamos con 0)
    for m in metrics:
        if m not in df.columns:
            df[m] = 0

    # Score
    df["score"] = df.apply(lambda r: compute_total(r, scheme_cfg), axis=1)

    # --------- Filtros elegantes ----------
    with st.sidebar:
        st.subheader("🎯 Filtros")
        typologies = sorted(df["typology"].astype(str).unique().tolist())
        pick = st.multiselect("Tipologías", options=typologies, default=typologies)
        q = st.text_input("Buscar por nombre de proyecto", "")
        min_score = st.slider("Score mínimo", min_value=0, max_value=100, value=0, step=1)

    view = df.copy()
    if pick:
        view = view[view["typology"].astype(str).isin(pick)]
    if q.strip():
        view = view[view["project_name"].astype(str).str.contains(q, case=False, na=False)]
    view = view[view["score"] >= min_score]

    # --------- KPIs ----------
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Proyectos", f"{len(view):,}")
    with c2:
        st.metric("Score promedio", f"{view['score'].mean():.1f}" if len(view) else "–")
    with c3:
        st.metric("Score máx.", f"{view['score'].max():.1f}" if len(view) else "–")
    with c4:
        st.metric("Tipologías activas", f"{view['typology'].nunique():,}")

    st.divider()

    # --------- Tabla ----------
    st.write("### Tabla de proyectos")
    st.dataframe(
        view[["project_name", "typology", "score"] + metrics].sort_values("score", ascending=False),
        hide_index=True, use_container_width=True
    )

    # --------- Gráficos ----------
    if len(view):
        st.write("### Score por proyecto")
        chart_projects = alt.Chart(view).mark_bar().encode(
            x=alt.X("score:Q", title="Score (0–100)"),
            y=alt.Y("project_name:N", sort="-x", title="Proyecto"),
            color=alt.Color("typology:N", title="Tipología"),
            tooltip=[
                alt.Tooltip("project_name:N", title="Proyecto"),
                alt.Tooltip("typology:N", title="Tipología"),
                alt.Tooltip("score:Q", title="Score", format=".1f")
            ]
        ).properties(height=400)
        st.altair_chart(chart_projects, use_container_width=True)

        st.write("### Promedio por tipología")
        avg_by_typ = (
            view.groupby("typology", as_index=False)["score"]
            .mean()
            .sort_values("score", ascending=False)
        )
        chart_typ = alt.Chart(avg_by_typ).mark_bar().encode(
            x=alt.X("score:Q", title="Score promedio"),
            y=alt.Y("typology:N", sort="-x", title="Tipología"),
            tooltip=[
                alt.Tooltip("typology:N", title="Tipología"),
                alt.Tooltip("score:Q", title="Score promedio", format=".1f")
            ]
        ).properties(height=300)
        st.altair_chart(chart_typ, use_container_width=True)

    # --------- Descargas ----------
    st.download_button("⬇️ Descargar resultados (CSV)", data=view.to_csv(index=False), file_name="portfolio_scores.csv")

else:
    st.info("Subí un CSV para comenzar. Podés usar la plantilla de ejemplo con tipologías.")
