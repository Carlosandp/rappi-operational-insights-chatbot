"""
charts.py — Plotly chart generation.
Formatting is driven by metric_dictionary.json unit field — not ad-hoc heuristics.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Theme tokens are applied via apply_plotly_theme() from ui_theme
# Charts use a standalone fallback palette so they work without the Streamlit context
_DARK_TEXT  = "#1F2937"
_DARK_MUTED = "#374151"
_GRID_COLOR = "#E5E7EB"
_BORDER     = "#D1D5DB"

RAPPI_ORANGE = "#FF5A3D"
CHART_COLORS = ["#FF441F", "#F7931E", "#2D9CDB", "#27AE60", "#9B59B6", "#E74C3C", "#1ABC9C"]
LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=12, color=_DARK_TEXT),
    margin=dict(l=40, r=20, t=55, b=40),
    title_font_color=_DARK_TEXT,
    legend=dict(font=dict(color=_DARK_TEXT), bgcolor="rgba(0,0,0,0)"),
)

AXIS_STYLE = dict(color=_DARK_MUTED, gridcolor=_GRID_COLOR, linecolor=_BORDER, zerolinecolor=_BORDER)

# ── Metric unit registry (canonical source) ──────────────────────────────
METRIC_UNITS = {
    "Lead Penetration": "ratio",
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

# Lead Penetration can exceed 1.0 — display as decimal, not percentage
RATIO_DISPLAY_AS_DECIMAL = {"Lead Penetration"}


def _fmt_val(val: float, metric: str) -> str:
    """Format a single value using the metric's unit type."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    unit = METRIC_UNITS.get(metric, "ratio")
    if unit == "count":
        return f"{val:,.0f}"
    elif unit == "currency":
        return f"${val:,.2f}"
    elif metric in RATIO_DISPLAY_AS_DECIMAL:
        # Lead Penetration: show as decimal ratio (can exceed 1)
        return f"{val:.2f}"
    else:
        # Standard ratio: show as percentage
        return f"{val:.1%}"


def _axis_fmt(metric: str) -> dict:
    """Return Plotly tickformat for a metric's axis."""
    unit = METRIC_UNITS.get(metric, "ratio")
    if unit == "count":
        return {"tickformat": ",.0f"}
    elif unit == "currency":
        return {"tickprefix": "$", "tickformat": ",.2f"}
    elif metric in RATIO_DISPLAY_AS_DECIMAL:
        return {"tickformat": ".2f"}
    else:
        return {"tickformat": ".1%"}


def _empty_chart(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False,
                       font=dict(size=14, color="gray"))
    fig.update_layout(**LAYOUT_BASE, height=280)
    return fig


# ── 1. Ranking ──────────────────────────────────────────────────────────
def chart_ranking(result: dict) -> go.Figure:
    df = result.get("data", pd.DataFrame())
    if df.empty:
        return _empty_chart("No data available")

    metric = result.get("metric", "")
    week = result.get("week", "L0W")
    df = df.copy()
    df["label"] = df["value"].apply(lambda v: _fmt_val(v, metric))

    fig = px.bar(
        df, x="value", y="ZONE", orientation="h",
        color="value",
        color_continuous_scale=[[0, "#FFE5DE"], [1, RAPPI_ORANGE]],
        text="label",
        hover_data=["COUNTRY", "CITY"] if "COUNTRY" in df.columns else None,
    )
    fig.update_traces(textposition="outside", showlegend=False)
    fig.update_coloraxes(showscale=False)
    fig.update_layout(
        **LAYOUT_BASE,
        title=f"<b>Top {len(df)} — {metric}</b><br><sup>Semana: {week}</sup>",
        xaxis=dict(title=metric, **_axis_fmt(metric), **AXIS_STYLE),
        yaxis=dict(title="Zona", categoryorder="total ascending", **AXIS_STYLE),
        height=max(300, len(df) * 65),
    )
    return fig


# ── 2. Comparison ────────────────────────────────────────────────────────
def chart_comparison(result: dict) -> go.Figure:
    df = result.get("data", pd.DataFrame())
    if df.empty:
        return _empty_chart("No data available")

    metric = result.get("metric", "")
    group_by = result.get("group_by", "group")
    week = result.get("week", "L0W")
    df = df.copy()
    df["label"] = df["value"].apply(lambda v: _fmt_val(v, metric))

    fig = px.bar(
        df, x="group", y="value", color="group",
        color_discrete_sequence=CHART_COLORS,
        text="label",
        hover_data=["n_zones"] if "n_zones" in df.columns else None,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        **LAYOUT_BASE,
        title=f"<b>{metric} por {group_by}</b><br><sup>Semana: {week} | Agg: {result.get('agg','mean')}</sup>",
        xaxis=dict(title=str(group_by).replace("_", " ").title(), **AXIS_STYLE),
        yaxis=dict(title=f"Avg {metric}", **_axis_fmt(metric), **AXIS_STYLE),
        showlegend=False,
        height=400,
    )
    return fig


# ── 3. Trend ─────────────────────────────────────────────────────────────
def chart_trend(result: dict) -> go.Figure:
    df = result.get("data", pd.DataFrame())
    if df.empty:
        return _empty_chart("No data available")

    metric  = result.get("metric", "")
    filters = result.get("filters", {})
    zone_label = filters.get("zone") or filters.get("city") or filters.get("country") or "Todas las zonas"
    # Capitalize first letter for display
    if zone_label:
        zone_label = str(zone_label).title()
    df = df.sort_values("week_index")

    fig = go.Figure()
    multi_zone = "ZONE" in df.columns and df["ZONE"].nunique() > 1

    if multi_zone:
        for i, zone in enumerate(df["ZONE"].unique()):
            z_df = df[df["ZONE"] == zone]
            fig.add_trace(go.Scatter(
                x=z_df["week_label"], y=z_df["value"],
                mode="lines+markers", name=zone,
                line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=2),
                marker=dict(size=7),
            ))
    else:
        fig.add_trace(go.Scatter(
            x=df["week_label"], y=df["value"],
            mode="lines+markers", name=metric,
            line=dict(color=RAPPI_ORANGE, width=3),
            marker=dict(size=9),
            showlegend=False,
        ))
        # WoW annotations
        if "wow_change" in df.columns:
            for _, row in df.iterrows():
                if pd.notna(row.get("wow_change")):
                    color = "#27AE60" if row["wow_change"] > 0 else "#E74C3C"
                    fig.add_annotation(
                        x=row["week_label"], y=row["value"],
                        text=f"{row['wow_change']:+.1%}",
                        showarrow=False, yshift=16,
                        font=dict(size=10, color=color),
                    )

    week_order = [f"L{i}W" for i in range(8, -1, -1)]
    present    = [w for w in week_order if w in df["week_label"].values]

    # Build layout without duplicate legend key
    # LAYOUT_BASE has legend already; we update it explicitly via update_layout(legend=...)
    # to avoid Plotly raising on duplicate keys in older/newer versions
    layout = dict(LAYOUT_BASE)
    layout.pop("legend", None)   # remove base legend; set it cleanly below

    fig.update_layout(
        **layout,
        title=f"<b>Tendencia: {metric}</b><br><sup>{zone_label}</sup>",
        xaxis=dict(title="Semana", categoryorder="array", categoryarray=present, **AXIS_STYLE),
        yaxis=dict(title=metric, **_axis_fmt(metric), **AXIS_STYLE),
        height=420,
        showlegend=multi_zone,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            font=dict(color=_DARK_TEXT), bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


# ── 4. Multivariable scatter ─────────────────────────────────────────────
def chart_multivariable(result: dict) -> go.Figure:
    df = result.get("data", pd.DataFrame())
    if df.empty:
        return _empty_chart("No zones match the criteria")

    metric_a = result.get("metric_a", "")
    metric_b = result.get("metric_b", "")

    fig = px.scatter(
        df, x="value_a", y="value_b", text="ZONE",
        color="COUNTRY" if "COUNTRY" in df.columns else None,
        color_discrete_sequence=CHART_COLORS,
        hover_data=["COUNTRY", "CITY"] if "COUNTRY" in df.columns else None,
    )
    fig.update_traces(textposition="top center", marker=dict(size=12))
    fig.add_vline(x=result.get("threshold_a", df["value_a"].median()),
                  line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_hline(y=result.get("threshold_b", df["value_b"].median()),
                  line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        **LAYOUT_BASE,
        title=f"<b>Alto {metric_a} ↔ Bajo {metric_b}</b>",
        xaxis=dict(title=metric_a, **_axis_fmt(metric_a)),
        yaxis=dict(title=metric_b, **_axis_fmt(metric_b)),
        height=460,
    )
    return fig


# ── 5. Growth ────────────────────────────────────────────────────────────
def chart_growth(result: dict) -> go.Figure:
    df = result.get("data", pd.DataFrame())
    if df.empty:
        return _empty_chart("No data available")

    n_weeks = result.get("n_weeks", 5)
    df = df.copy().sort_values("growth_pct", ascending=True)
    df["label"] = df["growth_pct"].apply(lambda v: f"{v:+.1%}")
    colors = [RAPPI_ORANGE if v > 0 else "#E74C3C" for v in df["growth_pct"]]

    fig = go.Figure(go.Bar(
        x=df["growth_pct"], y=df["ZONE"], orientation="h",
        marker_color=colors,
        text=df["label"], textposition="outside",
        hovertemplate="<b>%{y}</b><br>Crecimiento: %{x:.1%}<extra></extra>",
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=f"<b>Crecimiento en Órdenes — últimas {n_weeks} semanas</b>",
        xaxis=dict(title="Crecimiento %", tickformat=".1%", **AXIS_STYLE),
        yaxis=dict(title="Zona", **AXIS_STYLE),
        height=max(300, len(df) * 65),
    )
    return fig


# ── 6. Deterioration heatmap ─────────────────────────────────────────────
def chart_deterioration_heatmap(df_det: pd.DataFrame) -> go.Figure:
    if df_det is None or df_det.empty:
        return _empty_chart("No consistent deterioration detected")

    pivot = df_det.pivot_table(
        index="ZONE", columns="METRIC",
        values="consecutive_deterioration_weeks", fill_value=0,
    )
    pivot = pivot.loc[pivot.max(axis=1).nlargest(20).index]

    fig = px.imshow(
        pivot,
        color_continuous_scale=["white", "#FFE5DE", RAPPI_ORANGE, "#8B0000"],
        aspect="auto", text_auto=True,
    )
    fig.update_layout(
        **LAYOUT_BASE,
        title="<b>Semanas consecutivas de deterioro por zona y métrica</b>",
        xaxis_title="Métrica",
        yaxis_title="Zona",
        height=max(400, len(pivot) * 32),
    )
    return fig
