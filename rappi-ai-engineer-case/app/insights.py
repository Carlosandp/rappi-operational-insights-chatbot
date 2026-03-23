"""
insights.py — Automatic insight generation engine.
100% deterministic. No LLM.

Fixes applied:
- Anomaly detection uses dual-threshold (relative AND absolute) to avoid near-zero artifacts
- Benchmarking excludes data quality outliers (metric values out of expected range)
- Opportunities use peer-group context (same country + zone_type)
- Data quality alerts are a distinct category
- Top-5 executive summary is diversified across categories
"""

import numpy as np
import pandas as pd

from semantic_layer import is_higher_better
from utils import WEEK_LABELS, load_metric_dictionary


# ── Metric range validation ──────────────────────────────────────────────
# Define expected ranges; values outside are data quality issues
METRIC_EXPECTED_RANGES = {
    "Lead Penetration":                              (0, 2.0),   # ratio, can be > 1
    "Perfect Orders":                                (0, 1.0),
    "Gross Profit UE":                               (-100, 15), # audit: min=-97.1, max=12.8 — negatives are valid
    "Pro Adoption (Last Week Status)":               (0, 1.0),
    "% PRO Users Who Breakeven":                     (0, 1.0),
    "MLTV Top Verticals Adoption":                   (0, 1.0),
    "Restaurants SS > ATC CVR":                      (0, 1.0),
    "Restaurants SST > SS CVR":                      (0, 1.0),
    "Retail SST > SS CVR":                           (0, 1.0),
    "% Restaurants Sessions With Optimal Assortment":(0, 1.0),
    "Non-Pro PTC > OP":                              (0, 1.0),
    "Turbo Adoption":                                (0, 1.0),
    "Restaurants Markdowns / GMV":                   (0, 0.50),  # audit: max=0.43
    "Orders":                                        (0, 1e8),
}

# Absolute minimum change to flag as anomaly (prevents near-zero denominator artifacts)
METRIC_MIN_ABS_CHANGE = {
    "Lead Penetration":      0.02,   # 2 percentage points minimum
    "Perfect Orders":        0.02,
    "Gross Profit UE":       1.00,   # 1 unit minimum to avoid near-zero artifacts
    "Pro Adoption (Last Week Status)": 0.01,
    "% PRO Users Who Breakeven": 0.01,
    "MLTV Top Verticals Adoption": 0.01,
    "Restaurants SS > ATC CVR": 0.02,
    "Restaurants SST > SS CVR": 0.02,
    "Retail SST > SS CVR":   0.02,
    "% Restaurants Sessions With Optimal Assortment": 0.02,
    "Non-Pro PTC > OP":      0.02,
    "Turbo Adoption":        0.01,
    "Restaurants Markdowns / GMV": 0.02,
    "Orders":                10,     # at least 10 orders change
}


def _is_data_quality_issue(metric: str, value: float) -> bool:
    """Return True if value is outside expected range for the metric.
    Lead Penetration uses a strict upper bound (<2.0) so LP=2.0 exactly is flagged.
    All other metrics use inclusive upper bound to allow valid boundary values (e.g. PO=1.0).
    """
    if pd.isna(value):
        return False
    lo, hi = METRIC_EXPECTED_RANGES.get(metric, (-1e9, 1e9))
    if metric == "Lead Penetration":
        return not (lo <= value < hi)   # strict — LP=2.0 is a store count, not a ratio
    return not (lo <= value <= hi)      # inclusive for all other metrics


# Metrics for which we report the absolute delta instead of % WoW.
# Used when the base can be near-zero (e.g. GP UE crosses zero),
# making percentage changes meaningless or astronomically large.
METRIC_USE_ABSOLUTE_DELTA = {"Gross Profit UE"}

# Minimum absolute delta required to flag a GP UE anomaly (same unit as metric).
# GP UE range ≈ -97 to +13; a 2-unit absolute swing is meaningful.
GP_UE_MIN_ABS_ANOMALY = 1.5


def _robust_pct_change(v_from: float, v_to: float, metric: str) -> float | None:
    """
    Compute percentage change with dual guard.
    - GP UE: uses absolute delta normalised to range width to avoid
      astronomical percentages when base is near zero.
    - Other metrics: denominator floor prevents division by near-zero.
    Returns None if change is below minimum meaningful threshold.
    """
    if pd.isna(v_from) or pd.isna(v_to):
        return None

    abs_change = abs(v_to - v_from)
    min_abs = METRIC_MIN_ABS_CHANGE.get(metric, 0)
    if abs_change < min_abs:
        return None

    # GP UE special path: avoid extreme % when base crosses or is near zero
    if metric in METRIC_USE_ABSOLUTE_DELTA:
        if abs_change < GP_UE_MIN_ABS_ANOMALY:
            return None
        # Normalise to range width (~110 units) so result stays in a [-1,+1] scale
        RANGE_WIDTH = 110.0
        sign = 1 if (v_to - v_from) > 0 else -1
        return sign * abs_change / RANGE_WIDTH

    # Standard path
    from semantic_layer import load_metric_dictionary
    try:
        unit = load_metric_dictionary()["metrics"].get(metric, {}).get("unit", "ratio")
    except Exception:
        unit = "ratio"
    floor = 1.0 if unit == "count" else 0.001
    denom = max(abs(v_from), floor)
    return (v_to - v_from) / denom


# ── A. Anomaly detection ─────────────────────────────────────────────────
def detect_anomalies(
    df_metrics_wide: pd.DataFrame,
    df_orders_wide: pd.DataFrame,
    threshold: float = 0.10,
    from_week: str = "L1W",
    to_week: str = "L0W",
    top_n: int = 10,
) -> list[dict]:
    results = []

    # For metrics that use absolute-delta normalisation (GP UE), the normalised
    # value represents abs_delta/RANGE_WIDTH. A 1.5-unit move over a 110-unit range
    # = 0.0136. We use a lower threshold for these metrics so meaningful absolute
    # swings are not filtered out by the standard 10% relative threshold.
    GP_UE_NORM_THRESHOLD = GP_UE_MIN_ABS_ANOMALY / 110.0   # ~0.0136 for 1.5 units

    def _process(df, is_orders=False):
        for _, row in df.iterrows():
            metric = row.get("METRIC", "Orders") if is_orders else row.get("METRIC", "")
            v_from = row.get(from_week)
            v_to = row.get(to_week)

            # Skip data quality outliers from anomaly detection
            if _is_data_quality_issue(metric, v_from) or _is_data_quality_issue(metric, v_to):
                continue

            pct = _robust_pct_change(v_from, v_to, metric)
            # Use a lower threshold for GP UE (normalised absolute-delta path)
            effective_threshold = GP_UE_NORM_THRESHOLD if metric in METRIC_USE_ABSOLUTE_DELTA else threshold
            if pct is None or abs(pct) < effective_threshold:
                continue
            # Cap extreme pct changes for display — only relevant for standard ratio metrics
            pct = max(min(pct, 5.0), -5.0)

            higher_better = is_higher_better(metric)
            is_deterioration = (pct < 0) if higher_better else (pct > 0)

            results.append({
                "type": "anomaly",
                "category": "Deterioro" if is_deterioration else "Mejora",
                "zone": row.get("ZONE", ""),
                "country": row.get("COUNTRY", ""),
                "city": row.get("CITY", ""),
                "zone_type": row.get("ZONE_TYPE", ""),
                "zone_prioritization": row.get("ZONE_PRIORITIZATION", ""),
                "metric": metric,
                "value_from": v_from,
                "value_to": v_to,
                "pct_change": pct,
                "severity": "alta" if abs(pct) > 0.20 else "media",
            })

    _process(df_metrics_wide)
    _process(df_orders_wide, is_orders=True)

    # Sort by deterioration first, then by magnitude.
    # For GP UE the pct_change is a normalised value (not a true %), so it would
    # rank below other metrics. To ensure GP UE anomalies appear we use a
    # two-pass approach: first fill the top-N with the highest-magnitude results
    # across all metrics, then guarantee at least min_gp_ue GP UE entries.
    results_sorted = sorted(
        results,
        key=lambda x: (x["category"] == "Deterioro", abs(x["pct_change"])),
        reverse=True,
    )
    # Reserve slots for GP UE so it always has representation
    min_gp_ue = 3
    gp_ue_results = [r for r in results_sorted if r["metric"] in METRIC_USE_ABSOLUTE_DELTA]
    other_results  = [r for r in results_sorted if r["metric"] not in METRIC_USE_ABSOLUTE_DELTA]

    final = other_results[: top_n * 2 - min(min_gp_ue, len(gp_ue_results))]
    final += gp_ue_results[:min_gp_ue]
    # Re-sort the combined list
    final = sorted(final, key=lambda x: (x["category"] == "Deterioro", abs(x["pct_change"])), reverse=True)
    return final[: top_n * 2]


# ── B. Consistent deterioration ─────────────────────────────────────────
def detect_consistent_trends(
    df_metrics_wide: pd.DataFrame,
    min_weeks: int = 3,
    top_n: int = 10,
) -> list[dict]:
    results = []

    for _, row in df_metrics_wide.iterrows():
        metric = row["METRIC"]
        higher_better = is_higher_better(metric)

        # Skip if current value is a data quality issue
        if _is_data_quality_issue(metric, row.get("L0W")):
            continue

        consecutive = 0
        max_consecutive = 0
        det_start = None
        det_end = None

        for i in range(8, 0, -1):
            w_prev, w_curr = f"L{i}W", f"L{i-1}W"
            v_prev, v_curr = row.get(w_prev), row.get(w_curr)
            if pd.isna(v_prev) or pd.isna(v_curr) or v_prev == 0:
                consecutive = 0
                continue

            deteriorated = (v_curr < v_prev) if higher_better else (v_curr > v_prev)
            if deteriorated:
                if consecutive == 0:
                    det_start = v_prev
                consecutive += 1
                det_end = v_curr
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0

        if max_consecutive >= min_weeks and det_start:
            total_change = (det_end - det_start) / abs(det_start)
            results.append({
                "type": "consistent_deterioration",
                "category": "Tendencia Preocupante",
                "zone": row["ZONE"],
                "country": row["COUNTRY"],
                "city": row.get("CITY", ""),
                "zone_type": row.get("ZONE_TYPE", ""),
                "zone_prioritization": row.get("ZONE_PRIORITIZATION", ""),
                "metric": metric,
                "consecutive_weeks": max_consecutive,
                "total_pct_change": total_change,
                "current_value": row.get("L0W"),
                "severity": "alta" if max_consecutive >= 5 else "media",
            })

    return sorted(results, key=lambda x: x["consecutive_weeks"], reverse=True)[:top_n]


# ── C. Benchmarking (peers only, no outliers) ────────────────────────────
def detect_benchmarking_outliers(
    df_metrics_wide: pd.DataFrame,
    metric: str = "Perfect Orders",
    week: str = "L0W",
    z_threshold: float = 1.5,
    top_n: int = 10,
) -> list[dict]:
    results = []
    df = df_metrics_wide[df_metrics_wide["METRIC"] == metric].copy()
    if week not in df.columns or df.empty:
        return []

    df = df.dropna(subset=[week])

    # Exclude data quality outliers BEFORE computing peer stats.
    # Note: _is_data_quality_issue uses strict upper bound (<hi), so LP=2.0 is excluded.
    df = df[~df[week].apply(lambda v: _is_data_quality_issue(metric, v))]

    group_cols = ["COUNTRY", "ZONE_TYPE"]
    df["group_mean"] = df.groupby(group_cols)[week].transform("mean")
    df["group_std"] = df.groupby(group_cols)[week].transform("std")
    df["group_count"] = df.groupby(group_cols)[week].transform("count")
    df["z_score"] = (df[week] - df["group_mean"]) / (df["group_std"] + 1e-9)

    outliers = df[(df["z_score"].abs() >= z_threshold) & (df["group_count"] >= 3)].copy()
    higher_better = is_higher_better(metric)

    for _, row in outliers.iterrows():
        is_under = (row["z_score"] < 0 and higher_better) or (row["z_score"] > 0 and not higher_better)
        results.append({
            "type": "benchmarking",
            "category": "Benchmarking",
            "zone": row["ZONE"],
            "country": row["COUNTRY"],
            "city": row.get("CITY", ""),
            "zone_type": row.get("ZONE_TYPE", ""),
            "zone_prioritization": row.get("ZONE_PRIORITIZATION", ""),
            "metric": metric,
            "current_value": row[week],
            "group_mean": row["group_mean"],
            "z_score": row["z_score"],
            "performance": "underperformer" if is_under else "outperformer",
            "severity": "alta" if abs(row["z_score"]) >= 2.0 else "media",
        })

    return sorted(results, key=lambda x: abs(x["z_score"]), reverse=True)[:top_n]


# ── D. Correlations ──────────────────────────────────────────────────────
def detect_correlations(
    df_metrics_wide: pd.DataFrame,
    week: str = "L0W",
    top_n: int = 5,
) -> list[dict]:
    results = []
    if week not in df_metrics_wide.columns:
        return []

    pivot = df_metrics_wide.pivot_table(
        index=["COUNTRY", "CITY", "ZONE"],
        columns="METRIC",
        values=week,
        aggfunc="first",
    ).dropna(how="all")

    if pivot.shape[1] < 2:
        return []

    # Remove columns with data quality issues before correlating
    clean_cols = []
    for col in pivot.columns:
        lo, hi = METRIC_EXPECTED_RANGES.get(col, (-1e9, 1e9))
        col_clean = pivot[col].dropna()
        if len(col_clean) > 10 and col_clean.between(lo, hi).mean() > 0.9:
            clean_cols.append(col)
    pivot = pivot[clean_cols]

    corr_matrix = pivot.corr(method="pearson")
    for i, m1 in enumerate(corr_matrix.columns):
        for j, m2 in enumerate(corr_matrix.columns):
            if j <= i:
                continue
            corr_val = corr_matrix.loc[m1, m2]
            if pd.isna(corr_val) or abs(corr_val) < 0.5:
                continue
            results.append({
                "type": "correlation",
                "category": "Correlación",
                "metric_a": m1,
                "metric_b": m2,
                "correlation": corr_val,
                "direction": "positiva" if corr_val > 0 else "negativa",
                "severity": "alta" if abs(corr_val) >= 0.7 else "media",
                "interpretation": (
                    f"Zonas con alto {m1} tienden a tener "
                    f"{'también alto' if corr_val > 0 else 'bajo'} {m2}"
                ),
            })

    return sorted(results, key=lambda x: abs(x["correlation"]), reverse=True)[:top_n]


# ── E. Opportunities (peer-group context) ────────────────────────────────
def detect_opportunities(
    df_metrics_wide: pd.DataFrame,
    df_orders_wide: pd.DataFrame,
    week: str = "L0W",
    n_weeks_growth: int = 4,
    min_orders_base: int = 50,   # ignore micro-zones
    top_n: int = 8,
) -> list[dict]:
    results = []
    df_lead = df_metrics_wide[df_metrics_wide["METRIC"] == "Lead Penetration"].copy()
    df_perf = df_metrics_wide[df_metrics_wide["METRIC"] == "Perfect Orders"].copy()
    df_ord = df_orders_wide.copy()

    if week not in df_lead.columns:
        return []

    id_cols = ["COUNTRY", "CITY", "ZONE"]
    df_lead = df_lead[id_cols + [week, "ZONE_TYPE", "ZONE_PRIORITIZATION"]].rename(columns={week: "lead_pen"})
    df_perf = df_perf[id_cols + [week]].rename(columns={week: "perfect_orders"})

    start_col = f"L{n_weeks_growth}W"
    merged = df_lead.merge(df_perf, on=id_cols, how="inner")
    merged = merged.dropna(subset=["lead_pen", "perfect_orders"])

    # Filter data quality outliers — strict upper bound means LP=2.0 is excluded here too
    merged = merged[~merged["lead_pen"].apply(lambda v: _is_data_quality_issue("Lead Penetration", v))]
    merged = merged[~merged["perfect_orders"].apply(lambda v: _is_data_quality_issue("Perfect Orders", v))]

    # Orders growth
    if start_col in df_ord.columns and "L0W" in df_ord.columns:
        df_ord_g = df_ord[id_cols + [start_col, "L0W"]].copy().dropna()
        df_ord_g = df_ord_g[df_ord_g[start_col] >= min_orders_base]  # filter micro-zones
        df_ord_g = df_ord_g[df_ord_g[start_col] > 0]
        df_ord_g["order_growth"] = (df_ord_g["L0W"] - df_ord_g[start_col]) / df_ord_g[start_col].abs()
        df_ord_g["orders_base"] = df_ord_g[start_col]
        merged = merged.merge(df_ord_g[id_cols + ["order_growth", "orders_base"]], on=id_cols, how="left")

    # Use PEER-GROUP percentiles (same country + zone_type) instead of global
    merged["peer_key"] = merged["COUNTRY"] + "_" + merged["ZONE_TYPE"].fillna("unknown")
    merged["lead_peer_p75"] = merged.groupby("peer_key")["lead_pen"].transform(lambda x: x.quantile(0.75))
    merged["perf_peer_p40"] = merged.groupby("peer_key")["perfect_orders"].transform(lambda x: x.quantile(0.40))

    opps = merged[
        (merged["lead_pen"] >= merged["lead_peer_p75"]) &
        (merged["perfect_orders"] < merged["perf_peer_p40"])
    ].copy()

    if "order_growth" in opps.columns:
        opps = opps[opps["order_growth"] > 0]
        opps = opps.sort_values("order_growth", ascending=False)

    for _, row in opps.head(top_n).iterrows():
        growth_str = f"{row['order_growth']:+.1%}" if pd.notna(row.get("order_growth")) else "N/A"
        base_str = f"{int(row['orders_base']):,}" if pd.notna(row.get("orders_base")) else "N/A"
        peer_perfect_median = row.get("perf_peer_p40", 0)
        results.append({
            "type": "opportunity",
            "category": "Oportunidad",
            "zone": row["ZONE"],
            "country": row["COUNTRY"],
            "city": row.get("CITY", ""),
            "zone_type": row.get("ZONE_TYPE", ""),
            "zone_prioritization": row.get("ZONE_PRIORITIZATION", ""),
            "lead_penetration": row["lead_pen"],
            "perfect_orders": row["perfect_orders"],
            "peer_perfect_threshold": peer_perfect_median,
            "order_growth": row.get("order_growth", np.nan),
            "orders_base": row.get("orders_base", np.nan),
            "severity": "media",
            "interpretation": (
                f"Alta oferta vs. pares ({row['COUNTRY']}/{row.get('ZONE_TYPE','')}) — "
                f"Lead Pen: {row['lead_pen']:.1%}, Perfect Orders: {row['perfect_orders']:.1%} "
                f"(umbral peers: {peer_perfect_median:.1%}). "
                f"Crecimiento órdenes ({n_weeks_growth}w): {growth_str} sobre base de {base_str} órdenes."
            ),
        })

    return results


# ── F. Data quality alerts ───────────────────────────────────────────────
def detect_data_quality_issues(
    df_metrics_wide: pd.DataFrame,
    df_orders_wide: pd.DataFrame,
    week: str = "L0W",
) -> list[dict]:
    """Flag metric values outside expected ranges as data quality issues."""
    results = []

    for _, row in df_metrics_wide.iterrows():
        metric = row["METRIC"]
        val = row.get(week)
        if pd.isna(val):
            continue
        if _is_data_quality_issue(metric, val):
            lo, hi = METRIC_EXPECTED_RANGES.get(metric, (-1e9, 1e9))
            results.append({
                "type": "data_quality",
                "category": "Calidad de Datos",
                "zone": row["ZONE"],
                "country": row["COUNTRY"],
                "city": row.get("CITY", ""),
                "metric": metric,
                "value": val,
                "expected_range": f"[{lo}, {hi}]",
                "severity": "alta" if val > hi * 2 or val < lo * 2 else "media",
            })

    return results[:20]


# ── Master runner ─────────────────────────────────────────────────────────
def generate_all_insights(
    df_metrics_wide: pd.DataFrame,
    df_orders_wide: pd.DataFrame,
) -> dict:
    anomalies = detect_anomalies(df_metrics_wide, df_orders_wide, threshold=0.10)
    trends = detect_consistent_trends(df_metrics_wide, min_weeks=3)
    benchmarks = []
    for metric in ["Perfect Orders", "Lead Penetration", "Gross Profit UE"]:
        benchmarks.extend(detect_benchmarking_outliers(df_metrics_wide, metric=metric, top_n=5))
    correlations = detect_correlations(df_metrics_wide)
    opportunities = detect_opportunities(df_metrics_wide, df_orders_wide)
    data_quality = detect_data_quality_issues(df_metrics_wide, df_orders_wide)

    return {
        "anomalies": anomalies,
        "trends": trends,
        "benchmarks": benchmarks,
        "correlations": correlations,
        "opportunities": opportunities,
        "data_quality": data_quality,
        "total": len(anomalies) + len(trends) + len(benchmarks) + len(correlations) + len(opportunities),
    }


# ── Format insight card ───────────────────────────────────────────────────
_METRIC_RECOMMENDATIONS = {
    "Perfect Orders": "revisar tasa de defectos, cancelaciones y SLA de entrega",
    "Lead Penetration": "revisar habilitación de tiendas y densidad de oferta en la zona",
    "Gross Profit UE": "revisar mix de productos, descuentos aplicados y costos logísticos",
    "Restaurants SS > ATC CVR": "revisar catálogo, fotos y pricing en restaurantes",
    "Restaurants SST > SS CVR": "revisar relevancia del listado y posicionamiento de tiendas",
    "Retail SST > SS CVR": "revisar disponibilidad y presentación de supermercados",
    "Pro Adoption (Last Week Status)": "revisar comunicación y beneficios del programa Pro",
    "Turbo Adoption": "revisar cobertura y visibilidad del servicio Turbo",
    "Non-Pro PTC > OP": "revisar el funnel de checkout y posibles fricciones de pago",
}


def format_insight_card(insight: dict) -> dict:
    itype = insight.get("type")
    zone = insight.get("zone", "")
    metric = insight.get("metric", "")
    country = insight.get("country", "")
    metric_action = _METRIC_RECOMMENDATIONS.get(metric, "revisar operaciones y datos de la zona")

    if itype == "anomaly":
        pct = insight.get("pct_change", 0)
        cat = insight.get("category", "")
        metric = insight.get("metric", "")
        v_from = insight.get("value_from", 0)
        v_to = insight.get("value_to", 0)
        # For GP UE: pct_change is a normalised value, not a true %. Show absolute delta instead.
        if metric in METRIC_USE_ABSOLUTE_DELTA:
            abs_delta = abs(v_to - v_from)
            direction = "cayó" if (v_to - v_from) < 0 else "subió"
            change_str = f"{direction} {abs_delta:.2f} unidades ({v_from:.2f} → {v_to:.2f})"
        else:
            change_str = f"cambió {pct:+.1%} WoW ({v_from:.3f} → {v_to:.3f})"
        return {
            "title": f"{cat} brusca en {metric} — {zone} ({country})",
            "category": "🚨 Anomalía",
            "evidence": f"{metric} {change_str} en {zone}.",
            "why_it_matters": ("Un cambio abrupto puede indicar un problema operacional puntual "
                                "o una mejora inesperada que merece seguimiento."),
            "recommendation": (
                f"{'Investigar causa del deterioro' if cat == 'Deterioro' else 'Validar y capitalizar la mejora'} "
                f"en {zone}: {metric_action}."
            ),
            "severity": insight.get("severity", "media"),
        }

    elif itype == "consistent_deterioration":
        n = insight.get("consecutive_weeks", 0)
        total = insight.get("total_pct_change", 0)
        return {
            "title": f"Deterioro sostenido de {metric} — {zone} ({country})",
            "category": "📉 Tendencia Preocupante",
            "evidence": (f"{metric} ha caído {n} semanas consecutivas en {zone} ({country}). "
                         f"Cambio acumulado: {total:+.1%}. Valor actual: {insight.get('current_value', 0):.3f}."),
            "why_it_matters": (f"Un deterioro de {n}+ semanas sugiere un problema estructural, "
                                "no un evento puntual. Puede afectar retención y GMV."),
            "recommendation": f"Priorizar revisión en {zone}: {metric_action}.",
            "severity": insight.get("severity", "media"),
        }

    elif itype == "benchmarking":
        perf = insight.get("performance", "underperformer")
        z = insight.get("z_score", 0)
        gm = insight.get("group_mean", 0)
        curr = insight.get("current_value", 0)
        return {
            "title": f"{'Sub' if perf == 'underperformer' else 'Sobre'}performance en {metric} — {zone} ({country})",
            "category": "📊 Benchmarking",
            "evidence": (f"{zone}: {metric} = {curr:.3f} vs. promedio de pares "
                         f"({insight.get('zone_type', '')}, {country}) = {gm:.3f}. Z-score: {z:+.2f}."),
            "why_it_matters": "La divergencia respecto a pares puede revelar prácticas o condiciones específicas.",
            "recommendation": (
                f"{'Investigar qué falla en' if perf == 'underperformer' else 'Identificar best practices de'} "
                f"{zone} y replicar al resto del grupo: {metric_action}."
            ),
            "severity": insight.get("severity", "media"),
        }

    elif itype == "correlation":
        corr = insight.get("correlation", 0)
        return {
            "title": f"Correlación {insight.get('direction','')} entre {insight.get('metric_a','')} y {insight.get('metric_b','')}",
            "category": "🔗 Correlación",
            "evidence": f"Correlación Pearson = {corr:.2f} ({abs(corr):.0%} de fuerza asociativa).",
            "why_it_matters": insight.get("interpretation", ""),
            "recommendation": ("Usar esta relación para priorizar intervenciones: "
                                "mejorar la métrica palanca puede impactar ambas simultáneamente."),
            "severity": insight.get("severity", "media"),
        }

    elif itype == "opportunity":
        return {
            "title": f"Oportunidad de mejora en calidad — {zone} ({country})",
            "category": "🌟 Oportunidad",
            "evidence": insight.get("interpretation", ""),
            "why_it_matters": ("Esta zona tiene buena oferta y demanda creciente, "
                                "pero calidad por debajo de sus pares. Mejorar Perfect Orders "
                                "aquí puede amplificar el crecimiento."),
            "recommendation": f"Activar plan de calidad en {zone}: {metric_action}.",
            "severity": "media",
        }

    elif itype == "data_quality":
        val = insight.get("value", 0)
        exp = insight.get("expected_range", "")
        return {
            "title": f"Valor fuera de rango: {metric} = {val:.3f} en {zone} ({country})",
            "category": "⚠️ Calidad de Datos",
            "evidence": f"{metric} reporta {val:.3f} en {zone}. Rango esperado: {exp}.",
            "why_it_matters": "Valores fuera de rango pueden distorsionar benchmarks, correlaciones y rankings.",
            "recommendation": f"Validar fuente de datos para {zone} — {metric}. Excluir de análisis comparativos hasta confirmar.",
            "severity": insight.get("severity", "media"),
        }

    return {"title": "Insight", "category": "General", "evidence": str(insight),
            "why_it_matters": "", "recommendation": "", "severity": "media"}
