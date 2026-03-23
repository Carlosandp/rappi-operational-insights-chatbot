"""
streamlit_app.py — Rappi Operations Analytics System v4.

Clean architecture:
  - UI theme/CSS → ui_theme.py (dual light/dark palettes)
  - UI components → ui_components.py (render functions)
  - Analytics pipeline → executor.py (pandas, deterministic)
  - LLM parsing → query_parser.py (dynamic creds, rule-based fallback)
  - LLM narration → chatbot.py (dynamic creds, deterministic fallback)
  - Charts → charts.py (metric-unit-aware, palette tokens)
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import time
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Rappi Ops Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Import modules ─────────────────────────────────────────────────────────
from ui_theme import get_tokens, inject_css, apply_plotly_theme, DEFAULT_MODE
from ui_components import (
    render_status_bar, render_chat_message, render_trace_bar,
    render_suggestion_buttons, render_demo_buttons, render_insight_card,
)
from utils import get_processed_data
from query_parser import parse_query
from executor import (
    get_top_zones, compare_groups, get_trend, rebuild_trend_from_wide,
    aggregate_metric, find_high_low_zones,
    find_fastest_growing_zones, detect_consistent_deterioration,
)
from chatbot import generate_answer, generate_suggestions
from charts import chart_ranking, chart_comparison, chart_trend, chart_multivariable, chart_growth
from insights import generate_all_insights, format_insight_card
from report_generator import generate_markdown_report, generate_html_report

# ── Startup: validate and clear stale processed cache ──────────────────────
# This runs once per process start. If the stored fingerprint does not match
# the current Excel content hash, delete the pkl so get_processed_data rebuilds.
# This prevents the "works locally, fails in the running app" scenario caused
# by unzipping a new release on top of an old directory.
def _clear_stale_cache() -> None:
    from pathlib import Path
    import sys, os
    app_dir = Path(__file__).parent
    processed_dir = app_dir.parent / "data" / "processed"
    pkl_file  = processed_dir / "processed_data.pkl"
    fp_file   = processed_dir / "source_fingerprint.txt"
    if not pkl_file.exists():
        return
    try:
        from utils import _source_fingerprint
        current_fp = _source_fingerprint()
        stored_fp  = fp_file.read_text().strip() if fp_file.exists() else ""
        if stored_fp != current_fp:
            pkl_file.unlink(missing_ok=True)
            fp_file.unlink(missing_ok=True)
    except Exception:
        # If anything fails, delete the cache to be safe
        pkl_file.unlink(missing_ok=True)

_clear_stale_cache()

# ── Session state defaults ──────────────────────────────────────────────────
for k, v in {
    "messages": [], "context": {}, "insights_data": None,
    "chat_input": "", "queued_submit": False,
    "theme_mode": DEFAULT_MODE,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Data loading ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="⏳ Cargando datos...")
def load_data():
    return get_processed_data()

data         = load_data()
metrics_wide = data["metrics_wide"]
orders_wide  = data["orders_wide"]
metrics_long = data["metrics_long"]
orders_long  = data["orders_long"]

N_ZONES      = metrics_wide[["COUNTRY","CITY","ZONE"]].drop_duplicates().shape[0]
N_COUNTRIES  = metrics_wide["COUNTRY"].nunique()
N_METRICS    = metrics_wide["METRIC"].nunique()
ALL_COUNTRIES       = sorted(metrics_wide["COUNTRY"].unique())
ALL_ZONE_TYPES      = sorted(metrics_wide["ZONE_TYPE"].unique())
ALL_PRIORITIZATIONS = sorted(metrics_wide["ZONE_PRIORITIZATION"].unique())

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Rappi Ops Analytics")
    st.markdown("---")

    # Theme selector
    mode = st.selectbox("🎨 Tema", ["dark", "light"], index=0,
                        key="theme_mode_select")
    st.session_state["theme_mode"] = mode
    T = get_tokens(mode)      # active palette tokens

    # Inject CSS with active palette
    inject_css(T)

    st.markdown("---")
    st.markdown("### 🔑 LLM Configuration")
    provider = st.selectbox("Provider", ["gemini", "groq"], index=0, key="llm_provider")
    api_key  = st.text_input("API Key", type="password",
                              placeholder="Pega tu Gemini o Groq key",
                              key="llm_api_key")
    llm_ready = False
    if api_key:
        os.environ["LLM_PROVIDER"] = provider
        if provider == "gemini":
            os.environ["GEMINI_API_KEY"] = api_key
            os.environ.pop("GROQ_API_KEY", None)
        else:
            os.environ["GROQ_API_KEY"] = api_key
            os.environ.pop("GEMINI_API_KEY", None)
        llm_ready = True
        st.success(f"✅ {provider.title()} configurado")
    else:
        st.warning("⚠️ Sin API key — modo fallback determinístico")

    st.markdown("---")
    st.markdown("### 🌎 Filtros rápidos")
    filter_countries      = st.multiselect("País(es)", ALL_COUNTRIES, key="f_countries")
    filter_zone_type      = st.selectbox("Tipo de zona", ["Todos"] + ALL_ZONE_TYPES, key="f_zone_type")
    filter_prioritization = st.selectbox("Priorización",  ["Todos"] + ALL_PRIORITIZATIONS, key="f_prio")

    if len(filter_countries) == 1 and filter_zone_type != "Todos":
        st.warning("⚠️ Filtro muy específico activo. Consultas por país devolverán un único grupo.")

    st.markdown("---")

    # Developer mode toggle (hides debug trace in delivery mode)
    show_debug    = st.checkbox("🔧 Developer mode", value=False, key="dev_mode")

    st.markdown(f"""
    <div style="font-size:0.8rem; color:{T['text_muted']}; margin-top:8px;">
      <b style="color:{T['sidebar_text']};">Resumen de datos</b><br>
      🌎 {N_COUNTRIES} países &nbsp;|&nbsp; 📍 {N_ZONES:,} zonas<br>
      📈 {N_METRICS} métricas &nbsp;|&nbsp; 🗓️ 9 semanas
    </div>""", unsafe_allow_html=True)


# ── Callback ────────────────────────────────────────────────────────────────
def _set_question(q: str):
    st.session_state["chat_input"]    = q
    st.session_state["queued_submit"] = True


# ── Entity resolution ────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _build_zone_catalog() -> dict:
    """
    Build three lookup structures from the loaded dataset:
      - zone_names_lower: set of all zone names in lowercase
      - city_names_lower: set of all city names in lowercase
      - unique_zones: dict mapping zone_lower -> {zone, city, country}
        for zones that appear in exactly ONE city/country combination.
    """
    try:
        d = load_data()
        mw = d["metrics_wide"]
        zone_names = set(mw["ZONE"].str.lower().unique())
        city_names = set(mw["CITY"].str.lower().unique())

        # Build full identity map for unique zones
        catalog = (
            mw[["ZONE", "CITY", "COUNTRY"]]
            .drop_duplicates()
            .copy()
        )
        catalog["zone_lower"] = catalog["ZONE"].str.lower()
        counts = catalog.groupby("zone_lower").size()
        unique_zones = {}
        for _, row in catalog.iterrows():
            zl = row["zone_lower"]
            if counts[zl] == 1:
                unique_zones[zl] = {
                    "zone":    row["ZONE"],
                    "city":    row["CITY"],
                    "country": row["COUNTRY"],
                }
        return {
            "zone_names": zone_names,
            "city_names": city_names,
            "unique_zones": unique_zones,
        }
    except Exception:
        return {"zone_names": set(), "city_names": set(), "unique_zones": {}}


def resolve_location_entities(filters: dict) -> tuple[dict, list[str]]:
    """
    Fix LLM entity-classification errors and strengthen zone identity.

    Two rules applied in order:

    1. City-to-zone reclassification: if filters['city'] matches a known ZONE
       but NOT a known CITY (e.g. 'Chapinero'), move it to filters['zone'].

    2. Unique-zone inference: if filters['zone'] matches exactly one zone in
       the dataset, fill in the canonical city and country automatically.
       This makes the query robust regardless of whether the LLM included those
       fields and prevents stale-context or sidebar contamination from
       accidentally filtering out the zone.
    """
    fixes: list[str] = []
    catalog = _build_zone_catalog()
    zone_names   = catalog["zone_names"]
    city_names   = catalog["city_names"]
    unique_zones = catalog["unique_zones"]

    filters = dict(filters)  # always work on a copy

    # ── Rule 1: city value is actually a zone name ────────────────────────
    city_val = (filters.get("city") or "").strip().lower()
    if city_val and city_val not in city_names and city_val in zone_names:
        if not filters.get("zone"):
            fixes.append(
                f"'{filters['city']}' no es una ciudad — interpretado como zona."
            )
            filters["zone"] = city_val
            filters["city"] = None

    # ── Rule 2: unique-zone inference ─────────────────────────────────────
    zone_val = (filters.get("zone") or "").strip().lower()
    if zone_val and zone_val in unique_zones:
        identity = unique_zones[zone_val]
        changed = []
        # Only fill fields that are not already explicitly set to a different value
        if not filters.get("city"):
            filters["city"]    = identity["city"]
            changed.append(f"ciudad={identity['city']}")
        if not filters.get("country"):
            filters["country"] = identity["country"]
            changed.append(f"país={identity['country']}")
        # Always use the canonical casing for zone
        if filters["zone"] != identity["zone"]:
            filters["zone"] = identity["zone"]
            changed.append(f"zona={identity['zone']}")
        if changed:
            fixes.append(
                f"Zona única '{identity['zone']}' — completada automáticamente: "
                + ", ".join(changed) + "."
            )

    return filters, fixes


# ── Filter policy ────────────────────────────────────────────────────────────
def clean_filters_for_intent(
    query_filters: dict,
    sidebar_filters: dict,
    intent: str,
    group_by: str | None = None,
) -> tuple[dict, list[str]]:
    """
    Build effective filters from query + sidebar using business-aware rules.
    Returns (effective_filters, warnings).

    The key insight: zone_type can contaminate queries in TWO ways —
      a) from the sidebar (user left a filter active)
      b) from the query parser (user mentioned "Non Wealthy" in the question text
         for a comparison that requires BOTH groups)

    Both sources must be handled.

    Rules applied in order:
    1. comparison/aggregation by ZONE_TYPE → strip zone_type from BOTH query
       filters AND sidebar. The question is asking to compare groups, so restricting
       to one group contradicts the intent.
    2. trend or multivariable with an explicit zone name → strip zone_type from BOTH
       query filters AND sidebar. Named zones belong to exactly one zone_type;
       adding the filter silently returns 0 rows.
    3. Everything else → query filter takes precedence; sidebar fills gaps.
    """
    warnings: list[str] = []

    # Start from a clean copy of query filters
    effective = {k: v for k, v in query_filters.items() if v is not None}

    # ── Rule 1: comparison/aggregation by ZONE_TYPE ───────────────────────
    if group_by == "ZONE_TYPE" and intent in ("comparison", "aggregation"):
        if effective.get("zone_type"):
            warnings.append(
                f"Se ignoró el filtro «Tipo: {effective['zone_type']}» "
                f"para comparar ambos grupos (Wealthy / Non Wealthy)."
            )
            del effective["zone_type"]
        # Also block sidebar zone_type
        sidebar_zt = sidebar_filters.get("zone_type")
        if sidebar_zt:
            warnings.append(
                f"Se ignoró el filtro lateral «Tipo: {sidebar_zt}» "
                f"para preservar la comparación entre grupos."
            )
        # Apply remaining sidebar filters (skip zone_type)
        for k, v in sidebar_filters.items():
            if k == "zone_type":
                continue
            if v and not effective.get(k):
                effective[k] = v
        return effective, warnings

    # ── Rule 2: trend/multivariable with explicit zone ────────────────────
    if intent in ("trend", "multivariable") and effective.get("zone"):
        if effective.get("zone_type"):
            warnings.append(
                f"Se ignoró el filtro «Tipo: {effective['zone_type']}» "
                f"para mantener la serie de la zona '{effective['zone']}'."
            )
            del effective["zone_type"]
        sidebar_zt = sidebar_filters.get("zone_type")
        if sidebar_zt:
            warnings.append(
                f"Se ignoró el filtro lateral «Tipo: {sidebar_zt}» "
                f"para mantener la serie de la zona '{effective['zone']}'."
            )
        for k, v in sidebar_filters.items():
            if k == "zone_type":
                continue
            if v and not effective.get(k):
                effective[k] = v
        return effective, warnings

    # ── Rule 3: default — sidebar fills gaps ──────────────────────────────
    for k, v in sidebar_filters.items():
        if v and not effective.get(k):
            effective[k] = v

    return effective, warnings


# ── Analytics pipeline ──────────────────────────────────────────────────────
def _run_query(question: str):
    sidebar_filters = {}
    if len(filter_countries) == 1:
        sidebar_filters["country"] = filter_countries[0]
    if filter_zone_type != "Todos":
        sidebar_filters["zone_type"] = filter_zone_type
    if filter_prioritization != "Todos":
        sidebar_filters["prioritization"] = filter_prioritization

    parsed = parse_query(question, context=st.session_state.context)
    if not parsed.get("filters"):
        parsed["filters"] = {}

    # Step 1: fix entity mis-classification (e.g. zone name placed in 'city' field by LLM)
    parsed["filters"], entity_fixes = resolve_location_entities(parsed["filters"])

    intent      = parsed.get("intent", "ranking")
    metric      = parsed.get("metric")
    group_by    = parsed.get("group_by") or "country"
    n_weeks     = int(parsed.get("n_weeks") or 5)
    agg         = parsed.get("aggregation") or "mean"

    # Step 2: apply business-aware filter policy (prevents sidebar AND query contamination)
    parsed["filters"], filter_warnings = clean_filters_for_intent(
        query_filters=parsed["filters"],
        sidebar_filters=sidebar_filters,
        intent=intent,
        group_by=group_by,
    )
    filter_warnings = entity_fixes + filter_warnings

    filters     = parsed.get("filters", {})
    ts          = parsed.get("time_scope", "L0W")
    top_k       = int(parsed.get("top_k") or 5)
    sort_dir    = parsed.get("sort", "desc")

    if "-" in str(ts):
        parts = ts.split("-"); start_week = parts[0].strip(); end_week = parts[1].strip()
        current_week = end_week
    else:
        valid = [f"L{i}W" for i in range(9)]
        current_week = ts if ts in valid else "L0W"
        start_week = f"L{n_weeks}W"; end_week = "L0W"

    result, fig = {}, None
    try:
        if intent == "ranking":
            result = get_top_zones(metrics_wide, orders_wide,
                                   metric=metric or "Lead Penetration",
                                   week=current_week, filters=filters,
                                   top_k=top_k, sort=sort_dir)
            fig = apply_plotly_theme(chart_ranking(result), T)

        elif intent in ("comparison", "aggregation"):
            result = compare_groups(metrics_wide, orders_wide,
                                    metric=metric or "Perfect Orders",
                                    group_by=group_by, week=current_week,
                                    filters=filters, agg=agg)
            fig = apply_plotly_theme(chart_comparison(result), T)

        elif intent == "trend":
            metric_used = metric or "Lead Penetration"

            # ── Layer 1: primary path via long table ──────────────────────────
            result = get_trend(
                metrics_long, orders_long,
                metric=metric_used,
                filters=filters,
                start_week=start_week, end_week=end_week,
            )

            # ── Layer 2: retry with full unique-zone identity ─────────────────
            if result["data"].empty and filters.get("zone"):
                catalog  = _build_zone_catalog()
                zone_key = str(filters["zone"]).strip().lower()
                identity = catalog["unique_zones"].get(zone_key)
                if identity:
                    retry_filters = {**filters,
                                     "zone":    identity["zone"],
                                     "city":    identity["city"],
                                     "country": identity["country"]}
                    retry_result = get_trend(
                        metrics_long, orders_long,
                        metric=metric_used,
                        filters=retry_filters,
                        start_week=start_week, end_week=end_week,
                    )
                    if not retry_result["data"].empty:
                        result  = retry_result
                        filters = retry_filters
                        parsed["filters"] = retry_filters
                        filter_warnings.append(
                            f"Zona única '{identity['zone']}' — completada automáticamente: "
                            f"ciudad={identity['city']}, país={identity['country']}, zona={identity['zone']}."
                        )

            # ── Layer 3: deterministic fallback — rebuild from wide table ──────
            # This bypasses the long-table pipeline entirely, reading values
            # directly from the wide rows. Immune to cache or processing issues.
            if result["data"].empty and filters.get("zone"):
                fallback = rebuild_trend_from_wide(
                    metrics_wide, orders_wide,
                    metric=metric_used,
                    filters=filters,
                    start_week=start_week, end_week=end_week,
                )
                if not fallback["data"].empty:
                    result  = fallback
                    parsed["filters"] = filters
                    filter_warnings.append(
                        "Serie reconstruida automáticamente desde tabla wide."
                    )

            # ── Layer 4: developer trace (only in debug mode) ─────────────────
            if show_debug and filters.get("zone"):
                _debug_src = metrics_long if metric_used != "Orders" else orders_long
                _debug_df  = _debug_src.copy()
                if metric_used != "Orders":
                    _debug_df = _debug_df[_debug_df["METRIC"] == metric_used]
                if filters.get("country"):
                    _debug_df = _debug_df[_debug_df["COUNTRY"].str.upper() == str(filters["country"]).upper()]
                if filters.get("city"):
                    _debug_df = _debug_df[_debug_df["CITY"].str.lower() == str(filters["city"]).lower()]
                if filters.get("zone"):
                    _debug_df = _debug_df[_debug_df["ZONE"].str.lower() == str(filters["zone"]).lower()]
                filter_warnings.append(f"[debug] Filas exactas en long: {len(_debug_df)}")

            # ── Layer 5: build chart — chart errors NEVER erase data ──────────
            fig = None
            try:
                fig = apply_plotly_theme(chart_trend(result), T)
            except Exception as chart_err:
                result["chart_error"] = str(chart_err)
                filter_warnings.append(
                    f"No se pudo renderizar el gráfico, pero la serie sí se obtuvo: {chart_err}"
                )

        elif intent == "multivariable":
            ma = parsed.get("metric_a") or "Lead Penetration"
            mb = parsed.get("metric_b") or "Perfect Orders"
            result = find_high_low_zones(metrics_wide,
                                         metric_a=ma, metric_b=mb,
                                         direction_a=parsed.get("metric_a_direction","high"),
                                         direction_b=parsed.get("metric_b_direction","low"),
                                         week=current_week, filters=filters)
            fig = apply_plotly_theme(chart_multivariable(result), T)

        elif intent == "growth_explanation":
            result = find_fastest_growing_zones(orders_wide, metrics_wide,
                                                 n_weeks=n_weeks, filters=filters, top_k=top_k)
            fig = apply_plotly_theme(chart_growth(result), T)

        elif intent == "anomaly":
            det = detect_consistent_deterioration(metrics_wide, filters=filters)
            result = {"data": det, "metric": metric or "All"}

        else:
            result = get_top_zones(metrics_wide, orders_wide,
                                   metric=metric or "Lead Penetration",
                                   week="L0W", filters=filters, top_k=5)
            fig = apply_plotly_theme(chart_ranking(result), T)

    except Exception as e:
        fig = None
        result = {
            "data": pd.DataFrame(),
            "metric": metric,
            "filters": filters if "filters" in dir() else {},
            "error": str(e),
        }

    answer      = generate_answer(question, intent, result, parsed)
    if filter_warnings:
        answer = answer + "\n\n" + "\n".join(filter_warnings)
    suggestions = generate_suggestions(intent, result, parsed)

    if metric:  st.session_state.context["last_metric"]  = metric
    if filters.get("country"): st.session_state.context["last_country"] = filters["country"]
    if filters.get("zone"):    st.session_state.context["last_zone"]    = filters["zone"]
    st.session_state.context["last_intent"] = intent

    trace = {
        "intent": intent, "metric": metric, "filters": filters,
        "time_scope": ts, "top_k": top_k, "group_by": group_by,
        "_source": parsed.get("_source","unknown"),
        "_llm_error": parsed.get("_llm_error"),
    }
    msg_id = str(time.time()).replace(".", "")
    st.session_state.messages.append({
        "role": "assistant", "content": answer,
        "fig": fig, "df": result.get("data", pd.DataFrame()),
        "suggestions": suggestions, "trace": trace, "id": msg_id,
    })


# ══════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════
tab_chat, tab_insights, tab_report = st.tabs(
    ["💬 Chatbot", "🔍 Auto Insights", "📄 Reporte Ejecutivo"]
)


# ─────────────── TAB 1: CHATBOT ────────────────────────────────────────────
with tab_chat:
    render_status_bar(N_ZONES, llm_ready, provider, T)
    st.markdown("### 💬 Consulta las operaciones en lenguaje natural")
    st.caption("Español o inglés — preguntas complejas bienvenidas")

    demo_qs = [
        "¿Cuáles son las 5 zonas con mayor Lead Penetration esta semana?",
        "Compara Perfect Orders entre Wealthy y Non Wealthy en Colombia",
        "Muestra la evolución de Gross Profit UE en Chapinero últimas 8 semanas",
        "¿Cuál es el promedio de Lead Penetration por país?",
        "¿Qué zonas tienen alto Lead Penetration pero bajo Perfect Orders?",
        "¿Cuáles son las zonas que más crecen en órdenes en las últimas 5 semanas?",
    ]

    with st.expander("💡 Preguntas demo — click para ejecutar", expanded=False):
        render_demo_buttons(demo_qs, _set_question)

    # ── Chat history ──────────────────────────────────────────────────────
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-user">👤 <b>Tú:</b> {msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            render_chat_message(msg, show_debug=show_debug)
            render_suggestion_buttons(
                msg.get("suggestions", []), msg.get("id", ""), _set_question
            )
            st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

    # ── Input row ─────────────────────────────────────────────────────────
    col_in, col_btn = st.columns([5, 1])
    with col_in:
        user_input = st.text_input(
            "question", key="chat_input",
            label_visibility="collapsed",
            placeholder="Haz una pregunta sobre métricas, zonas, tendencias o comparaciones…",
        )
    with col_btn:
        manual_send = st.button("Enviar →", type="primary",
                                use_container_width=True, key="btn_send")

    should_run = (manual_send and user_input.strip()) or \
                 (st.session_state.get("queued_submit") and user_input.strip())

    if should_run:
        st.session_state["queued_submit"] = False
        question = user_input.strip()
        st.session_state.messages.append({"role": "user", "content": question})
        with st.spinner("🧠 Analizando…"):
            _run_query(question)
        st.rerun()

    if st.session_state.messages:
        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        if st.button("🗑️ Limpiar chat", key="clear_chat"):
            st.session_state.messages = []
            st.session_state.context  = {}
            st.session_state["chat_input"] = ""
            st.rerun()


# ─────────────── TAB 2: AUTO INSIGHTS ─────────────────────────────────────
with tab_insights:
    st.markdown("### 🔍 Insights Automáticos")
    st.caption("Motor determinístico — 100% reproducible, sin alucinaciones")

    if st.button("▶️ Ejecutar motor de insights", type="primary",
                  use_container_width=True, key="run_insights"):
        with st.spinner("🔍 Analizando todas las zonas y métricas…"):
            st.session_state.insights_data = generate_all_insights(metrics_wide, orders_wide)

    if st.session_state.insights_data:
        ins = st.session_state.insights_data
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("🚨 Anomalías",     len(ins.get("anomalies",[])))
        c2.metric("📉 Tendencias",     len(ins.get("trends",[])))
        c3.metric("📊 Benchmarks",     len(ins.get("benchmarks",[])))
        c4.metric("🔗 Correlaciones",  len(ins.get("correlations",[])))
        c5.metric("🌟 Oportunidades",  len(ins.get("opportunities",[])))
        c6.metric("⚠️ Calidad datos",  len(ins.get("data_quality",[])))
        st.markdown("---")

        sections = [
            ("anomalies",    "🚨 Anomalías (WoW >10%)",                True),
            ("trends",       "📉 Tendencias Preocupantes (3+ sem)",     True),
            ("benchmarks",   "📊 Benchmarking vs. Pares",               False),
            ("correlations", "🔗 Correlaciones",                         False),
            ("opportunities","🌟 Oportunidades",                         True),
            ("data_quality", "⚠️ Alertas de Calidad de Datos",           False),
        ]
        for key, title, expanded in sections:
            raw_list = ins.get(key, [])
            if not raw_list:
                continue
            with st.expander(f"{title} ({len(raw_list)})", expanded=expanded):
                for raw in raw_list[:8]:
                    render_insight_card(format_insight_card(raw), primary_color=T["primary"])
    else:
        st.info("👆 Haz clic en **Ejecutar motor de insights** para analizar automáticamente.")


# ─────────────── TAB 3: EXECUTIVE REPORT ──────────────────────────────────
with tab_report:
    st.markdown("### 📄 Generador de Reporte Ejecutivo")
    st.caption("Descargable en Markdown o HTML — 6 categorías de insights")

    summary_stats = {"n_zones": N_ZONES, "n_countries": N_COUNTRIES, "n_metrics": N_METRICS}

    col_gen, col_fmt = st.columns([2, 1])
    with col_fmt:
        report_fmt = st.radio("Formato", ["HTML", "Markdown"], horizontal=True, key="report_fmt")
    with col_gen:
        gen_report = st.button("📄 Generar Reporte", type="primary",
                               use_container_width=True, key="gen_report")

    if gen_report:
        if not st.session_state.insights_data:
            with st.spinner("🔍 Generando insights primero…"):
                st.session_state.insights_data = generate_all_insights(metrics_wide, orders_wide)
        with st.spinner("✍️ Redactando reporte…"):
            ins = st.session_state.insights_data
            if report_fmt == "Markdown":
                content = generate_markdown_report(ins, summary_stats)
                st.download_button("⬇️ Descargar Markdown", content,
                                   file_name="rappi_executive_report.md",
                                   mime="text/markdown", key="dl_md")
                st.markdown("---"); st.markdown(content)
            else:
                content = generate_html_report(ins, summary_stats)
                st.download_button("⬇️ Descargar HTML", content,
                                   file_name="rappi_executive_report.html",
                                   mime="text/html", key="dl_html")
                st.markdown("---")
                st.components.v1.html(content, height=900, scrolling=True)
    else:
        st.info("👆 Haz clic en **Generar Reporte**. Ejecuta los insights primero.")
