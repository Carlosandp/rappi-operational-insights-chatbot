"""
ui_components.py — Reusable UI rendering functions.
Keeps streamlit_app.py clean by extracting all HTML/display logic here.
"""

import streamlit as st
import pandas as pd


def render_status_bar(n_zones: int, llm_ready: bool, provider: str, t: dict):
    llm_s = (f'<span class="s-ok">● LLM: {provider.title()}</span>'
             if llm_ready else '<span class="s-warn">● LLM: fallback</span>')
    st.markdown(
        f'<div class="status-bar">'
        f'<span class="s-ok">● Datos: {n_zones:,} zonas</span>'
        f'{llm_s}'
        f'<span class="s-ok">● Motor analítico: listo</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_trace_bar(trace: dict, show_debug: bool = False):
    """Render filter chips.
    Delivery mode (show_debug=False): only active filter chips — clean product feel.
    Developer mode (show_debug=True): also shows intent, group_by, source, and full trace JSON.
    """
    if not trace:
        return
    filters  = trace.get("filters", {})
    intent   = trace.get("intent", "")
    group_by = trace.get("group_by")
    src      = "🤖 LLM" if trace.get("_source") == "llm" else "⚙️ reglas"

    labels = {"country": "País", "city": "Ciudad", "zone": "Zona",
              "zone_type": "Tipo", "prioritization": "Prioridad"}

    filter_chips = [
        f'<span class="filter-chip">{labels.get(k, k)}: {v}</span>'
        for k, v in filters.items() if v
    ]

    if show_debug:
        # Developer mode: full chip set + trace expander
        debug_chips = list(filter_chips)
        debug_chips.append(f'<span class="filter-chip intent">Intent: {intent}</span>')
        if group_by and group_by != "country":
            debug_chips.append(f'<span class="filter-chip">Por: {group_by}</span>')
        debug_chips.append(f'<span style="font-size:0.73rem; opacity:0.7;">{src}</span>')
        if debug_chips:
            st.markdown(
                f'<div class="trace-bar">{"  ".join(debug_chips)}</div>',
                unsafe_allow_html=True,
            )
        with st.expander("🔍 Query trace (debug)", expanded=False):
            st.json(trace)
    else:
        # Delivery mode: only active filter chips
        if filter_chips:
            st.markdown(
                f'<div class="trace-bar">{"  ".join(filter_chips)}</div>',
                unsafe_allow_html=True,
            )

    # Trivial filter warning (always shown regardless of debug mode)
    tw = _trivial_warn(filters, intent)
    if tw:
        st.markdown(f'<div class="trivial-warning">{tw}</div>', unsafe_allow_html=True)


def _trivial_warn(filters: dict, intent: str) -> str | None:
    if intent == "aggregation" and filters.get("country"):
        return (f"ℹ️ Filtro activo: país={filters['country']}. "
                f"La agregación por país mostrará solo un grupo.")
    if intent == "comparison" and filters.get("zone_type"):
        return f"ℹ️ Filtro tipo={filters['zone_type']} activo en comparación."
    return None


def render_chat_message(msg: dict, show_debug: bool = False):
    """Render a single assistant message: answer + trace + chart + table + suggestions."""
    st.markdown(
        f'<div class="chat-bot">🤖 <b>Asistente:</b><br>{msg["content"]}</div>',
        unsafe_allow_html=True,
    )

    # Trace bar (always shown — filters only, debug behind flag)
    render_trace_bar(msg.get("trace"), show_debug=show_debug)

    # Chart
    if msg.get("fig"):
        st.plotly_chart(msg["fig"], use_container_width=True,
                        key=f"fig_{msg.get('id', '')}")

    # Data table + download
    df_msg = msg.get("df")
    if df_msg is not None and not df_msg.empty:
        with st.expander("📋 Ver tabla de datos", expanded=False):
            st.dataframe(df_msg.head(25), use_container_width=True)
            st.download_button(
                "⬇️ Descargar CSV",
                df_msg.to_csv(index=False),
                file_name="rappi_result.csv",
                mime="text/csv",
                key=f"dl_{msg.get('id', '')}",
            )


def render_suggestion_buttons(suggestions: list, msg_id: str, set_question_fn):
    """Render suggestion buttons — shorter labels, real on_click."""
    if not suggestions:
        return
    # Shorten suggestions for cleaner display
    short = [_shorten(s) for s in suggestions]
    st.markdown('<div class="sug-label">💡 Seguir explorando:</div>', unsafe_allow_html=True)
    cols = st.columns(len(short))
    for i, (orig, label) in enumerate(zip(suggestions, short)):
        cols[i].button(
            label,
            key=f"sug_{msg_id}_{i}",
            on_click=set_question_fn,
            args=(orig,),
            use_container_width=True,
        )


def _shorten(text: str, max_len: int = 45) -> str:
    """Trim suggestion to a shorter display label."""
    # Remove leading question marks and verbose openers
    text = text.strip().lstrip("¿").rstrip("?")
    text = text.replace("¿Ver ", "Ver ").replace("¿Comparar ", "Comparar ")
    text = text.replace("¿Quieres ver ", "Ver ").replace("¿Cuántas ", "Cuántas ")
    if len(text) > max_len:
        text = text[:max_len - 1] + "…"
    return text


def render_demo_buttons(demo_qs: list, set_question_fn):
    """Render demo question grid with real on_click callbacks."""
    cols = st.columns(2)
    for i, q in enumerate(demo_qs):
        cols[i % 2].button(
            q,
            key=f"demo_{i}",
            on_click=set_question_fn,
            args=(q,),
            use_container_width=True,
        )


def render_insight_card(card: dict, primary_color: str = "#FF5A3D"):
    """Render a single insight card with consistent styling."""
    sev = card.get("severity", "media")
    bc  = "#EF4444" if sev == "alta" else primary_color
    st.markdown(f"""
<div class="insight-card" style="border-left: 4px solid {bc};">
  <div class="insight-cat" style="color:{bc};">{card['category']} {'🔴' if sev == 'alta' else '🟠'}</div>
  <div class="insight-title">{card['title']}</div>
  <div class="insight-field"><b>📋 Evidencia:</b> {card['evidence']}</div>
  <div class="insight-field"><b>❓ Por qué importa:</b> {card['why_it_matters']}</div>
  <div class="insight-field"><b>✅ Acción:</b> {card['recommendation']}</div>
</div>""", unsafe_allow_html=True)
