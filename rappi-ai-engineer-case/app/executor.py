"""
executor.py — Pure pandas/numpy analytical engine.
The LLM never performs calculations. All numbers come from here.

Data quality constants based on audit of actual dataset:
- Lead Penetration > 2.0: 26 zones are store counts (not ratios) → excluded from
  percentile-based thresholds but shown in results with DQ note
- GP UE: range -97 to +12 is valid; negatives = high-subsidy zones
- Orders base filter: minimum 50 orders to avoid micro-zone growth artifacts
"""

import numpy as np
import pandas as pd

from semantic_layer import is_higher_better
from utils import WEEK_LABELS, fmt_change, fmt_value

# ── Data quality constants ────────────────────────────────────────────
# Lead Penetration: values > 2.0 are absolute store counts (not ratios)
# They are valid data but distort ratio-based percentile analysis
LP_OUTLIER_THRESHOLD = 2.0
MIN_ORDERS_BASE = 50   # Minimum orders in start week for growth analysis


# ──────────────────────────────────────────────
# Filter helpers
# ──────────────────────────────────────────────
def _apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply country/city/zone/zone_type/prioritization filters.
    Uses contains() for ZONE to support partial zone-name queries.
    For exact zone matching (trend by zone), use _apply_filters_exact_zone."""
    if not filters:
        return df
    if filters.get("country"):
        df = df[df["COUNTRY"].str.upper() == filters["country"].upper()]
    if filters.get("city"):
        df = df[df["CITY"].str.lower() == filters["city"].lower()]
    if filters.get("zone"):
        df = df[df["ZONE"].str.lower().str.contains(filters["zone"].lower(), regex=False)]
    if filters.get("zone_type"):
        df = df[df["ZONE_TYPE"].str.lower() == filters["zone_type"].lower()]
    if filters.get("prioritization"):
        df = df[df["ZONE_PRIORITIZATION"].str.lower() == filters["prioritization"].lower()]
    return df


def _apply_filters_exact_zone(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Exact-match filter for zone trends.
    Uses equality (not contains) for ZONE to avoid partial-match ambiguity
    when a specific zone is requested in a time-series query.
    """
    if not filters:
        return df
    if filters.get("country"):
        df = df[df["COUNTRY"].str.upper() == str(filters["country"]).upper()]
    if filters.get("city"):
        df = df[df["CITY"].str.lower() == str(filters["city"]).lower()]
    if filters.get("zone"):
        df = df[df["ZONE"].str.lower() == str(filters["zone"]).lower()]
    if filters.get("zone_type") and "ZONE_TYPE" in df.columns:
        df = df[df["ZONE_TYPE"].str.lower() == str(filters["zone_type"]).lower()]
    if filters.get("prioritization") and "ZONE_PRIORITIZATION" in df.columns:
        df = df[df["ZONE_PRIORITIZATION"].str.lower() == str(filters["prioritization"]).lower()]
    return df


def rebuild_trend_from_wide(
    df_metrics_wide: pd.DataFrame,
    df_orders_wide: pd.DataFrame,
    metric: str,
    filters: dict = None,
    start_week: str = "L8W",
    end_week: str = "L0W",
) -> dict:
    """
    Deterministic fallback: rebuild a trend series directly from the wide table.

    Called when the long-table path returns empty — e.g. due to a stale cache,
    a processing edge case, or a chart rendering error that swallowed data.
    Bypasses all intermediate transformations and reads values directly from
    the source wide rows, making it immune to pipeline state issues.
    """
    filters = filters or {}

    if metric == "Orders":
        df = df_orders_wide.copy()
    else:
        df = df_metrics_wide[df_metrics_wide["METRIC"] == metric].copy()

    # Use exact zone match for deterministic results
    if filters.get("zone"):
        df = _apply_filters_exact_zone(df, filters)
    else:
        df = _apply_filters(df, filters)

    if df.empty:
        return {"data": pd.DataFrame(), "metric": metric, "filters": filters,
                "start_week": start_week, "end_week": end_week, "fallback_used": False}

    week_cols = [w for w in WEEK_LABELS if w in df.columns]
    group_cols = [c for c in ["COUNTRY", "CITY", "ZONE", "METRIC"] if c in df.columns]

    # Average duplicate rows defensively
    df = df[group_cols + week_cols].copy()
    df = df.groupby(group_cols, dropna=False)[week_cols].mean().reset_index()

    label_to_idx = {f"L{i}W": 8 - i for i in range(9)}
    start_idx = label_to_idx.get(start_week, 0)
    end_idx   = label_to_idx.get(end_week, 8)
    week_order = [f"L{i}W" for i in range(8, -1, -1)]  # L8W ... L0W

    rows = []
    if filters.get("zone") and len(df) >= 1:
        row = df.iloc[0]
        for wk in week_order:
            if wk not in week_cols:
                continue
            idx = label_to_idx[wk]
            if idx < start_idx or idx > end_idx:
                continue
            val = row.get(wk)
            if pd.isna(val):
                continue
            rows.append({
                "COUNTRY": row.get("COUNTRY"),
                "CITY": row.get("CITY"),
                "ZONE": row.get("ZONE"),
                "week_label": wk,
                "week_index": idx,
                "value": val,
                "has_value": True,
                "metric": metric,
            })
    else:
        for wk in week_order:
            if wk not in week_cols:
                continue
            idx = label_to_idx[wk]
            if idx < start_idx or idx > end_idx:
                continue
            vals = pd.to_numeric(df[wk], errors="coerce").dropna()
            if len(vals) == 0:
                continue
            rows.append({
                "week_label": wk,
                "week_index": idx,
                "value": float(vals.mean()),
                "has_value": True,
                "metric": metric,
            })

    if not rows:
        return {"data": pd.DataFrame(), "metric": metric, "filters": filters,
                "start_week": start_week, "end_week": end_week, "fallback_used": False}

    out = pd.DataFrame(rows).sort_values("week_index").reset_index(drop=True)
    out["wow_change"] = out["value"].pct_change()

    return {"data": out, "metric": metric, "filters": filters,
            "start_week": start_week, "end_week": end_week, "fallback_used": True}


# ──────────────────────────────────────────────
# 3. Trend (time series)
# ──────────────────────────────────────────────
def get_trend(
    df_metrics_long: pd.DataFrame,
    df_orders_long: pd.DataFrame,
    metric: str,
    filters: dict = None,
    start_week: str = "L8W",
    end_week: str = "L0W",
) -> dict:
    """
    Return time series for a metric across weeks.
    Uses exact zone matching when a specific zone is requested
    to avoid partial-match false-negatives.
    """
    filters = filters or {}
    week_order = {f"L{i}W": 8 - i for i in range(9)}
    start_idx = week_order.get(start_week, 0)
    end_idx   = week_order.get(end_week, 8)

    if metric == "Orders":
        df = df_orders_long.copy()
    else:
        df = df_metrics_long[df_metrics_long["METRIC"] == metric].copy()

    # Use exact match for zone-specific trends; flexible match otherwise
    if filters.get("zone"):
        df = _apply_filters_exact_zone(df, filters)
    else:
        df = _apply_filters(df, filters)

    df = df[(df["week_index"] >= start_idx) & (df["week_index"] <= end_idx)]
    df = df[df["has_value"] == True].copy()

    if df.empty:
        return {"data": pd.DataFrame(), "metric": metric, "filters": filters,
                "start_week": start_week, "end_week": end_week}

    if not filters.get("zone"):
        agg_df = (
            df.groupby(["week_label", "week_index"])["value"]
            .mean().reset_index().sort_values("week_index")
        )
    else:
        agg_df = (
            df.groupby(["week_label", "week_index", "ZONE"])["value"]
            .mean().reset_index().sort_values("week_index")
        )

    agg_df = agg_df.reset_index(drop=True)
    agg_df["wow_change"] = agg_df["value"].pct_change()
    agg_df["metric"] = metric

    return {"data": agg_df, "metric": metric, "filters": filters,
            "start_week": start_week, "end_week": end_week}




# ──────────────────────────────────────────────
# 1. Ranking / Top-K
# ──────────────────────────────────────────────
def get_top_zones(
    df_metrics_wide: pd.DataFrame,
    df_orders_wide: pd.DataFrame,
    metric: str,
    week: str = "L0W",
    filters: dict = None,
    top_k: int = 5,
    sort: str = "desc",
) -> dict:
    """
    Return top-K zones for a given metric at a specific week.
    For Lead Penetration: outliers (>=2.0) are EXCLUDED from the standard ranking
    (they are absolute store counts, not ratios, and dominate the top-K misleadingly).
    They are returned separately in lp_outliers_df for transparency.
    """
    filters = filters or {}

    if metric == "Orders":
        df = df_orders_wide.copy()
    else:
        df = df_metrics_wide[df_metrics_wide["METRIC"] == metric].copy()

    df = _apply_filters(df, filters)

    if week not in df.columns:
        week = "L0W"

    df = df[["COUNTRY", "CITY", "ZONE", week]].dropna(subset=[week])
    df = df.rename(columns={week: "value"})

    # For LP: split outliers out before ranking so they don't dominate top-K
    has_lp_outliers = False
    lp_outliers_df = pd.DataFrame()
    if metric == "Lead Penetration":
        lp_outliers_df = df[df["value"] >= LP_OUTLIER_THRESHOLD].copy()
        df = df[df["value"] < LP_OUTLIER_THRESHOLD].copy()
        has_lp_outliers = len(lp_outliers_df) > 0

    df = df.sort_values("value", ascending=(sort == "asc"))
    df = df.head(top_k).reset_index(drop=True)
    df["rank"] = df.index + 1
    df["metric"] = metric
    df["week"] = week
    df["data_quality_note"] = ""

    return {
        "data": df,
        "metric": metric,
        "week": week,
        "top_k": top_k,
        "filters": filters,
        "count": len(df),
        "has_lp_outliers": has_lp_outliers,
        "lp_outliers_df": lp_outliers_df,
    }


# ──────────────────────────────────────────────
# 2. Comparison between groups
# ──────────────────────────────────────────────
def compare_groups(
    df_metrics_wide: pd.DataFrame,
    df_orders_wide: pd.DataFrame,
    metric: str,
    group_by: str = "ZONE_TYPE",
    week: str = "L0W",
    filters: dict = None,
    agg: str = "mean",
) -> dict:
    """Compare metric values across groups. For LP, excludes outliers from group avg."""
    filters = filters or {}

    col_map = {
        "zone_type": "ZONE_TYPE",
        "ZONE_TYPE": "ZONE_TYPE",
        "country": "COUNTRY",
        "city": "CITY",
        "prioritization": "ZONE_PRIORITIZATION",
        "ZONE_PRIORITIZATION": "ZONE_PRIORITIZATION",
    }
    group_col = col_map.get(group_by, group_by.upper() if group_by else "COUNTRY")

    if metric == "Orders":
        df = df_orders_wide.copy()
        if "ZONE_TYPE" not in df.columns:
            df["ZONE_TYPE"] = None
        if "ZONE_PRIORITIZATION" not in df.columns:
            df["ZONE_PRIORITIZATION"] = None
    else:
        df = df_metrics_wide[df_metrics_wide["METRIC"] == metric].copy()

    # For Lead Penetration aggregations: exclude outliers to get meaningful ratio averages
    lp_outliers_excluded = False
    if metric == "Lead Penetration":
        n_before = len(df)
        df = df[df[week] <= LP_OUTLIER_THRESHOLD] if week in df.columns else df
        lp_outliers_excluded = (len(df) < n_before)

    df = _apply_filters(df, filters)

    if week not in df.columns:
        week = "L0W"

    df = df[[group_col, week]].dropna(subset=[week, group_col])

    if agg == "mean":
        result = df.groupby(group_col)[week].mean().reset_index()
    elif agg == "median":
        result = df.groupby(group_col)[week].median().reset_index()
    elif agg == "sum":
        result = df.groupby(group_col)[week].sum().reset_index()
    else:
        result = df.groupby(group_col)[week].mean().reset_index()

    n_zones_map = df.groupby(group_col).size().to_dict()
    result = result.rename(columns={week: "value", group_col: "group"})
    result["n_zones"] = result["group"].map(n_zones_map)
    result = result.sort_values("value", ascending=False).reset_index(drop=True)
    result["metric"] = metric
    result["week"] = week

    return {
        "data": result,
        "metric": metric,
        "group_by": group_by,
        "week": week,
        "agg": agg,
        "filters": filters,
        "lp_outliers_excluded": lp_outliers_excluded,
    }


# ──────────────────────────────────────────────
# 4. Aggregation (mean/sum by dimension)
# ──────────────────────────────────────────────
def aggregate_metric(
    df_metrics_wide: pd.DataFrame,
    df_orders_wide: pd.DataFrame,
    metric: str,
    group_by: str = "country",
    week: str = "L0W",
    filters: dict = None,
    agg: str = "mean",
) -> dict:
    """Average or sum a metric by a given dimension.
    For Lead Penetration: outliers (>2) are excluded from group averages."""
    return compare_groups(
        df_metrics_wide, df_orders_wide, metric, group_by, week, filters, agg
    )


# ──────────────────────────────────────────────
# 5. Multivariable: high A + low B
# ──────────────────────────────────────────────
def find_high_low_zones(
    df_metrics_wide: pd.DataFrame,
    metric_a: str,
    metric_b: str,
    direction_a: str = "high",
    direction_b: str = "low",
    week: str = "L0W",
    filters: dict = None,
    percentile_high: float = 0.75,
    percentile_low: float = 0.25,
) -> dict:
    """
    Find zones where metric_a is high AND metric_b is low.
    For Lead Penetration as metric_a: outliers (>2) are excluded from percentile
    calculation so thresholds are meaningful ratio-based boundaries.
    Outlier zones (LP >= 2.0) are excluded from the analysis entirely and
    returned in lp_outliers_df so the UI can mention them without contaminating results.
    """
    filters = filters or {}

    df_a = df_metrics_wide[df_metrics_wide["METRIC"] == metric_a].copy()
    df_b = df_metrics_wide[df_metrics_wide["METRIC"] == metric_b].copy()

    df_a = _apply_filters(df_a, filters)
    df_b = _apply_filters(df_b, filters)

    if week not in df_a.columns:
        week = "L0W"

    id_cols = ["COUNTRY", "CITY", "ZONE"]
    df_a = df_a[id_cols + [week, "ZONE_TYPE", "ZONE_PRIORITIZATION"]].rename(columns={week: "value_a"})
    df_b = df_b[id_cols + [week]].rename(columns={week: "value_b"})

    merged = df_a.merge(df_b, on=id_cols, how="inner")
    merged = merged.dropna(subset=["value_a", "value_b"])

    if merged.empty:
        return {"data": pd.DataFrame(), "metric_a": metric_a, "metric_b": metric_b, "count": 0}

    # For LP: remove outliers (>=2.0) from the analysis entirely — they distort
    # percentile thresholds and are not valid ratio data points
    lp_outliers_df = pd.DataFrame()
    if metric_a == "Lead Penetration":
        lp_outliers_df = merged[merged["value_a"] >= LP_OUTLIER_THRESHOLD].copy()
        merged = merged[merged["value_a"] < LP_OUTLIER_THRESHOLD].copy()
        if merged.empty:
            return {"data": pd.DataFrame(), "metric_a": metric_a, "metric_b": metric_b,
                    "count": 0, "lp_outliers_df": lp_outliers_df}

    pct_high = merged["value_a"].quantile(percentile_high)
    pct_low  = merged["value_b"].quantile(percentile_low)

    if direction_a == "high":
        mask_a = merged["value_a"] >= pct_high
    else:
        mask_a = merged["value_a"] <= merged["value_a"].quantile(1 - percentile_high)

    if direction_b == "low":
        mask_b = merged["value_b"] <= pct_low
    else:
        mask_b = merged["value_b"] >= merged["value_b"].quantile(1 - percentile_low)

    result = merged[mask_a & mask_b].copy()
    result = result.sort_values("value_a", ascending=False).reset_index(drop=True)
    result["percentile_a"] = result["value_a"].rank(pct=True)
    result["percentile_b"] = result["value_b"].rank(pct=True)
    result["data_quality_note"] = ""

    return {
        "data": result,
        "metric_a": metric_a,
        "metric_b": metric_b,
        "direction_a": direction_a,
        "direction_b": direction_b,
        "week": week,
        "threshold_a": pct_high,
        "threshold_b": pct_low,
        "count": len(result),
        "filters": filters,
        "lp_outliers_df": lp_outliers_df,
    }


# ──────────────────────────────────────────────
# 6. Growth explanation
# ──────────────────────────────────────────────
def find_fastest_growing_zones(
    df_orders_wide: pd.DataFrame,
    df_metrics_wide: pd.DataFrame,
    n_weeks: int = 5,
    filters: dict = None,
    top_k: int = 5,
    min_base: int = MIN_ORDERS_BASE,
) -> dict:
    """
    Find zones with highest order growth over last N weeks.
    Applies minimum base filter (default 50 orders) to avoid micro-zone artifacts.
    Confirmed with data: MASCHWITZ has base=4 → excluded. El Vecino base=58 → included.
    """
    filters = filters or {}
    df = df_orders_wide.copy()
    df = _apply_filters(df, filters)

    start_col = f"L{n_weeks}W"
    end_col = "L0W"

    for col in [start_col, end_col]:
        if col not in df.columns:
            return {"data": pd.DataFrame(), "error": f"Column {col} not found"}

    df = df.dropna(subset=[start_col, end_col])
    # Apply minimum base filter BEFORE computing growth
    df = df[df[start_col] >= min_base]   # was: df[start_col] > 0 — BUG FIXED
    df = df[df[start_col] > 0]           # secondary guard against zero division

    if df.empty:
        return {"data": pd.DataFrame(), "explanations": [], "n_weeks": n_weeks,
                "filters": filters, "top_k": top_k, "min_base": min_base}

    df = df.copy()
    df["growth_pct"]       = (df[end_col] - df[start_col]) / df[start_col].abs()
    df["orders_start"]     = df[start_col]
    df["orders_end"]       = df[end_col]
    df["orders_abs_growth"] = df[end_col] - df[start_col]

    top_zones = df.nlargest(top_k, "growth_pct")[
        ["COUNTRY", "CITY", "ZONE", "growth_pct", "orders_start", "orders_end", "orders_abs_growth"]
    ].reset_index(drop=True)

    # For each top zone, find correlated metric improvements
    explanations = []
    for _, row in top_zones.iterrows():
        zone_metrics = df_metrics_wide[
            (df_metrics_wide["ZONE"] == row["ZONE"]) &
            (df_metrics_wide["COUNTRY"] == row["COUNTRY"])
        ].copy()

        metric_changes = []
        for _, mrow in zone_metrics.iterrows():
            m = mrow["METRIC"]
            v_start = mrow.get(start_col, np.nan)
            v_end   = mrow.get(end_col, np.nan)
            if pd.isna(v_start) or pd.isna(v_end):
                continue
            # Use epsilon floor to prevent near-zero denominator artifacts
            denom = max(abs(v_start), 1e-3)
            if denom < 1e-3:
                continue
            pct_change  = (v_end - v_start) / denom
            higher_better = is_higher_better(m)
            improvement = pct_change if higher_better else -pct_change
            metric_changes.append({
                "metric":       m,
                "value_start":  v_start,
                "value_end":    v_end,
                "pct_change":   pct_change,
                "improvement":  improvement,
            })

        metric_changes = sorted(metric_changes, key=lambda x: x["improvement"], reverse=True)
        explanations.append({
            "zone":                     row["ZONE"],
            "country":                  row["COUNTRY"],
            "city":                     row["CITY"],
            "growth_pct":               row["growth_pct"],
            "orders_start":             row["orders_start"],
            "orders_end":               row["orders_end"],
            "top_metric_improvements":  metric_changes[:3],
        })

    return {
        "data":         top_zones,
        "explanations": explanations,
        "n_weeks":      n_weeks,
        "filters":      filters,
        "top_k":        top_k,
        "min_base":     min_base,
    }


# ──────────────────────────────────────────────
# Helper: WoW change
# ──────────────────────────────────────────────
def compute_wow_change(
    df_wide: pd.DataFrame,
    metric: str | None = None,
    from_week: str = "L1W",
    to_week: str = "L0W",
    filters: dict = None,
) -> pd.DataFrame:
    filters = filters or {}
    if metric and metric != "Orders":
        df = df_wide[df_wide["METRIC"] == metric].copy()
    else:
        df = df_wide.copy()
    df = _apply_filters(df, filters)
    if from_week not in df.columns or to_week not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["wow_change"] = (df[to_week] - df[from_week]) / df[from_week].abs()
    id_cols = [c for c in ["COUNTRY", "CITY", "ZONE", "METRIC", "ZONE_TYPE", "ZONE_PRIORITIZATION"]
               if c in df.columns]
    return df[id_cols + ["wow_change", from_week, to_week]].dropna(subset=["wow_change"])


# ──────────────────────────────────────────────
# Helper: consistent deterioration detector
# ──────────────────────────────────────────────
def detect_consistent_deterioration(
    df_metrics_wide: pd.DataFrame,
    min_weeks: int = 3,
    filters: dict = None,
) -> pd.DataFrame:
    filters = filters or {}
    df = _apply_filters(df_metrics_wide.copy(), filters)
    results = []

    for _, row in df.iterrows():
        metric = row["METRIC"]
        higher_better = is_higher_better(metric)
        consecutive = 0
        max_consecutive = 0
        start_val = None
        end_val = None

        for i in range(8, 0, -1):
            w_prev, w_curr = f"L{i}W", f"L{i-1}W"
            v_prev, v_curr = row.get(w_prev), row.get(w_curr)
            if pd.isna(v_prev) or pd.isna(v_curr) or v_prev == 0:
                consecutive = 0
                continue
            deteriorated = (v_curr < v_prev) if higher_better else (v_curr > v_prev)
            if deteriorated:
                consecutive += 1
                if consecutive == 1:
                    start_val = v_prev
                end_val = v_curr
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0

        if max_consecutive >= min_weeks:
            total_change = (end_val - start_val) / abs(start_val) if start_val else np.nan
            results.append({
                "COUNTRY":                      row["COUNTRY"],
                "CITY":                         row["CITY"],
                "ZONE":                         row["ZONE"],
                "METRIC":                       metric,
                "ZONE_TYPE":                    row.get("ZONE_TYPE"),
                "ZONE_PRIORITIZATION":          row.get("ZONE_PRIORITIZATION"),
                "consecutive_deterioration_weeks": max_consecutive,
                "total_pct_change":             total_change,
                "L0W_value":                    row.get("L0W"),
            })

    if results:
        return pd.DataFrame(results).sort_values(
            "consecutive_deterioration_weeks", ascending=False
        )
    return pd.DataFrame()
