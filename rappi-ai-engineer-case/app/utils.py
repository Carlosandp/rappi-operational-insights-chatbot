"""
utils.py — Data loading, cleaning, and transformation utilities.
Fixes: SettingWithCopyWarning eliminated (use .copy() + .loc), 
       cache invalidation by file mtime+size hash.
"""

import json
import hashlib
import os
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
DATA_RAW   = BASE_DIR / "data" / "raw" / "dummy_data.xlsx"
DATA_PROCESSED = BASE_DIR / "data" / "processed"
METRIC_DICT_PATH = BASE_DIR / "data" / "metric_dictionary.json"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────
WEEK_LABELS  = ["L8W", "L7W", "L6W", "L5W", "L4W", "L3W", "L2W", "L1W", "L0W"]
WEEK_INDICES = list(range(9))


def load_raw_metrics() -> pd.DataFrame:
    df = pd.read_excel(DATA_RAW, sheet_name="RAW_INPUT_METRICS")
    df.columns = df.columns.str.strip()
    return df


def load_raw_orders() -> pd.DataFrame:
    df = pd.read_excel(DATA_RAW, sheet_name="RAW_ORDERS")
    df.columns = df.columns.str.strip()
    return df


def load_metric_dictionary() -> dict:
    with open(METRIC_DICT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Cleaning (SettingWithCopyWarning-free) ────────────────────────────────
def clean_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates().copy()                          # .copy() prevents warning
    for col in ["COUNTRY", "CITY", "ZONE", "ZONE_TYPE", "ZONE_PRIORITIZATION", "METRIC"]:
        df.loc[:, col] = df[col].astype(str).str.strip()     # .loc avoids chained assignment
    week_col_map = {f"L{i}W_ROLL": f"L{i}W" for i in range(9)}
    df = df.rename(columns=week_col_map)
    for w in WEEK_LABELS:
        if w in df.columns:
            df.loc[:, w] = pd.to_numeric(df[w], errors="coerce")
    return df


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates().copy()
    for col in ["COUNTRY", "CITY", "ZONE", "METRIC"]:
        df.loc[:, col] = df[col].astype(str).str.strip()
    for w in WEEK_LABELS:
        if w in df.columns:
            df.loc[:, w] = pd.to_numeric(df[w], errors="coerce")
    return df


# ── Wide → Long ───────────────────────────────────────────────────────────
def melt_to_long(df: pd.DataFrame, id_vars: list, value_name: str = "value") -> pd.DataFrame:
    week_cols = [w for w in WEEK_LABELS if w in df.columns]
    long = df.melt(id_vars=id_vars, value_vars=week_cols,
                   var_name="week_label", value_name=value_name)
    # L8W=0 (oldest), L0W=8 (newest)
    label_to_idx = {f"L{i}W": 8 - i for i in range(9)}
    long["week_index"] = long["week_label"].map(lambda x: label_to_idx.get(x, -1))
    long["weeks_ago"]  = long["week_label"].map(
        lambda x: int(x[1]) if len(x) == 3 else int(x[1:3])
    )
    return long


def build_metrics_long(df_metrics: pd.DataFrame) -> pd.DataFrame:
    id_vars = ["COUNTRY", "CITY", "ZONE", "ZONE_TYPE", "ZONE_PRIORITIZATION", "METRIC"]
    long = melt_to_long(df_metrics, id_vars=id_vars)
    long["has_value"] = long["value"].notna()
    return long


def build_orders_long(df_orders: pd.DataFrame) -> pd.DataFrame:
    id_vars = ["COUNTRY", "CITY", "ZONE", "METRIC"]
    long = melt_to_long(df_orders, id_vars=id_vars)
    long["ZONE_TYPE"]          = None
    long["ZONE_PRIORITIZATION"] = None
    long["has_value"]          = long["value"].notna()
    return long


# ── Cache invalidation by content hash ───────────────────────────────────────
# Using a content hash (not mtime) ensures the cache is invalidated even when
# the file is replaced with one that has the same size and an identical mtime
# (which can happen when unzipping a new release on top of an old one).
# The CACHE_VERSION salt forces a full rebuild whenever the processing logic changes.
CACHE_VERSION = "v4"  # bump this whenever clean_metrics / data schema changes


def _source_fingerprint() -> str:
    """Return a fingerprint of the raw Excel file using its SHA-256 content hash."""
    import hashlib
    h = hashlib.sha256()
    with open(DATA_RAW, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"{CACHE_VERSION}_{h.hexdigest()[:16]}"


def get_processed_data() -> dict:
    """
    Returns processed DataFrames with automatic cache management.

    Cache is keyed by SHA-256 of the Excel content + CACHE_VERSION.
    Any stale .pkl (different fingerprint OR different code version) is
    deleted and rebuilt automatically — no manual cleanup needed.
    """
    cache_file       = DATA_PROCESSED / "processed_data.pkl"
    fingerprint_file = DATA_PROCESSED / "source_fingerprint.txt"
    current_fp       = _source_fingerprint()

    # ── Delete stale cache proactively ────────────────────────────────────
    if cache_file.exists():
        stored_fp = fingerprint_file.read_text().strip() if fingerprint_file.exists() else ""
        if stored_fp != current_fp:
            try:
                cache_file.unlink()
                fingerprint_file.unlink(missing_ok=True)
            except Exception:
                pass

    # ── Try loading valid cache ────────────────────────────────────────────
    if cache_file.exists():
        try:
            with open(cache_file, "rb") as f:
                data = pickle.load(f)
            # Quick sanity check: Chapinero must be resolvable
            mw = data.get("metrics_wide", None)
            if mw is not None:
                chap_rows = mw[
                    (mw["ZONE"].str.lower() == "chapinero") &
                    (mw["METRIC"] == "Gross Profit UE")
                ]
                if len(chap_rows) == 1:   # exactly 1 row = deduplicated correctly
                    return data
            # Cache loaded but failed sanity — fall through to rebuild
        except Exception:
            pass
        # Delete corrupt / invalid cache
        try:
            cache_file.unlink()
            fingerprint_file.unlink(missing_ok=True)
        except Exception:
            pass

    # ── Build from scratch ─────────────────────────────────────────────────
    raw_metrics   = load_raw_metrics()
    raw_orders    = load_raw_orders()
    metrics_clean = clean_metrics(raw_metrics)
    orders_clean  = clean_orders(raw_orders)

    metrics_wide = metrics_clean.copy()
    orders_wide  = orders_clean.copy()
    metrics_long = build_metrics_long(metrics_clean)
    orders_long  = build_orders_long(orders_clean)

    # Enrich orders_long with zone metadata
    zone_meta = (
        metrics_clean[["COUNTRY", "CITY", "ZONE", "ZONE_TYPE", "ZONE_PRIORITIZATION"]]
        .drop_duplicates()
    )
    orders_long = orders_long.drop(columns=["ZONE_TYPE", "ZONE_PRIORITIZATION"])
    orders_long = orders_long.merge(zone_meta, on=["COUNTRY", "CITY", "ZONE"], how="left")

    result = {
        "metrics_long": metrics_long,
        "orders_long":  orders_long,
        "metrics_wide": metrics_wide,
        "orders_wide":  orders_wide,
    }

    # Save cache
    try:
        DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "wb") as f:
            pickle.dump(result, f)
        fingerprint_file.write_text(current_fp)
    except Exception:
        pass

    return result


# ── Formatting helpers ────────────────────────────────────────────────────
def fmt_value(val, metric: str = "") -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    d = load_metric_dictionary()
    unit = d["metrics"].get(metric, {}).get("unit", "ratio")
    if unit == "ratio":
        return f"{val:.1%}"
    elif unit == "currency":
        return f"${val:,.2f}"
    elif unit == "count":
        return f"{val:,.0f}"
    return f"{val:.4f}"


def fmt_change(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    return f"{'+' if val > 0 else ''}{val:.1%}"
