import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="GreenScore Prototype", page_icon="🌿", layout="wide")

# ---------------- fallbacks ----------------
DEFAULT_CFG = {
    "schemes": {
        "LEED": {
            "weights": {
                "Energy": 0.30, "Water": 0.20, "Materials": 0.15,
                "IEQ": 0.15, "Transport": 0.10, "Site": 0.05, "Innovation": 0.05
            },
            "metrics": {
                "energy_saving_pct": {"label":"Ahorro energético (%) vs. baseline","category":"Energy","type":"pct","target":30},
                "renewables_pct": {"label":"Energía renovable on-site (%)","category":"Energy","type":"pct","target":10},
                "water_saving_pct": {"label":"Ahorro de agua (%) vs. baseline","category":"Water","type":"pct","target":30},
                "recycled_content_pct": {"label":"Contenido reciclado de materiales (%)","category":"Materials","type":"pct","target":20},
                "daylight_areas_pct": {"label":"Áreas con luz natural (%)","category":"IEQ","type":"pct","target":75},
                "low_voc_pct": {"label":"Materiales de bajo VOC (%)","category":"IEQ","type":"pct","target":100},
                "near_transit": {"label":"Cercanía a transporte público (sí/no)","category":"Transport","type":"bool","target":1},
                "bike_parking": {"label":"Bicicleteros / duchas (sí/no)","category":"Transport","type":"bool","target":1},
                "green_roof_pct": {"label":"Cubierta verde / reflectiva (%)","category":"Site","type":"pct","target":50},
                "waste_recycled_pct": {"label":"Residuos de obra reciclados (%)","category":"Site","type":"pct","target":75},
                "innovation_points": {"label":"Puntos de innovación (0–5)","category":"Innovation","type":"number","min":0,"max":5,"target":5}
            }
        },
        "EDGE": {
            "weights": {"Energy": 0.45, "Water": 0.35, "Materials": 0.20},
            "metrics": {
                "energy_saving_pct": {"label":"Ahorro energético (%) vs. baseline","category":"Energy","type":"pct","target":20},
                "solar_ready": {"label":"Preparado para fotovoltaica (sí/no)","category":"Energy","type":"bool","target":1},
                "water_saving_pct": {"label":"Ahorro de agua (%) vs. baseline","category":"Water","type":"pct","target":20},
                "fixtures_efficiency_score": {"label":"Eficiencia de artefactos sanitarios (0–1)","category":"Water","type":"number","min":0,"max":1,"target":1},
                "embodied_carbon_reduction_pct": {"label":"Reducción de carbono incorporado (%)","category":"Materials","type":"pct","target":20},
                "local_materials_pct": {"label":"Materiales locales (%)","category":"Materials","type":"pct","target":25}
            }
        }
    }
}

DEFAULT_SAMPLE = pd.DataFrame([
    {"project_name":"Edificio A – Oficinas","typology":"Oficinas",
     "energy_saving_pct":25,"renewables_pct":5,"water_saving_pct":22,"recycled_content_pct":18,
     "daylight_areas_pct":70,"low_voc_pct":100,"near_transit":1,"bike_parking":1,
     "green_roof_pct":20,"waste_recycled_pct":60,"innovation_points":2.0,"solar_ready":1,
     "fixtures_efficiency_score":0.8,"embodied_carbon_reduction_pct":10,"local_materials_pct":30},
    {"project_name":"Torre C – Residencial","typology":"Residencial",
     "energy_saving_pct":35,"renewables_pct":12,"water_saving_pct":28,"recycled_content_pct":10,
     "daylight_areas_pct":50,"low_voc_pct":80,"near_transit":0,"bike_parking":0,
     "green_roof_pct":0,"waste_recycled_pct":40,"innovation_points":1.0,"solar_ready":0,
     "fixtures_efficiency_score":0.6,"embodied_carbon_reduction_pct":15,"local_materials_pct":20},
])

# ---------------- helpers ----------------
@st.cache_data
def load_config():
    cfg_path = Path("config/scoring_config.json")
    if cfg_path.exists():
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    return DEFAULT_CFG  # fallback

def clamp01(x: float) -> float:
    if x is None: return 0.0
    try: x = float(x)
    except: x = 0.0
    return max(0.0, min(1.0, x))

def normalize(value, meta):
    target = meta.get("target", 1)
    typ = meta.get("type", "number")
    if typ == "bool":
        v = 1.0 if bool(value) else 0.0
        return clamp01(v / target if target else v)
    try:
        v = float(value)
    except:
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
        metric_rows.append({"metric": key, "label": meta.get("label", key), "category": cat, "value": val, "normalized": norm})
    cat_scores = {cat: (sum(vals)/len(vals) if vals else 0.0) for cat, vals in cat_vals.items()}
    total = sum(cat_scores.get(cat, 0.0) * w for cat, w in weights.items()) * 100.0
    contribs = [{"Category": c, "Contribution": cat_scores.get(c,0.0)*w*100.0} for c, w in weights.items()]
    return total, pd.DataFrame(contribs), pd.DataFrame(metric_rows)

def label_tier(score: float):
    return ("Platinum (demo)" if score>=85 else
            "Gold (demo)" if score>=75 else
            "Silver (demo)" if score>=65 else
            "Bronze (demo)" if score>=50 else
            "Starter (demo)")

cfg = load_config()
schemes = list(cfg["schemes"].keys())

# ---------------- UI ----------------
st.title("🌿 GreenScore Prototype")
st.caption("Demo simplificada LEED / EDGE para prefactibilidad. No oficial.")

with st.sidebar:
    st.header("Ajustes")
    scheme = st.selectbox("Esquema", options=schemes, index=0)
    scheme_cfg = cfg["schemes"][scheme]
    st.subheader("Ponderaciones")
    st.dataframe(pd.DataFrame([scheme_cfg["weights"]]).T.rename(columns={0:"Peso"}).reset_index().rename(columns={"index":"Categoría"}),
                 hide_index=True, use_container_width=True)

tabs = st.tabs(["Proyecto individual", "Portfolio", "Metodología"])

# ---------- TAB 1: Proyecto individual (form robusto) ----------
with tabs[0]:
    st.subheader(f"Proyecto individual — {scheme}")
    metrics = scheme_cfg["metrics"]

    with st.form("single_project_form", clear_on_submit=False):
        st.write("Ingresá valores y luego presioná **Calcular score**.")
        cols = st.columns(2)
        inputs = {}

        for i, (key, meta) in enumerate(metrics.items()):
            col = cols[i % 2]
            label = meta.get("label", key)
            typ = meta.get("type", "number")
            with col:
                if typ == "bool":
                    inputs[key] = st.toggle(label, value=False)
                elif typ == "pct":
                    inputs[key] = st.slider(label, min_value=0, max_value=100, value=0, step=1)
                else:
                    mn = float(meta.get("min", 0.0))
                    mx = float(meta.get("max", 100.0))
                    step = 0.1 if (mx - mn) <= 5 else 1.0
                    inputs[key] = st.number_input(label, min_value=mn, max_value=mx, value=mn, step=step)

        submitted = st.form_submit_button("Calcular score", use_container_width=True)

    if submitted:
        total, contrib_df, metric_df = compute_scores(inputs, scheme_cfg)
        st.metric("Score total (0–100)", f"{total:.1f}")
        st.success(f"Clasificación demo: **{label_tier(total)}**")

        st.altair_chart(
            alt.Chart(contrib_df).mark_bar().encode(
                x=alt.X("Contribution:Q", title="Aporte al score"),
                y=alt.Y("Category:N", sort="-x", title="Categoría"),
                tooltip=["Category", alt.Tooltip("Contribution:Q", format=".1f")]
            ),
            use_container_width=True
        )

        metric_df["normalized"] = metric_df["normalized"].map(lambda v: f"{v:.2f}")
        st.write("Detalle de métricas normalizadas (0–1):")
        st.dataframe(
            metric_df[["label","category","value","normalized"]],
            hide_index=True, use_container_width=True
        )

# ---------- TAB 2: Portfolio ----------
with tabs[1]:
    st.subheader("Portfolio con tipologías")
    st.write("Subí un CSV con `project_name`, `typology` (opcional) y las métricas del esquema.")
    sample_path = Path("data/sample_portfolio_with_typologies.csv")
    if sample_path.exists():
        st.download_button("⬇️ Descargar plantilla (CSV)", data=sample_path.read_bytes(),
                           file_name="sample_portfolio_with_typologies.csv")
    else:
        st.download_button("⬇️ Descargar plantilla (CSV)", data=DEFAULT_SAMPLE.to_csv(index=False).encode("utf-8"),
                           file_name="sample_portfolio_with_typologies.csv")

    file = st.file_uploader("Subir CSV", type=["csv"])
    if file:
        try:
            df = pd.read_csv(file)
        except Exception:
            df = pd.read_csv(file, encoding="utf-8", errors="ignore")
    else:
        df = DEFAULT_SAMPLE.copy()

    if "project_name" not in df.columns:
        st.error("El CSV debe incluir la columna `project_name`.")
    else:
        if "typology" not in df.columns:
            df["typology"] = "Sin tipología"
        metrics = list(scheme_cfg["metrics"].keys())
        missing = [m for m in metrics if m not in df.columns]
        if missing:
            st.warning(f"Faltan métricas: {', '.join(missing)}. Se consideran 0 para el cálculo.")
            for m in missing:
                df[m] = 0

        def score_row(r):
            # compute_scores espera dict con claves de métricas
            inputs = {k: r.get(k, 0) for k in metrics}
            return compute_scores(inputs, scheme_cfg)[0]

        df["score"] = df.apply(score_row, axis=1)

        with st.sidebar:
            st.subheader("Filtros de portfolio")
            tps = sorted(df["typology"].astype(str).unique().tolist())
            filt_tp = st.multiselect("Tipologías", options=tps, default=tps, key="tps")
            q = st.text_input("Buscar proyecto", "", key="q")
            min_score = st.slider("Score mínimo", 0, 100, 0, 1, key="minsc")

        view = df.copy()
        if filt_tp: view = view[view["typology"].astype(str).isin(filt_tp)]
        if q.strip(): view = view[view["project_name"].astype(str).str.contains(q, case=False, na=False)]
        view = view[view["score"] >= min_score]

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Proyectos", f"{len(view):,}")
        with c2: st.metric("Promedio", f"{view['score'].mean():.1f}" if len(view) else "–")
        with c3: st.metric("Máximo", f"{view['score'].max():.1f}" if len(view) else "–")
        with c4: st.metric("Tipologías", f"{view['typology'].nunique():,}")

        st.dataframe(view[["project_name","typology","score"] + metrics].sort_values("score", ascending=False),
                     hide_index=True, use_container_width=True)

        if len(view):
            st.altair_chart(
                alt.Chart(view).mark_bar().encode(
                    x=alt.X("score:Q", title="Score"),
                    y=alt.Y("project_name:N", sort="-x", title="Proyecto"),
                    color=alt.Color("typology:N", title="Tipología"),
                    tooltip=[alt.Tooltip("project_name:N"), alt.Tooltip("typology:N"),
                             alt.Tooltip("score:Q", format=".1f")]
                ).properties(height=420),
                use_container_width=True
            )
            by_tp = view.groupby("typology", as_index=False)["score"].mean().sort_values("score", ascending=False)
            st.altair_chart(
                alt.Chart(by_tp).mark_bar().encode(
                    x=alt.X("score:Q", title="Promedio por tipología"),
                    y=alt.Y("typology:N", sort="-x", title="Tipología"),
                    tooltip=[alt.Tooltip("typology:N"), alt.Tooltip("score:Q", format=".1f")]
                ).properties(height=320),
                use_container_width=True
            )

        st.download_button("⬇️ Descargar resultados (CSV)", data=view.to_csv(index=False), file_name="portfolio_scores.csv")

# ---------- TAB 3: Metodología ----------
with tabs[2]:
    st.subheader("Metodología (demo)")
    st.markdown("""
1) **Normalización** de métricas: `valor / target` → truncado a [0, 1].  
2) **Score de categoría** = promedio de métricas normalizadas.  
3) **Score total** = suma **ponderada** de categorías × 100.  
4) Clasificación demo: Starter / Bronze / Silver / Gold / Platinum.
    """)
    st.markdown("**Pesos actuales:**")
    st.dataframe(pd.DataFrame([scheme_cfg["weights"]]).T.rename(columns={0:"Peso"}).reset_index().rename(columns={"index":"Categoría"}),
                 hide_index=True, use_container_width=True)
    st.markdown("**Métricas activas:**")
    rows = []
    for key, meta in scheme_cfg["metrics"].items():
        rows.append({"Clave": key, "Etiqueta": meta.get("label", key),
                     "Categoría": meta.get("category",""), "Tipo": meta.get("type",""),
                     "Target": meta.get("target","")})
    st.dataframe(pd.DataFrame(rows).sort_values(["Categoría","Etiqueta"]), hide_index=True, use_container_width=True)

st.caption("© EcoLogic – Prototipo orientado a preventa LEED/EDGE.")
