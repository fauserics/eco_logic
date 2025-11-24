import json
import re
from io import BytesIO
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# ========================= IDIOMAS SENCILLOS ES / EN =========================

def get_lang() -> str:
    """
    Devuelve el idioma actual de la app: 'es' o 'en'.
    Por defecto: 'es'.
    """
    if "lang" not in st.session_state:
        st.session_state["lang"] = "es"
    return st.session_state["lang"]


def language_selector():
    """
    Selector de idioma global. Llamalo en cada página (Inicio.py y pages/*)
    para que el dropdown esté SIEMPRE visible en la barra lateral.
    """
    current = get_lang()

    # mapa label → código
    options = {"Español": "es", "English": "en"}
    # mapa código → label
    reverse = {v: k for k, v in options.items()}

    current_label = reverse.get(current, "Español")
    labels = list(options.keys())
    idx = labels.index(current_label)

    with st.sidebar:
        label = "Idioma / Language" if current == "es" else "Language"
        choice = st.selectbox(label, labels, index=idx, key="__lang_select")

    st.session_state["lang"] = options[choice]


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
    lines = (llm_text or "").splitlines()
    body_parts, toc = [], []
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

def _em_render_report_pdf_html(org: str, site: str, generated_at: str, llm_text: str,
                               brand_color: str, logo_url: str) -> str:
    body_html, toc = _markdownish_to_html_and_toc(llm_text)
    if toc:
        toc_items = []
        for level, title, sid in toc:
            indent = "0" if level == "h2" else "12"
            toc_items.append(f'<div style="margin-left:{indent}pt;">• <a href="#{sid}">{title}</a></div>')
        toc_html = "<h2>Índice</h2>" + "\n".join(toc_items)
    else:
        toc_html = "<h2>Índice</h2><p>(No se detectaron encabezados en el texto del informe)</p>"

    logo_img = f"<img src='{logo_url}' alt='Logo' style='height:64pt;vertical-align:middle;margin-right:10pt;'/>" if logo_url else ""
    style = f"""
    <style>
      @page {{
        size: A4;
        margin: 2cm;
        @bottom-right {{
          content: "Página " counter(page) " de " counter(pages);
          font-size: 9pt; color: #555;
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
        font-size: 72pt; color: #e6f2ef;
        z-index: 0;
      }}
      .section {{ position: relative; z-index: 1; }}
      .badge {{ float:right; background:{brand_color or '#0B8C6B'}; color:#fff; padding:2pt 6pt; border-radius:12pt; font-size:9pt; }}
      .headerline {{ border-bottom:2pt solid {brand_color or '#0B8C6B'}; padding-bottom:6pt; margin-bottom:12pt; }}
      @media print {{ .no-print {{ display:none; }} }}
    </style>
    """
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
    toc_page = f"""
    <div class="section">
      <div class="headerline"><h1>Contenido</h1></div>
      {toc_html}
    </div>
    <pdf:nextpage/>
    """
    body = f"""
    <div class="section">
      <div class="headerline"><h1>Informe</h1></div>
      {body_html}
    </div>
    """
    return f"<!doctype html><html><head><meta charset='utf-8'/>{style}</head><body>{cover}{toc_page}{body}</body></html>"

def _em_html_to_pdf_bytes(html: str) -> bytes | None:
    try:
        from io import BytesIO
        from xhtml2pdf import pisa
        out = BytesIO()
        if not html.lower().strip().startswith("<!doctype"):
            html = "<!doctype html><html><head><meta charset='utf-8'></head><body>" + html + "</body></html>"
        pisa.CreatePDF(src=html, dest=out, encoding="utf-8")
        return out.getvalue()
    except Exception:
        return None

def _em_show_print_button(html: str, label: str = "🖨️ Imprimir / Guardar como PDF (A4)"):
    import html as _html
    _ = _html.escape(html)
    payload = f"""
    <!doctype html>
    <html>
    <head><meta charset='utf-8'>
      <script>
        function openAndPrint() {{
          var w = window.open('', '_blank');
          w.document.open();
          w.document.write({repr(html)});
          w.document.close();
          setTimeout(function() {{ w.focus(); w.print(); }}, 300);
        }}
      </script>
    </head>
    <body class="no-print" style="margin:0;padding:8px;">
      <button onclick="openAndPrint()" style="padding:8px 12px; font-size:14px;">{label}</button>
    </body>
    </html>
    """
    st.components.v1.html(payload, height=60)

# ========================= OPENAI (reporte y OCR/parse) =========================

def _openai_client():
    import os
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta OPENAI_API_KEY en Secrets/entorno.")
    return OpenAI(api_key=api_key)

def _em_openai_report(dataset: dict, brand_color: str, logo_url: str,
                      model: str = "gpt-4o-mini", detail_level: int = 3,
                      temperature: float = 0.2) -> str:
    import json as _json
    try:
        client = _openai_client()
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
            "Redacta un informe institucional en español con tono profesional y claro. "
            "DEBES usar los valores de línea de base y EnPIs provistos en dataset.derived "
            "(kWh/año equivalente, $/kWh, kWh/m²·año, kWh/usuario·año) como referencia numérica. "
            "Cita explícitamente la línea de base con su período (dataset.derived.baseline.period_start → period_end) "
            "y construye EnPIs a partir de esos valores. Si faltan, indícalo como limitación de datos. "
            "Incluye estas secciones (con encabezados explícitos): "
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
            messages=[{"role":"system","content":system},{"role":"user","content":user}]
        )
        return out.choices[0].message.content
    except Exception as e:
        return (f"AVISO: No fue posible llamar a OpenAI ({e}). "
                "Revisá el modelo, la versión del SDK y la clave.")

# --------- OCR IMAGEN (ROBUSTO) ---------

def _ocr_image_invoice_with_openai(file_bytes: bytes, filename: str, model: str = "gpt-4o-mini"):
    """
    OCR de una imagen (PNG/JPG) con OpenAI Vision → filas mensuales.
    Preprocesa (resize<=1200px, grises, contraste/umbral), fuerza JSON estricto y hace retries.
    Guarda /tmp/last_ocr_raw.json si falla el parseo.
    """
    import base64, time, json as _json
    from PIL import Image, ImageOps

    def _preprocess(img_bytes: bytes) -> bytes:
        with Image.open(BytesIO(img_bytes)) as im:
            im = im.convert("L")
            max_side = 1200
            w, h = im.size
            scale = min(max_side / max(w, h), 1.0)
            if scale < 1.0:
                im = im.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
            im = ImageOps.autocontrast(im)
            # umbral suave: mejora contraste pero evita blanco/negro agresivo
            im = ImageOps.invert(ImageOps.invert(im).point(lambda p: 255 if p > 200 else (0 if p < 30 else p)))
            buf = BytesIO()
            im.save(buf, format="PNG", optimize=True)
            return buf.getvalue()

    try:
        client = _openai_client()
    except Exception as e:
        st.warning(f"OCR no disponible: {e}")
        return pd.DataFrame()

    pre = _preprocess(file_bytes)
    b64 = base64.b64encode(pre).decode("utf-8")
    image_url = f"data:image/png;base64,{b64}"

    prompt = (
        "Extrae datos de la factura de energía. Devuelve JSON con la clave 'rows' (lista). "
        "Cada elemento debe tener: year_month (YYYY-MM), kwh (número), cost (número), "
        "demand_kw (número o null), currency (texto breve, p.ej. ARS/USD). "
        "Si ves varias facturas o meses en la imagen, devolvé varias filas. "
        "No incluyas comentarios fuera del JSON."
    )

    delays = [0.5, 1.0, 2.0]
    last_raw = ""
    for delay in [0.0] + delays:
        if delay:
            time.sleep(delay)
        try:
            out = client.chat.completions.create(
                model=model,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Sos un extractor de datos que siempre responde JSON válido."},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]}
                ]
            )
            raw = out.choices[0].message.content or "{}"
            last_raw = raw
            data = json.loads(raw)
            rows = data.get("rows", [])
            recs = []
            for r in rows:
                ym = str(r.get("year_month") or "").strip()
                dt = pd.to_datetime(ym + "-01", errors="coerce")
                recs.append({
                    "_year_month": dt if pd.notna(dt) else pd.NaT,
                    "_kwh": float(r.get("kwh") or 0),
                    "_cost": float(r.get("cost") or 0),
                    "_demand_kw": float(r.get("demand_kw")) if r.get("demand_kw") not in (None, "") else None,
                    "_currency": (str(r.get("currency") or "").strip() or None),
                    "_source": filename
                })
            if recs:
                return pd.DataFrame(recs)
        except Exception:
            continue

    try:
        Path("/tmp/last_ocr_raw.json").write_text(last_raw, encoding="utf-8")
    except Exception:
        pass
    st.warning(f"No se pudo OCR {filename}: respuesta no JSON. Se guardó /tmp/last_ocr_raw.json para depurar.")
    return pd.DataFrame()

# --------- PDF: TEXTO + RENDER A IMAGEN (pypdfium2) ---------

def _extract_text_from_pdf_simple(file_obj) -> str:
    try:
        import PyPDF2
    except Exception:
        return ""
    try:
        reader = PyPDF2.PdfReader(file_obj)
        chunks = []
        for page in reader.pages:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(chunks).strip()
    except Exception:
        return ""

def _pdf_to_images(file_bytes: bytes, dpi: int = 200):
    """
    Convierte PDF a lista de imágenes PNG (bytes) usando pypdfium2.
    """
    try:
        import pypdfium2 as pdfium
        from PIL import Image  # noqa: F401
    except Exception:
        return []
    imgs = []
    try:
        pdf = pdfium.PdfDocument(BytesIO(file_bytes))
        n_pages = len(pdf)
        for i in range(n_pages):
            page = pdf.get_page(i)
            pil = page.render(scale=dpi/72).to_pil()
            buf = BytesIO()
            pil.save(buf, format="PNG")
            imgs.append(buf.getvalue())
            page.close()
        pdf.close()
    except Exception:
        return []
    return imgs

def _parse_invoice_text_blocks_with_llm(raw_text: str, filename: str, model: str = "gpt-4o-mini") -> pd.DataFrame:
    """
    Convierte texto crudo (PDF con texto) a filas mensuales. JSON estricto + retries.
    """
    if not (raw_text or "").strip():
        return pd.DataFrame()
    import json as _json, time
    try:
        client = _openai_client()
    except Exception as e:
        st.warning(f"Parser LLM deshabilitado: {e}")
        return pd.DataFrame()

    instruction = (
        "A partir del texto de una factura(s) de energía, devolvé JSON válido con una lista 'rows' "
        "de registros mensuales: year_month (YYYY-MM), kwh (número), cost (número), "
        "demand_kw (número o null), currency (texto). No incluyas comentarios fuera del JSON."
    )

    delays = [0.5, 1.0, 2.0]
    last_raw = ""
    for delay in [0.0] + delays:
        if delay:
            time.sleep(delay)
        try:
            out = client.chat.completions.create(
                model=model,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Sos un extractor de datos de facturas que siempre responde JSON válido."},
                    {"role": "user", "content": f"{instruction}\n\nTEXTO (truncado):\n{raw_text[:16000]}"}  # trunc seguridad
                ]
            )
            raw = out.choices[0].message.content or "{}"
            last_raw = raw
            data = _json.loads(raw)
            rows = data.get("rows", [])
            recs = []
            for r in rows:
                ym = str(r.get("year_month") or "").strip()
                dt = pd.to_datetime(ym + "-01", errors="coerce")
                recs.append({
                    "_year_month": dt if pd.notna(dt) else pd.NaT,
                    "_kwh": float(r.get("kwh") or 0),
                    "_cost": float(r.get("cost") or 0),
                    "_demand_kw": float(r.get("demand_kw")) if r.get("demand_kw") not in (None, "") else None,
                    "_currency": (str(r.get("currency") or "").strip() or None),
                    "_source": filename
                })
            if recs:
                return pd.DataFrame(recs)
        except Exception:
            continue

    try:
        Path("/tmp/last_ocr_raw.json").write_text(last_raw, encoding="utf-8")
    except Exception:
        pass
    st.warning(f"No se pudo interpretar texto de PDF {filename}: respuesta no JSON. Se guardó /tmp/last_ocr_raw.json.")
    return pd.DataFrame()

# ========================= RESUMEN / BASELINE / ENPI =========================

def _em_summarize_invoices(inv_df: pd.DataFrame, total_area_m2: float, users_count: int,
                           baseline_start: str | None, baseline_end: str | None):
    result = {"monthly_series": [], "metrics": {}, "period": {"start": None, "end": None}, "notes": []}
    if inv_df is None or inv_df.empty or "_year_month" not in inv_df.columns:
        result["notes"].append("No hay datos tabulares de facturas (o no se detectó período).")
        return result

    df = inv_df.copy()
    df = df.dropna(subset=["_year_month"])
    if df.empty:
        result["notes"].append("No se pudo interpretar el período de facturación.")
        return result

    grp = df.groupby("_year_month", as_index=False).agg(
        kwh=("_kwh","sum"),
        cost=("_cost","sum"),
        demand_kw=("_demand_kw","max")
    ).sort_values("_year_month")

    result["monthly_series"] = [
        {"month": d.strftime("%Y-%m"), "kwh": float(k or 0), "cost": float(c or 0), "demand_kw": float(dk or 0) if pd.notna(dk) else None}
        for d,k,c,dk in zip(grp["_year_month"], grp["kwh"], grp["cost"], grp["demand_kw"])
    ]

    total_kwh = float(grp["kwh"].fillna(0).sum())
    total_cost = float(grp["cost"].fillna(0).sum())
    months = int(grp.shape[0])
    unit_cost = (total_cost / total_kwh) if total_kwh > 0 else None

    factor = 12 / months if months and months < 12 else 1.0
    kwh_year_equiv = total_kwh * factor
    kwh_per_m2_yr = (kwh_year_equiv / total_area_m2) if total_area_m2 and total_area_m2 > 0 else None
    kwh_per_user_yr = (kwh_year_equiv / users_count) if users_count and users_count > 0 else None

    result["metrics"] = {
        "total_kwh": total_kwh, "total_cost": total_cost, "unit_cost": unit_cost,
        "months": months, "kwh_year_equiv": kwh_year_equiv,
        "kwh_per_m2_yr": kwh_per_m2_yr, "kwh_per_user_yr": kwh_per_user_yr
    }

    start = grp["_year_month"].min()
    end = grp["_year_month"].max()
    result["period"] = {
        "start": start.strftime("%Y-%m") if pd.notna(start) else None,
        "end": end.strftime("%Y-%m") if pd.notna(end) else None,
        "baseline_start": str(baseline_start) if baseline_start else None,
        "baseline_end": str(baseline_end) if baseline_end else None
    }

    if months < 6:
        result["notes"].append("Menos de 6 meses de datos: la anualización puede ser poco representativa.")
    if total_kwh == 0:
        result["notes"].append("kWh total = 0 (revisar extracción/columnas).")
    return result

def _em_compute_baseline_from_invoices(invoices_summary: dict, total_area_m2: float, users_count: int):
    res = {"baseline": {}, "enpi": {}, "notas": []}
    if not invoices_summary or "metrics" not in invoices_summary:
        res["notas"].append("No hay métricas de facturas para baseline/EnPI.")
        return res
    m = invoices_summary.get("metrics", {})
    p = invoices_summary.get("period", {})
    total_kwh = m.get("total_kwh") or 0.0
    kwh_year_equiv = m.get("kwh_year_equiv") or total_kwh
    unit_cost = m.get("unit_cost")
    kwh_per_m2_yr = m.get("kwh_per_m2_yr")
    kwh_per_user_yr = m.get("kwh_per_user_yr")
    if (not kwh_per_m2_yr) and total_area_m2:
        kwh_per_m2_yr = (kwh_year_equiv / total_area_m2) if total_area_m2 > 0 else None
    if (not kwh_per_user_yr) and users_count:
        kwh_per_user_yr = (kwh_year_equiv / users_count) if users_count > 0 else None
    res["baseline"] = {
        "period_start": p.get("start"),
        "period_end": p.get("end"),
        "kwh_year_equiv": kwh_year_equiv,
        "unit_cost": unit_cost
    }
    res["enpi"] = {
        "kwh_per_m2_yr": kwh_per_m2_yr,
        "kwh_per_user_yr": kwh_per_user_yr,
        "cost_per_kwh": unit_cost
    }
    notes = invoices_summary.get("notes", []) or invoices_summary.get("notas", [])
    res["notas"].extend(notes)
    return res

# ========================= HELPERS DE CARGA =========================

def _normalize_invoice_table(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    cols = {c.lower().strip(): c for c in df.columns}
    def pick(cands):
        for k in cands:
            if k in cols: return cols[k]
        return None
    c_date  = pick(["fecha","date","periodo","period","billing_period","mes","month"])
    c_kwh   = pick(["kwh","consumo_kwh","consumption_kwh","energy_kwh","active_energy_kwh"])
    c_cost  = pick(["costo","cost","importe","monto","amount","total"])
    c_dem   = pick(["demanda_kw","kw","peak_kw","dem_kw"])
    c_curr  = pick(["moneda","currency"])

    if c_date:
        try: df["_date"] = pd.to_datetime(df[c_date], dayfirst=True, errors="coerce")
        except Exception: df["_date"] = pd.to_datetime(df[c_date], errors="coerce")
        m = df["_date"].isna() & df[c_date].astype(str).str.match(r"^\d{4}-\d{2}$")
        if m.any():
            df.loc[m, "_date"] = pd.to_datetime(df.loc[m, c_date] + "-01", errors="coerce")
        df["_year_month"] = df["_date"].dt.to_period("M").dt.to_timestamp()
    else:
        df["_year_month"] = pd.NaT

    for src, dst in [(c_kwh, "_kwh"), (c_cost, "_cost"), (c_dem, "_demand_kw")]:
        if src: df[dst] = pd.to_numeric(df[src], errors="coerce")
        else:   df[dst] = None

    df["_currency"] = df[c_curr].astype(str) if c_curr else None
    df["_source"] = source_name
    return df

# ========================= PÁGINAS (UI) =========================

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
    st.subheader("AInergy Score Audit ⚡")

    # ------ Registro histórico (import/export) ------
    with st.expander("📒 Registro histórico de facturas (CSV)", expanded=False):
        st.caption("Importá un ledger previo o descargá el actual normalizado.")
        if "em_ledger" not in st.session_state:
            st.session_state["em_ledger"] = pd.DataFrame(columns=["_year_month","_kwh","_cost","_demand_kw","_currency","_source"])
        up = st.file_uploader("Cargar ledger CSV (columnas: _year_month,_kwh,_cost,_demand_kw,_currency,_source)", type=["csv"], key="em_ledger_up")
        if up:
            try:
                new = pd.read_csv(up, parse_dates=["_year_month"], dayfirst=True, infer_datetime_format=True)
                st.session_state["em_ledger"] = pd.concat([st.session_state["em_ledger"], new], ignore_index=True).drop_duplicates()
                st.success("Ledger importado y fusionado.")
            except Exception as e:
                st.error(f"No se pudo importar el ledger: {e}")
        st.download_button("⬇️ Descargar ledger actual (CSV)",
                           data=st.session_state["em_ledger"].to_csv(index=False),
                           file_name="energy_invoices_ledger.csv")

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
    uses_df = st.data_editor(
        pd.DataFrame([{"tipología":"Oficinas","area_m2":1000,"horas_operación_semana":50}]),
        num_rows="dynamic", use_container_width=True, key="em_uses_df"
    )

    st.markdown("**Perfiles de uso / Ocupación**")
    occ_col1, occ_col2 = st.columns(2)
    peak_occupancy = int(occ_col1.number_input("Ocupación pico", 0, 1_000_000, 0, key="em_peak"))
    occupancy_pattern = occ_col2.text_input("Patrón de ocupación", "L–V 9–18, sáb reducido", key="em_occpat")

    st.markdown("**Evidencias**")
    photos = st.file_uploader("Fotos / Facturas en imagen (PNG/JPG)", type=["png","jpg","jpeg"], accept_multiple_files=True, key="em_photos")
    invoices = st.file_uploader("Facturas/mediciones (CSV/XLSX o PDF)", type=["csv","xlsx","xls","pdf"], accept_multiple_files=True, key="em_invoices")

    with st.expander("Opciones de lectura de facturas", expanded=True):
        use_ocr = st.toggle("Usar OCR con OpenAI (imágenes y PDFs escaneados)", value=True)
        ocr_model = st.selectbox("Modelo para OCR/parse", ["gpt-4o-mini","gpt-4o"], index=0)
        ocr_dpi = st.slider("DPI para rasterizar PDF", 120, 240, 180, 10, help="Menor DPI = archivos más livianos")

    st.markdown("**Política energética, objetivos y plan**")
    energy_policy = st.text_area("Política energética (borrador)", key="em_policy")
    objectives = st.text_area("Objetivos/Metas (uno por línea)", "Reducir EUI 10% en 12 meses\nPF ≥ 0.97", key="em_objs")
    action_plan = st.text_area("Plan de acción (uno por línea)", "LED\nOptimización consignas HVAC\nMantenimiento VFD", key="em_plan")

    if "em_last_dataset" not in st.session_state:
        st.session_state["em_last_dataset"] = None

    # ---- Guardar dataset del sitio
    if st.button("Guardar dataset del sitio (memoria de sesión)", key="em_save"):
        inv_tables, saved_files = [], []

        # 1) CSV/XLSX/PDF
        for f in (invoices or []):
            saved_files.append(getattr(f, "name", ""))
            name = getattr(f, "name", "file")
            suf = name.lower().split(".")[-1]
            try:
                if suf == "csv":
                    df = pd.read_csv(f)
                    inv_tables.append(_normalize_invoice_table(df, name))
                elif suf in ("xlsx","xlsm","xls"):
                    df = pd.read_excel(f)
                    inv_tables.append(_normalize_invoice_table(df, name))
                elif suf == "pdf":
                    b = f.read()
                    # 1) Intentar extraer texto (si no es escaneado)
                    raw = _extract_text_from_pdf_simple(BytesIO(b))
                    parsed = pd.DataFrame()
                    if raw:
                        parsed = _parse_invoice_text_blocks_with_llm(raw, name, model=ocr_model) if use_ocr else pd.DataFrame()
                    # 2) Si falló o no hay texto, rasterizar y OCR por página
                    if parsed.empty and use_ocr:
                        pages = _pdf_to_images(b, dpi=int(ocr_dpi))
                        for j, pbytes in enumerate(pages):
                            dfo = _ocr_image_invoice_with_openai(pbytes, f"{name}#p{j+1}.png", model=ocr_model)
                            if not dfo.empty:
                                inv_tables.append(dfo)
                        if not pages:
                            st.info(f"No se pudo rasterizar {name}. ¿Agregaste pypdfium2 y Pillow al requirements?")
                    elif not parsed.empty:
                        inv_tables.append(parsed)
                else:
                    st.info(f"Formato no soportado en 'Facturas': {name}")
            except Exception as e:
                st.warning(f"No se pudo leer {name}: {e}")

        # 2) Imágenes (OCR)
        for p in (photos or []):
            saved_files.append(getattr(p, "name", ""))
            try:
                if use_ocr:
                    df = _ocr_image_invoice_with_openai(p.read(), p.name, model=ocr_model)
                    if not df.empty:
                        inv_tables.append(df)
            except Exception as e:
                st.warning(f"No se pudo OCR {p.name}: {e}")

        # Consolidación + merge con ledger histórico
        inv_df = pd.concat(inv_tables, ignore_index=True) if inv_tables else pd.DataFrame()
        if not inv_df.empty:
            if "_year_month" in inv_df.columns:
                inv_df["_year_month"] = pd.to_datetime(inv_df["_year_month"])
            cols = ["_year_month","_kwh","_cost","_demand_kw","_currency","_source"]
            inv_df = inv_df[[c for c in cols if c in inv_df.columns]]
            st.session_state["em_ledger"] = pd.concat([st.session_state.get("em_ledger", pd.DataFrame(columns=cols)), inv_df], ignore_index=True)
            st.session_state["em_ledger"] = st.session_state["em_ledger"].drop_duplicates()

        # Área total y usuarios
        try:
            total_area_m2 = float(pd.DataFrame(st.session_state.get("em_uses_df", [])).get("area_m2", pd.Series([0])).sum())
        except Exception:
            total_area_m2 = 0.0

        # Usamos el ledger completo para baseline/series
        use_df = st.session_state["em_ledger"].copy()
        invoices_summary = _em_summarize_invoices(
            inv_df=use_df,
            total_area_m2=total_area_m2,
            users_count=int(st.session_state.get("em_users", 0)),
            baseline_start=st.session_state.get("em_bstart"),
            baseline_end=st.session_state.get("em_bend"),
        )
        derived = _em_compute_baseline_from_invoices(
            invoices_summary=invoices_summary,
            total_area_m2=total_area_m2,
            users_count=int(st.session_state.get("em_users", 0))
        )

        dataset = {
            "site": {
                "organization": org or "Org",
                "site_name": site or "Site",
                "address": address,
                "climate_zone": climate_zone,
                "baseline_start": str(baseline_start) if baseline_start else None,
                "baseline_end": str(baseline_end) if baseline_end else None,
                "energy_policy": energy_policy,
                "significant_energy_uses": [],  # podés enganchar los SEUs desde uses_df si querés
                "enpis": [],
                "objectives": [s.strip() for s in (objectives or "").splitlines() if s.strip()],
                "action_plan": [s.strip() for s in (action_plan or "").splitlines() if s.strip()],
            },
            "users_profile": {
                "users_count": users_count,
                "peak_occupancy": peak_occupancy,
                "occupancy_pattern": occupancy_pattern,
            },
            "building_uses": uses_df.to_dict("records"),
            "evidence_files": saved_files,
            "invoices": {
                "preview_rows": use_df.head(100).to_dict(orient="records") if (not use_df.empty) else [],
                "summary": invoices_summary
            },
            "derived": derived
        }
        st.session_state["em_last_dataset"] = dataset
        st.success("Dataset guardado en memoria de sesión.")

        # ---- Vista + KPIs + GRÁFICOS ----
        if not use_df.empty:
            st.markdown("**Ledger normalizado (histórico consolidado):**")
            show_cols = [c for c in ["_year_month","_kwh","_cost","_demand_kw","_currency","_source"] if c in use_df.columns]
            if show_cols:
                dfshow = use_df.copy().sort_values("_year_month")
                st.dataframe(dfshow[show_cols].rename(columns={
                    "_year_month":"mes","_kwh":"kWh","_cost":"costo","_demand_kw":"demanda_kw","_currency":"moneda","_source":"archivo"
                }), use_container_width=True)

            st.markdown("**Baseline y EnPIs:**")
            c1, c2, c3, c4 = st.columns(4)
            b = derived.get("baseline", {})
            e = derived.get("enpi", {})
            with c1: st.metric("kWh/año (equiv.)", f"{(b.get('kwh_year_equiv') or 0):,.0f}")
            with c2: st.metric("$/kWh", f"{(e.get('cost_per_kwh') or 0):,.4f}" if e.get("cost_per_kwh") else "–")
            with c3: st.metric("kWh/m²·año", f"{(e.get('kwh_per_m2_yr') or 0):,.1f}" if e.get("kwh_per_m2_yr") else "–")
            with c4: st.metric("kWh/usuario·año", f"{(e.get('kwh_per_user_yr') or 0):,.0f}" if e.get("kwh_per_user_yr") else "–")

            ms = invoices_summary.get("monthly_series", [])
            if ms:
                sdf = pd.DataFrame(ms)
                sdf["month"] = pd.to_datetime(sdf["month"])
                st.markdown("**Tendencias mensuales**")
                c5, c6 = st.columns(2)
                with c5:
                    st.altair_chart(
                        alt.Chart(sdf).mark_line(point=True).encode(
                            x=alt.X("month:T", title="Mes"),
                            y=alt.Y("kwh:Q", title="kWh"),
                            tooltip=[alt.Tooltip("month:T", title="Mes", format="%Y-%m"),
                                     alt.Tooltip("kwh:Q", title="KWh", format=",.0f")]
                        ).properties(height=280),
                        use_container_width=True
                    )
                with c6:
                    st.altair_chart(
                        alt.Chart(sdf).mark_line(point=True).encode(
                            x=alt.X("month:T", title="Mes"),
                            y=alt.Y("cost:Q", title="Costo"),
                            tooltip=[alt.Tooltip("month:T", title="Mes", format="%Y-%m"),
                                     alt.Tooltip("cost:Q", title="Costo", format=",.2f")]
                        ).properties(height=280),
                        use_container_width=True
                    )

    # ---- Parámetros de reporte LLM + branding
    st.markdown("---")
    st.markdown("#### Generar reporte con OpenAI")

    colm1, colm2, colm3 = st.columns([2, 1, 1])
    with colm1:
        model = st.selectbox("Modelo OpenAI", ["gpt-4o-mini", "gpt-4o"], index=0)
    with colm2:
        detail_level = st.slider("Nivel de detalle", 1, 5, 3, 1)
    with colm3:
        temperature = st.slider("Creatividad (temp.)", 0.0, 1.0, 0.2, 0.1)

    brand_color = st.color_picker("Color institucional", "#0B8C6B", key="em_color")
    logo_url = st.text_input("Logo (URL pública opcional)", key="em_logo")

    if st.button("Generar reporte ISO 50001", key="em_report"):
        dataset = st.session_state.get("em_last_dataset")
        if not dataset:
            st.error("No hay dataset guardado para generar el reporte.")
        else:
            st.info(f"Generando reporte con **{model}** · detalle **{detail_level}/5** · temp **{temperature:.1f}**…")
            llm_text = _em_openai_report(
                dataset=dataset, brand_color=brand_color, logo_url=logo_url,
                model=model, detail_level=detail_level, temperature=temperature,
            )
            html = _em_render_report_html(
                org=dataset["site"]["organization"], site=dataset["site"]["site_name"],
                generated_at=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                llm_text=llm_text, brand_color=brand_color, logo_url=logo_url
            )
            _em_download_button_html(html, "energy_report.html")
            st.markdown("Vista previa:")
            st.components.v1.html(html, height=800, scrolling=True)

            pdf_html = _em_render_report_pdf_html(
                org=dataset["site"]["organization"], site=dataset["site"]["site_name"],
                generated_at=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                llm_text=llm_text, brand_color=brand_color, logo_url=logo_url
            )
            pdf_bytes = _em_html_to_pdf_bytes(pdf_html)
            if pdf_bytes:
                st.download_button("⬇️ Descargar PDF (A4)", data=pdf_bytes, file_name="energy_report.pdf",
                                   mime="application/pdf", use_container_width=True)
            else:
                st.info("Podés exportar el PDF directamente desde tu navegador.")
                _em_show_print_button(pdf_html, label="🖨️ Imprimir / Guardar como PDF (A4)")
