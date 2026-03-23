"""
chatbot.py — LLM narrative generation from structured analytical results.
Fixes: google.genai migration, dynamic creds, unified formatting via utils.fmt_value.
"""

import json, os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

# Metric unit registry (mirrors charts.py — single source of truth is metric_dictionary.json)
METRIC_UNITS = {
    "Lead Penetration": "decimal",   # can exceed 1.0, shown as raw decimal
    "Perfect Orders": "ratio",
    "Gross Profit UE": "currency",
    "Pro Adoption (Last Week Status)": "ratio",
    "% PRO Users Who Breakeven": "ratio",
    "MLTV Top Verticals Adoption": "ratio",
    "Restaurants SS > ATC CVR": "ratio",
    "Restaurants SST > SS CVR": "ratio",
    "Retail SST > SS CVR": "ratio",
    "% Restaurants Sessions With Optimal Assortment": "ratio",
    "Non-Pro PTC > OP": "ratio",
    "Turbo Adoption": "ratio",
    "Restaurants Markdowns / GMV": "ratio",
    "Orders": "count",
}


def _fmt(val: float, metric: str) -> str:
    """Format value consistently with charts.py — never ad-hoc heuristics."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    unit = METRIC_UNITS.get(metric, "ratio")
    if unit == "count":    return f"{val:,.0f}"
    if unit == "currency": return f"${val:,.2f}"
    if unit == "decimal":  return f"{val:.2f}"
    return f"{val:.1%}"  # ratio


def _get_llm_config() -> dict:
    return {
        "provider":   os.environ.get("LLM_PROVIDER", "gemini").lower(),
        "gemini_key": os.environ.get("GEMINI_API_KEY", ""),
        "groq_key":   os.environ.get("GROQ_API_KEY", ""),
    }


ANSWER_SYSTEM_PROMPT = """You are Rappi's operations analytics assistant.
Write clear, concise, business-friendly responses in the SAME LANGUAGE as the user's question (Spanish or English).
Rules: max 3-4 paragraphs, lead with the key finding, reference specific numbers,
for growth say "hypothesis/correlation" not causation, no markdown headers."""


def _df_to_summary(df: pd.DataFrame, max_rows: int = 10) -> str:
    if df is None or df.empty:
        return "No data available."
    rows = df.head(max_rows).to_dict("records")
    lines = [f"Columns: {', '.join(df.columns.tolist())}"]
    for i, row in enumerate(rows, 1):
        row_str = " | ".join(
            f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}"
            for k, v in row.items() if v is not None
        )
        lines.append(f"Row {i}: {row_str}")
    return "\n".join(lines)


def _call_gemini(prompt: str, api_key: str) -> str:
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=ANSWER_SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=600,
            ),
        )
        return response.text
    except ImportError:
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            import google.generativeai as genai_legacy
        genai_legacy.configure(api_key=api_key)
        model = genai_legacy.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=ANSWER_SYSTEM_PROMPT,
        )
        return model.generate_content(prompt).text


def _call_groq(prompt: str, api_key: str) -> str:
    from groq import Groq
    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        max_tokens=600,
    )
    return completion.choices[0].message.content


def generate_answer(question: str, intent: str, result: dict, parsed_query: dict) -> str:
    df            = result.get("data", pd.DataFrame())
    data_summary  = _df_to_summary(df)
    filters       = parsed_query.get("filters", {})
    active        = {k: v for k, v in filters.items() if v}
    filter_note   = f"\nActive filters: {json.dumps(active)}" if active else ""

    extra = ""
    if intent == "growth_explanation" and result.get("explanations"):
        lines = []
        for exp in result["explanations"][:3]:
            imps = exp.get("top_metric_improvements", [])
            imp_str = ", ".join(f"{i['metric']} ({i['pct_change']:+.1%})" for i in imps[:3])
            lines.append(f"Zone {exp['zone']}: orders grew {exp['growth_pct']:+.1%}. Correlated: {imp_str}")
        extra = "\n\nGrowth explanations:\n" + "\n".join(lines)

    # Add data quality context for LP outliers
    dq_note = ""
    if result.get("has_lp_outliers"):
        dq_note = "\nData quality note: Lead Penetration values >2.0 are absolute store counts, NOT ratios. Mention this clearly."
    elif result.get("lp_outliers_excluded"):
        dq_note = "\nData quality note: LP outliers (>2.0, store counts) excluded from aggregates for ratio comparability."

    prompt = f'User question: "{question}"\nIntent: {intent}{filter_note}{dq_note}\n\nData:\n{data_summary}{extra}\n\nAnswer based ONLY on data above.'

    cfg = _get_llm_config()
    try:
        if cfg["provider"] == "gemini" and cfg["gemini_key"]:
            return _call_gemini(prompt, cfg["gemini_key"])
        elif cfg["provider"] == "groq" and cfg["groq_key"]:
            return _call_groq(prompt, cfg["groq_key"])
        elif cfg["gemini_key"]:
            return _call_gemini(prompt, cfg["gemini_key"])
        elif cfg["groq_key"]:
            return _call_groq(prompt, cfg["groq_key"])
    except Exception:
        pass
    return _fallback_answer(intent, result, question, parsed_query)


def _fallback_answer(intent: str, result: dict, question: str, parsed_query: dict = None) -> str:
    """Deterministic, intent-specific fallback using unified _fmt() — no ad-hoc heuristics."""
    df       = result.get("data", pd.DataFrame())
    metric   = result.get("metric") or (parsed_query or {}).get("metric", "")
    week     = result.get("week", "L0W")
    filters  = (parsed_query or {}).get("filters", {})
    # Show only meaningful filters — skip None values and internal keys
    fs_parts = [f"{k}={v}" for k, v in filters.items() if v and not k.startswith("_")]
    fn       = f" ({', '.join(fs_parts)})" if fs_parts else ""

    if df.empty:
        fs_clean = ", ".join(f"{k}: {v}" for k, v in filters.items() if v)
        hint = f" Filtros activos: {fs_clean}." if fs_clean else ""
        return f"No se encontraron datos para esta consulta.{hint} Intenta ampliar los filtros."

    if intent == "ranking":
        lines = [f"Estas son las **{len(df)} zonas con mayor {metric}** en la semana actual{fn}:"]
        for _, row in df.head(5).iterrows():
            lines.append(f"• **#{int(row.get('rank',1))} {row['ZONE']}** ({row.get('COUNTRY','')}) — {_fmt(row.get('value',0), metric)}")
        if result.get("has_lp_outliers"):
            n_out = len(result.get("lp_outliers_df", pd.DataFrame()))
            lines.append(f"\nℹ️ *{n_out} zona(s) con Lead Penetration ≥ 2.0 excluidas del ranking (conteos absolutos de tiendas, no ratios).*")
        return "\n".join(lines)

    if intent in ("aggregation", "comparison"):
        gb    = result.get("group_by", "grupo")
        label = "Comparación" if intent == "comparison" else "Promedio"
        lines = [f"**{label} de {metric} por {gb}{fn}:**"]
        for _, row in df.iterrows():
            n = f" ({int(row['n_zones'])} zonas)" if "n_zones" in row else ""
            lines.append(f"• **{row['group']}**: {_fmt(row.get('value',0), metric)}{n}")
        # Show gap for comparison between exactly two groups
        if len(df) == 2 and intent == "comparison":
            v0, v1 = df.iloc[0]["value"], df.iloc[1]["value"]
            g0, g1 = df.iloc[0]["group"], df.iloc[1]["group"]
            diff = v0 - v1
            unit = METRIC_UNITS.get(metric, "ratio")
            if unit == "ratio":
                diff_str = f"{abs(diff)*100:.1f} p.p."
            elif unit == "currency":
                diff_str = f"${abs(diff):,.2f}"
            else:
                diff_str = _fmt(abs(diff), metric)
            lines.append(f"\n**Gap {g0} vs {g1}:** {diff_str} ({'a favor de ' + g0 if diff > 0 else 'a favor de ' + g1})")
        if result.get("lp_outliers_excluded"):
            lines.append("\nℹ️ *Outliers de Lead Penetration (≥2.0) excluidos del promedio para comparabilidad.*")
        return "\n".join(lines)

    if intent == "trend":
        n = len(df)
        if n > 0:
            sv, ev   = df.iloc[0]["value"], df.iloc[-1]["value"]
            avg_val  = df["value"].mean()
            wow      = df.iloc[-1].get("wow_change")
            wow_str  = f"{wow:+.1%}" if wow is not None and not (isinstance(wow, float) and np.isnan(wow)) else "N/A"
            chg      = (ev - sv) / abs(sv) if sv != 0 else 0
            dir_     = "mejoró" if chg > 0 else "empeoró"
            zone_lbl = filters.get("zone", "").title() or "la zona"
            lines = [
                f"**{metric} — {zone_lbl}** (últimas {n} semanas):",
                f"• Valor actual: **{_fmt(ev, metric)}**",
                f"• Cambio WoW: **{wow_str}**",
                f"• Promedio 8 semanas: **{_fmt(avg_val, metric)}**",
                f"• Tendencia general: {dir_} {abs(chg):.1%} ({_fmt(sv, metric)} → {_fmt(ev, metric)})",
            ]
            return "\n".join(lines)
        return f"No se encontraron datos de tendencia para {metric}{fn}."

    if intent == "multivariable":
        ma, mb = result.get("metric_a","A"), result.get("metric_b","B")
        n      = result.get("count", len(df))
        lines  = [f"Se identificaron **{n} zonas con alto {ma} pero bajo {mb}**{fn}:"]
        for _, row in df.head(5).iterrows():
            lines.append(f"• **{row['ZONE']}** ({row.get('COUNTRY','')}) — {ma}: {_fmt(row.get('value_a',0), ma)} | {mb}: {_fmt(row.get('value_b',0), mb)}")
        n_excl = len(result.get("lp_outliers_df", pd.DataFrame()))
        if n_excl > 0:
            lines.append(f"\nℹ️ *{n_excl} zona(s) con Lead Penetration ≥ 2.0 excluidas (conteos absolutos, no ratios).*")
        lines.append(f"\nEstas zonas tienen buena oferta pero calidad de entrega por debajo del umbral — oportunidad de intervención.")
        return "\n".join(lines)

    if intent == "growth_explanation":
        min_base = result.get("min_base", 50)
        lines = [f"**Zonas con mayor crecimiento en órdenes{fn}:**"]
        for _, row in df.head(5).iterrows():
            lines.append(
                f"• **{row['ZONE']}** ({row.get('COUNTRY','')}) — "
                f"{row.get('growth_pct',0):+.1%} "
                f"({int(row.get('orders_start',0)):,} → {int(row.get('orders_end',0)):,} órdenes)"
            )
        lines.append(f"\nℹ️ *Se excluyeron zonas con base reciente menor a {min_base} órdenes para evitar crecimientos espurios.*")
        lines.append("*Las métricas correlacionadas son hipótesis asociativas, no causalidad.*")
        return "\n".join(lines)

    return f"Análisis completado. {len(df)} resultados encontrados."


def generate_suggestions(intent: str, result: dict, parsed_query: dict) -> list:
    metric  = result.get("metric") or parsed_query.get("metric", "")
    filters = parsed_query.get("filters", {})
    country = filters.get("country") or ""

    # Short labels: max ~35 chars for clean button display
    if intent == "ranking":
        return [
            "Ver evolución 8 semanas",
            "Comparar Wealthy vs Non Wealthy",
            f"Filtrar a {'otro país' if country else 'Colombia'}",
        ]
    if intent in ("comparison", "aggregation"):
        return [
            f"Top 5 zonas por {metric[:20]}",
            "Ver tendencia 8 semanas",
            "Comparar por país",
        ]
    if intent == "trend":
        return [
            "Cruzar con volumen de órdenes",
            "Zonas con mayor deterioro",
            "Ver misma métrica otro país",
        ]
    if intent == "multivariable":
        return [
            "¿Cuántas son High Priority?",
            "Ver tendencia 5 semanas",
            "Comparar vs promedio de país",
        ]
    if intent == "growth_explanation":
        return [
            "Ver Perfect Orders en estas zonas",
            "Zonas con mayor deterioro",
            "Comparar por tipo de zona",
        ]
    return [
        f"Ranking de {metric[:20]}",
        "Comparar Wealthy vs Non Wealthy",
        "Ver tendencia temporal",
    ]
