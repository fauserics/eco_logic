import json
import re
from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st

# ========================= CONFIG / DEFAULTS =========================

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

@st.cache_data
def load_config():
    cfg_path = Path("config/scoring_config.json")
    if cfg_path.exists():
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    return DEFAULT_CFG

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

# ========================= UTILIDADES REPORTE / PDF =========================

def _slugify(text: str) -> str:
    t = re.sub(r"[^a-zA-Z0-9\s\-_/]", "", text or "")
    t = re.sub(r"\s+", "-", t.strip())
    return t.lower()[:80] or "sec"

def _markdownish_to_html_and_toc(llm_text: str):
    """Convierte texto plano del LLM en HTML simple con <h2>/<h3> y genera TOC dinámico."""
    lines = (llm_text or "").splitlines()
    body_parts, toc = [], []
    # Patrones típicos de secciones ISO 50001
    section_keys = [
        "Resumen Ejecutivo", "Alcance", "Contexto", "Revisión Energética",
        "Línea de Base", "EnPIs", "Oportunidades", "Medidas", "Ahorros",
        "Plan de Implementación", "Monitoreo", "Verificación", "M&V",
        "Riesgos", "Recomendaciones", "Conclusiones"
    ]
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        # Detectar encabezados tipo "##", "###" o líneas cortas en Title Case / incluidas en claves
        if line.startswith("### "):
            title = line[4:].strip()
            sid = _slugify(title)
            toc.append(("h3", title, sid))
            body_parts.append(f'<h3 id="{sid}">{title}</h3>')
        elif line.startswith("## "):
            title = line[3:].strip()
            sid = _slugify(title)
            toc.append(("h2", title, sid))
            body_parts.append(f'<h2 id="{sid}">{title}</h2>')
        elif any(k.lower() in line.lower() for k in section_keys) and len(line) < 80:
            title = line
            sid = _slugify(title)
            toc.append(("h2", title, sid))
            body_parts.append(f'<h2 id="{sid}">{title}</h2>')
        else:
            body_parts.append(f"<p>{line}</p>")
    html_body = "\n".join(body_parts) if body_parts else f"<p>{llm_text or ''}</p>"
    return html_body, toc

def _em_download_button_html(html: str, filename: str, label: str = "Descargar reporte (HTML)"):
    import base64
    b64 = base64.b64encode(html.encode("utf-8")).decode()
    href = f'<a download="{filename}" href="data:text/html;base64,{b64}">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)

# ---------- HTML de vista previa (fondo blanco) ----------
def _em_render_report_html(org: str, site: str, generated_at: str, llm_text: str,
                           brand_color: str, logo_url: str) -> str:
    body_html, _ = _markdownish_to_html_and_toc(llm_text)
    style = f"""
    <style>
      :root {{ --brand: {brand_color or '#0B8C6B'}; }}
      html, body {{ background:#fff !important; color:#1b1f24; margin:0; padding:0; }}
      body {{ font-family: Inter, system-ui, Segoe UI, Roboto, Arial, sans-serif; }}
      .page {{ background:#fff; padding:24px; }}
      .header {{ display:flex; align-items:center; gap:16px; border-bottom:3px solid var(--brand); padding-bottom:12px; margin-bottom:24px; }}
      .badge {{ background: var(--brand); color:#fff; padding:4px 10px; border-radius:999px; font-size:12px; margin-left:auto; }}
      .meta {{ color:#667085; font-size:12px; }}
      .section h2 {{ color: var(--brand); border-bottom:1px solid #eaecef; padding-bottom:6px; }}
      .prose p {{ line-height:1.6; }}
    </style>
    """
    logo_html = f'<img src="{logo_url}" alt="Logo" height="42"/>' if logo_url else ""
    body = f"""
    <div class="page">
      <div class="header">
        {logo_html}
        <div>
          <h1>Reporte de Gestión de la Energía (ISO 50001)</h1>
          <div class="meta">{org} – {site} · Generado: {generated_at}</div>
        </div>
        <span class="badge">Green&nbsp;Score</span>
      </div>
      <div class="section prose">
        {body_html}
      </div>
    </div>
    """
    return f"<!doctype html><html lang='es'><head><meta charset='utf-8'/><meta name='viewport' content='width=device-width,initial-scale=1'/><title>Reporte Energético – {org} / {site}</title>{style}</head><body>{body}</body></html>"

# ---------- HTML para PDF (portada + índice + cuerpo, A4, marca de agua, paginado) ----------
def _em_render_report_pdf_html(org: str, site: str, generated_at: str, llm_text: str,
                               brand_color: str, logo_url: str) -> str:
    body_html, toc = _markdownish_to_html_and_toc(llm_text)

    # Construir índice dinámico
    if toc:
        toc_items = []
        for level, title, sid in toc:
            indent = "0" if level == "h2" else "12"
            toc_items.append(f'<div style="margin-left:{indent}pt;">• <a href="#{sid}">{title}</a></div>')
        toc_html = "<h2>Índice</h2>" + "\n".join(toc_items)
    else:
        toc_html = "<h2>Índice</h2><p>(No se detectaron encabezados en el texto del informe)</p>"

    logo_img = f"<img src='{logo_url}' alt='Logo' style='height:64pt;vertical-align:middle;margin-right:10pt;'/>" if logo_url else ""
    # CSS para xhtml2pdf (A4 + footer con numeración + watermark)
    style = f"""
    <style>
      @page {{
        size: A4;
        margin: 2cm;
        @bottom-right {{
          content: "Página " counter(page) " de " counter(pages);
          font-size: 9pt;
          color: #555;
        }}
      }}
      body {{ background:#fff; color:#111; font-family: DejaVu Sans, Arial, sans-serif; font-size:12pt; }}
      h1 {{ color:{brand_color or '#0B8C6B'}; font-size:22pt; margin:0 0 6pt 0; }}
      h2 {{ color:{brand_color or '#0B8C6B'}; font-size:15pt; border-bottom:1px solid #ccc; padding-bottom:2pt; margin-top:14pt; }}
      h3 {{ color:#222; font-size:12.5pt; margin-top:10pt; }}
      p  {{ line-height:1.4; margin:0 0 8pt 0; }}
      a  {{ color:{brand_color or '#0B8C6B'}; text-decoration:none; }}
      .cover {{ text-align:center; padding-top:120pt; }}
      .cover .title {{ font-size:28pt; color:{brand_color or '#0B8C6B'}; margin-top:10pt; }}
      .meta {{ color:#555; font-size:11pt; margin-top:6pt; }}
      .watermark {{
        position: fixed; top: 35%; left: 10%;
        transform: rotate(-20deg);
        font-size: 72pt; color: #e6f2ef;  /* claro = marca de agua */
        z-index: 0;
      }}
      .section {{ position: relative; z-index: 1; }}
      .badge {{ float:right; background:{brand_color or '#0B8C6B'}; color:#fff; padding:2pt 6pt; border-radius:12pt; font-size:9pt; }}
      .headerline {{ border-bottom:2pt solid {brand_color or '#0B8C6B'}; padding-bottom:6pt; margin-bottom:12pt; }}
    </style>
    """

    # Portada (sin resumen)
    cover = f"""
    <div class="watermark">GreenScore</div>
    <div class="cover">
      {logo_img}
      <div class="title">Reporte de Gestión de la Energía (ISO 50001)</div>
      <div class="meta" style="margin-top:18pt;">{org} – {site}</div>
      <div class="meta">Generado: {generated_at}</div>
      <div class="meta" style="margin-top:24pt;"><span class="badge">Green&nbsp;Score</span></div>
    </div>
    <pdf:nextpage/>
    """

    # Índice
    toc_page = f"""
    <div class="section">
      <div class="headerline"><h1>Contenido</h1></div>
      {toc_html}
    </div>
    <pdf:nextpage/>
    """

    # Cuerpo
    body = f"""
    <div class="section">
      <div class="headerline"><h1>Informe</h1></div>
      {body_html}
    </div>
    """

    return f"<!doctype html><html><head><meta charset='utf-8'/>{style}</head><body>{cover}{toc_page}{body}</body></html>"

def _em_html_to_pdf_bytes(html: str) -> bytes:
    """Convierte HTML a PDF (bytes) con xhtml2pdf (CSS simple)."""
    from io import BytesIO
    from xhtml2pdf import pisa
    out = BytesIO()
    if not html.lower().strip().startswith("<!doctype"):
        html = "<!doctype html><html><head><meta charset='utf-8'></head><body>" + html + "</body></html>"
    pisa.CreatePDF(src=html, dest=out, encoding="utf-8")
    return out.getvalue()

# ========================= OPENAI (reporte) =========================

def _em_openai_report(dataset: dict, brand_color: str, logo_url: str,
                      model: str = "gpt-4o-mini", detail_level: int = 3,
                      temperature: float = 0.2) -> str:
    """
    Genera el cuerpo del reporte ISO 50001 con OpenAI.
    - model: "gpt-4o-mini" (rápido/económico) o "gpt-4o"
    - detail_level: 1..5 (1 = muy sintético, 5 = muy técnico)
    - temperature: 0.0..1.0
    """
    import os, json as _json
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return ("AVISO: Falta OPENAI_API_KEY en Secrets/entorno. "
                    "Configúrala para generar el reporte automáticamente.")
        client = OpenAI(api_key=api_key)

        depth_map = {
            1: "Resumen ejecutivo muy sintético, no exceder 300 palabras.",
            2: "Resumen breve + hallazgos clave (≈500 palabras).",
            3: "Informe estándar con secciones completas y cifras básicas (≈900 palabras).",
            4: "Informe amplio con justificación técnica y tablas en texto (≈1400 palabras).",
            5: "Informe técnico exhaustivo, supuestos, riesgos, fórmulas simples y M&V detallada (≈2000 palabras)."
        }
        guidance = depth_map.get(int(detail_level), depth_map[3])

        system = (
            "Eres consultor sénior en gestión de la energía bajo ISO 50001. "
            "Redacta un informe institucional en español con tono profesional y claro, "
            "incluyendo estas secciones (con encabezados explícitos): "
            "Resumen Ejecutivo; Alcance y Contexto; Revisión Energética; "
            "Línea de Base y EnPIs; Oportunidades y Medidas; "
            "Estimación de Ahorros (kWh/año, %, costo, payback simple); "
            "Plan de Implementación; Monitoreo y Verificación (M&V); "
            "Riesgos y Recomendaciones."
        )
        user = (
            f"PARÁMETROS DE REDACCIÓN: {guidance}\n\n"
            f"DATOS (JSON):\n{_json.dumps(dataset, ensure_ascii=False)}"
        )

        out = client.chat.completions.create(
            model=model,
            temperature=float(temperature),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        )
        return out.choices[0].message.content
    except Exception as e:
        return (f"AVISO: No fue posible llamar a OpenAI ({e}). "
                "Revisá el modelo, la versión del SDK y la clave.")

# ========================= PÁGINAS =========================

def page_proyecto_individual():
    cfg = load_config()
    SCHEMES = list(cfg["schemes"].keys())

    st.subheader("Proyecto individual")
    with st.expander("⚙️ Ajustes generales del esquema", expanded=True):
        scheme = st.selectbox("Esquema", options=SCHEMES, index=0, key="pi_scheme")
        scheme_cfg = cfg["schemes"][scheme]
        st.dataframe(
            pd.DataFrame([scheme_cfg["weights"]]).T.rename(columns={0:"Peso"})
            .reset_index().rename(columns={"index":"Categoría"}),
            hide_index=True, use_container_width=True
        )

    metrics = cfg["schemes"][st.session_state.get("pi_scheme", SCHEMES[0])]["metrics"]

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
        scheme_cfg = cfg["schemes"][st.session_state.get("pi_scheme", SCHEMES[0])]
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
        st.dataframe(metric_df[["label","category","value","normalized"]],
                     hide_index=True, use_container_width=True)

def page_portfolio():
    cfg = load_config()
    SCHEMES = list(cfg["schemes"].keys())
    st.subheader("Portfolio con tipologías")

    scheme = st.selectbox("Esquema del cálculo para el portfolio", options=SCHEMES, index=0, key="pf_scheme")
    scheme_cfg = cfg["schemes"][scheme]

    st.write("Subí un CSV con `project_name`, `typology` (opcional) y las métricas del esquema.")
    sample_path = Path("data/sample_portfolio_with_typologies.csv")
    if sample_path.exists():
        st.download_button("⬇️ Descargar plantilla (CSV)", data=sample_path.read_bytes(),
                           file_name="sample_portfolio_with_typologies.csv")
    else:
        from io import BytesIO
        buf = BytesIO()
        DEFAULT_SAMPLE.to_csv(buf, index=False)
        st.download_button("⬇️ Descargar plantilla (CSV)", data=buf.getvalue(),
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
        return

    if "typology" not in df.columns:
        df["typology"] = "Sin tipología"
    metrics = list(scheme_cfg["metrics"].keys())
    missing = [m for m in metrics if m not in df.columns]
    if missing:
        st.warning(f"Faltan métricas: {', '.join(missing)}. Se consideran 0.")
        for m in missing:
            df[m] = 0

    def score_row(r):
        inputs = {k: r.get(k, 0) for k in metrics}
        return compute_scores(inputs, scheme_cfg)[0]

    df["score"] = df.apply(score_row, axis=1)

    with st.expander("Filtros", expanded=True):
        tps = sorted(df["typology"].astype(str).unique().tolist())
        filt_tp = st.multiselect("Tipologías", options=tps, default=tps, key="pf_tps")
        q = st.text_input("Buscar proyecto", "", key="pf_q")
        min_score = st.slider("Score mínimo", 0, 100, 0, 1, key="pf_minsc")

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
        by_tp = view.groupby("typology", as_index=False)["score"].mean().sort_values("score", descending=False)
        st.altair_chart(
            alt.Chart(by_tp).mark_bar().encode(
                x=alt.X("score:Q", title="Promedio por tipología"),
                y=alt.Y("typology:N", sort="-x", title="Tipología"),
                tooltip=[alt.Tooltip("typology:N"), alt.Tooltip("score:Q", format=".1f")]
            ).properties(height=320),
            use_container_width=True
        )

    st.download_button("⬇️ Descargar resultados (CSV)", data=view.to_csv(index=False), file_name="portfolio_scores.csv")

def page_metodologia():
    cfg = load_config()
    SCHEMES = list(cfg["schemes"].keys())

    st.subheader("Metodología (demo)")
    scheme = st.selectbox("Esquema a visualizar", options=SCHEMES, index=0, key="me_scheme")
    scheme_cfg = cfg["schemes"][scheme]

    st.markdown("""
1) **Normalización**: `valor / target` truncado a [0, 1].  
2) **Score de categoría** = promedio de métricas normalizadas.  
3) **Score total** = suma ponderada de categorías × 100.  
4) Clasificación demo: Starter / Bronze / Silver / Gold / Platinum.
    """)
    st.dataframe(
        pd.DataFrame([scheme_cfg["weights"]]).T.rename(columns={0:"Peso"})
        .reset_index().rename(columns={"index":"Categoría"}),
        hide_index=True, use_container_width=True
    )
    rows = []
    for key, meta in scheme_cfg["metrics"].items():
        rows.append({"Clave": key, "Etiqueta": meta.get("label", key),
                     "Categoría": meta.get("category",""), "Tipo": meta.get("type",""),
                     "Target": meta.get("target","")})
    st.dataframe(pd.DataFrame(rows).sort_values(["Categoría","Etiqueta"]),
                 hide_index=True, use_container_width=True)

def page_energy_management():
    st.subheader("ISO 50001 – Energy Management")

    col1, col2, col3 = st.columns([2, 2, 1])
    org = col1.text_input("Organización", placeholder="Fauser ICS", key="em_org")
    site = col2.text_input("Sitio/Edificio", placeholder="HQ – Quilmes", key="em_site")
    users_count = col3.number_input("Nº usuarios", min_value=0, value=0, step=1, key="em_users")

    col4, col5 = st.columns(2)
    address = col4.text_input("Dirección", placeholder="Calle, Ciudad, País", key="em_addr")
    climate_zone = col5.text_input("Zona climática", placeholder="ASHRAE/IRAM…", key="em_zone")

    col6, col7 = st.columns(2)
    baseline_start = col6.date_input("Baseline desde", value=None, key="em_bstart")
    baseline_end = col7.date_input("Baseline hasta", value=None, key="em_bend")

    st.markdown("**Usos significativos de energía (SEUs) y tipologías**")
    seus = st.text_area("SEUs (uno por línea)", "HVAC\nIluminación\nProcesos\nTI/Datacenter", key="em_seus")
    enpis = st.text_area("EnPIs candidatos (uno por línea)", "kWh/m2\nkWh/usuario\nEUI\nFactor de carga", key="em_enpis")

    st.markdown("**Perfiles de uso**")
    uses_df = st.data_editor(
        pd.DataFrame([{"tipología":"Oficinas","area_m2":1000,"horas_operación_semana":50}]),
        num_rows="dynamic", use_container_width=True, key="em_uses_df"
    )

    occ_col1, occ_col2 = st.columns(2)
    peak_occupancy = int(occ_col1.number_input("Ocupación pico", 0, 1_000_000, 0, key="em_peak"))
    occupancy_pattern = occ_col2.text_input("Patrón de ocupación", "L–V 9–18, sáb reducido", key="em_occpat")

    st.markdown("**Evidencias**")
    photos = st.file_uploader("Fotos (PNG/JPG)", type=["png","jpg","jpeg"], accept_multiple_files=True, key="em_photos")
    invoices = st.file_uploader("Facturas/mediciones (CSV/XLSX preferido; PDF/IMG como evidencia)",
                                type=["csv","xlsx","xls","pdf","png","jpg","jpeg"], accept_multiple_files=True, key="em_invoices")

    st.markdown("**Política energética, objetivos y plan**")
    energy_policy = st.text_area("Política energética (borrador)", key="em_policy")
    objectives = st.text_area("Objetivos/Metas (uno por línea)", "Reducir EUI 10% en 12 meses\nPF ≥ 0.97", key="em_objs")
    action_plan = st.text_area("Plan de acción (uno por línea)", "LED\nOptimización consignas HVAC\nMantenimiento VFD", key="em_plan")

    # ---- Generar y guardar dataset
    if "em_last_dataset" not in st.session_state:
        st.session_state["em_last_dataset"] = None

    if st.button("Guardar dataset del sitio (memoria de sesión)", key="em_save"):
        inv_df, saved_files = _em_parse_invoices(invoices)
        dataset = {
            "site": {
                "organization": org or "Org",
                "site_name": site or "Site",
                "address": address,
                "climate_zone": climate_zone,
                "baseline_start": str(baseline_start) if baseline_start else None,
                "baseline_end": str(baseline_end) if baseline_end else None,
                "energy_policy": energy_policy,
                "significant_energy_uses": [s.strip() for s in (seus or "").splitlines() if s.strip()],
                "enpis": [s.strip() for s in (enpis or "").splitlines() if s.strip()],
                "objectives": [s.strip() for s in (objectives or "").splitlines() if s.strip()],
                "action_plan": [s.strip() for s in (action_plan or "").splitlines() if s.strip()],
            },
            "users_profile": {
                "users_count": users_count,
                "peak_occupancy": peak_occupancy,
                "occupancy_pattern": occupancy_pattern,
            },
            "building_uses": uses_df.to_dict("records"),
            "evidence_files": [getattr(p, "name", str(p)) for p in (photos or [])] + saved_files,
            "invoices_preview": inv_df.head(100).to_dict(orient="records") if 'inv_df' in locals() and not inv_df.empty else [],
        }
        st.session_state["em_last_dataset"] = dataset
        st.success("Dataset guardado en memoria de sesión.")
        if 'inv_df' in locals() and not inv_df.empty:
            st.dataframe(pd.DataFrame(st.session_state["em_last_dataset"]["invoices_preview"]).head(50),
                         use_container_width=True)

    # ---- Parámetros de reporte LLM + branding
    st.markdown("----")
    st.markdown("#### Generar reporte con OpenAI")

    colm1, colm2, colm3 = st.columns([2, 1, 1])
    with colm1:
        model = st.selectbox(
            "Modelo OpenAI",
            options=["gpt-4o-mini", "gpt-4o"],
            index=0,
            help="Elegí el LLM. 4o-mini es rápido y económico; 4o ofrece mayor calidad."
        )
    with colm2:
        detail_level = st.slider(
            "Nivel de detalle",
            min_value=1, max_value=5, value=3, step=1,
            help="1 = muy sintético ··· 5 = muy técnico/exhaustivo"
        )
    with colm3:
        temperature = st.slider(
            "Creatividad (temp.)",
            min_value=0.0, max_value=1.0, value=0.2, step=0.1,
            help="0.0 = determinista · 1.0 = más creativo"
        )

    brand_color = st.color_picker("Color institucional", "#0B8C6B", key="em_color")
    logo_url = st.text_input("Logo (URL pública opcional)", key="em_logo")

    if st.button("Generar reporte ISO 50001", key="em_report"):
        dataset = st.session_state.get("em_last_dataset")
        if not dataset:
            st.error("No hay dataset guardado para generar el reporte.")
        else:
            st.info(f"Generando reporte con **{model}** · detalle **{detail_level}/5** · temp **{temperature:.1f}**…")
            llm_text = _em_openai_report(
                dataset=dataset,
                brand_color=brand_color,
                logo_url=logo_url,
                model=model,
                detail_level=detail_level,
                temperature=temperature,
            )
            # HTML para vista previa (fondo blanco)
            html = _em_render_report_html(
                org=dataset["site"]["organization"],
                site=dataset["site"]["site_name"],
                generated_at=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                llm_text=llm_text,
                brand_color=brand_color,
                logo_url=logo_url
            )
            _em_download_button_html(html, "energy_report.html")
            st.markdown("Vista previa:")
            st.components.v1.html(html, height=800, scrolling=True)

            # HTML para PDF (portada + índice + cuerpo + watermark + numeración)
            pdf_html = _em_render_report_pdf_html(
                org=dataset["site"]["organization"],
                site=dataset["site"]["site_name"],
                generated_at=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                llm_text=llm_text,
                brand_color=brand_color,
                logo_url=logo_url
            )
            try:
                pdf_bytes = _em_html_to_pdf_bytes(pdf_html)
                st.download_button(
                    "⬇️ Descargar PDF (A4)",
                    data=pdf_bytes,
                    file_name="energy_report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.warning(f"No se pudo generar PDF automáticamente ({e}). "
                           "Podés imprimir el HTML a PDF desde el navegador.")

# ========================= HELPERS DE CARGA =========================

def _em_parse_invoices(files):
    import pandas as pd, os
    tables, saved = [], []
    for f in (files or []):
        saved.append(getattr(f, "name", ""))
        suf = os.path.splitext(f.name)[1].lower()
        try:
            if suf == ".csv":
                df = pd.read_csv(f)
            elif suf in (".xlsx", ".xlsm", ".xls"):
                df = pd.read_excel(f)
            else:
                df = pd.DataFrame()
        except Exception:
            df = pd.DataFrame()
        if not df.empty:
            df["_source"] = f.name
            tables.append(df)
    return (pd.concat(tables, ignore_index=True) if tables else pd.DataFrame(), saved)
