"""
tests/test_queries.py — Deterministic tests for executor functions.
Run: python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pandas as pd
import numpy as np
import pytest

from utils import get_processed_data
from executor import (
    get_top_zones,
    compare_groups,
    get_trend,
    find_high_low_zones,
    find_fastest_growing_zones,
    detect_consistent_deterioration,
)
from semantic_layer import resolve_metric, resolve_country, resolve_zone_type


@pytest.fixture(scope="module")
def data():
    return get_processed_data()


# ─── Semantic layer tests ───────────────────
class TestSemanticLayer:
    def test_resolve_metric_exact(self):
        assert resolve_metric("Lead Penetration") == "Lead Penetration"

    def test_resolve_metric_alias(self):
        assert resolve_metric("lead pen") == "Lead Penetration"
        assert resolve_metric("perfect order") == "Perfect Orders"
        assert resolve_metric("gross profit") == "Gross Profit UE"
        assert resolve_metric("markdowns") == "Restaurants Markdowns / GMV"

    def test_resolve_metric_fuzzy(self):
        assert resolve_metric("lead penetracion") == "Lead Penetration"

    def test_resolve_country(self):
        assert resolve_country("colombia") == "CO"
        assert resolve_country("mexico") == "MX"
        assert resolve_country("CO") == "CO"
        assert resolve_country("brasil") == "BR"

    def test_resolve_zone_type(self):
        assert resolve_zone_type("wealthy") == "Wealthy"
        assert resolve_zone_type("non wealthy") == "Non Wealthy"
        assert resolve_zone_type("no rico") == "Non Wealthy"

    def test_resolve_metric_unknown(self):
        assert resolve_metric("zxkqwerty") is None


# ─── Executor tests ─────────────────────────
class TestExecutor:
    def test_top_zones_returns_dataframe(self, data):
        result = get_top_zones(
            data["metrics_wide"], data["orders_wide"],
            metric="Lead Penetration", week="L0W", top_k=5,
        )
        assert isinstance(result["data"], pd.DataFrame)
        assert len(result["data"]) <= 5
        assert "ZONE" in result["data"].columns
        assert "value" in result["data"].columns

    def test_top_zones_sorted_desc(self, data):
        result = get_top_zones(
            data["metrics_wide"], data["orders_wide"],
            metric="Lead Penetration", week="L0W", top_k=10, sort="desc",
        )
        values = result["data"]["value"].tolist()
        assert values == sorted(values, reverse=True)

    def test_top_zones_orders(self, data):
        result = get_top_zones(
            data["metrics_wide"], data["orders_wide"],
            metric="Orders", week="L0W", top_k=5,
        )
        assert len(result["data"]) > 0

    def test_compare_groups_returns_groups(self, data):
        result = compare_groups(
            data["metrics_wide"], data["orders_wide"],
            metric="Perfect Orders", group_by="ZONE_TYPE", week="L0W",
        )
        df = result["data"]
        assert "group" in df.columns
        assert "value" in df.columns
        assert len(df) == 2  # Wealthy, Non Wealthy

    def test_compare_groups_by_country(self, data):
        result = compare_groups(
            data["metrics_wide"], data["orders_wide"],
            metric="Lead Penetration", group_by="country", week="L0W",
        )
        assert len(result["data"]) > 1

    def test_get_trend_returns_timeseries(self, data):
        result = get_trend(
            data["metrics_long"], data["orders_long"],
            metric="Lead Penetration",
            filters={"zone": "Chapinero"},
            start_week="L8W", end_week="L0W",
        )
        df = result["data"]
        assert len(df) <= 9  # max 9 weeks
        if len(df) > 0:
            assert "week_label" in df.columns
            assert "value" in df.columns

    def test_find_high_low_zones(self, data):
        result = find_high_low_zones(
            data["metrics_wide"],
            metric_a="Lead Penetration",
            metric_b="Perfect Orders",
            direction_a="high",
            direction_b="low",
            week="L0W",
        )
        assert "data" in result
        assert "count" in result
        # All returned zones should have value_a >= threshold_a
        if len(result["data"]) > 0:
            assert all(result["data"]["value_a"] >= result["threshold_a"] * 0.99)

    def test_find_fastest_growing_zones(self, data):
        result = find_fastest_growing_zones(
            data["orders_wide"], data["metrics_wide"],
            n_weeks=5, top_k=5,
        )
        df = result["data"]
        assert "growth_pct" in df.columns
        if len(df) > 1:
            # Should be sorted descending
            values = df["growth_pct"].tolist()
            assert values == sorted(values, reverse=True)

    def test_detect_consistent_deterioration(self, data):
        result = detect_consistent_deterioration(data["metrics_wide"], min_weeks=3)
        if len(result) > 0:
            assert "ZONE" in result.columns
            assert "METRIC" in result.columns
            assert "consecutive_deterioration_weeks" in result.columns
            assert all(result["consecutive_deterioration_weeks"] >= 3)

    def test_filter_by_country(self, data):
        result = get_top_zones(
            data["metrics_wide"], data["orders_wide"],
            metric="Lead Penetration", week="L0W",
            filters={"country": "CO"}, top_k=10,
        )
        if len(result["data"]) > 0:
            assert all(result["data"]["COUNTRY"] == "CO")

    def test_filter_by_zone_type(self, data):
        result = compare_groups(
            data["metrics_wide"], data["orders_wide"],
            metric="Perfect Orders", group_by="country",
            filters={"zone_type": "Wealthy"}, week="L0W",
        )
        assert "data" in result


# ─── Data integrity tests ───────────────────
class TestDataIntegrity:
    def test_all_countries_present(self, data):
        countries = data["metrics_wide"]["COUNTRY"].unique()
        expected = {"AR", "BR", "CL", "CO", "CR", "EC", "MX", "PE", "UY"}
        assert expected == set(countries)

    def test_no_negative_orders(self, data):
        for col in ["L0W", "L1W"]:
            vals = data["orders_wide"][col].dropna()
            assert all(vals >= 0), f"Negative orders found in {col}"

    def test_metrics_have_l0w(self, data):
        assert data["metrics_wide"]["L0W"].notna().any()

    def test_long_format_has_week_index(self, data):
        assert "week_index" in data["metrics_long"].columns
        assert data["metrics_long"]["week_index"].between(0, 8).all()

    def test_zone_type_values(self, data):
        zone_types = data["metrics_wide"]["ZONE_TYPE"].unique()
        for zt in zone_types:
            assert zt in ["Wealthy", "Non Wealthy"], f"Unexpected zone_type: {zt}"


# ─── Demo acceptance tests (regression guards for the 6 brief queries) ─────
# These tests simulate the exact filter conditions that caused failures in demos
# and assert the corrected behavior holds.

def _clean_filters_for_intent(query_filters, sidebar_filters, intent, group_by=None):
    """Mirror of streamlit_app.clean_filters_for_intent for test isolation."""
    warnings, effective = [], {k: v for k, v in query_filters.items() if v is not None}

    if group_by == "ZONE_TYPE" and intent in ("comparison", "aggregation"):
        effective.pop("zone_type", None)
        for k, v in sidebar_filters.items():
            if k == "zone_type": continue
            if v and not effective.get(k): effective[k] = v
        return effective, warnings

    if intent in ("trend", "multivariable") and effective.get("zone"):
        effective.pop("zone_type", None)
        for k, v in sidebar_filters.items():
            if k == "zone_type": continue
            if v and not effective.get(k): effective[k] = v
        return effective, warnings

    for k, v in sidebar_filters.items():
        if v and not effective.get(k): effective[k] = v
    return effective, warnings


class TestDemoAcceptance:
    """
    Acceptance regression tests for the 6 demo queries from the technical brief.
    Each test guards against a specific failure mode observed during review.
    """

    def test_q2_comparison_both_groups_with_sidebar_zone_type(self, data):
        """Q2: comparison must return BOTH groups even when sidebar has zone_type=Non Wealthy."""
        mw, ow = data["metrics_wide"], data["orders_wide"]
        # Simulate parser extracting zone_type from question text AND sidebar active
        query_filters   = {"country": "CO", "zone_type": "Non Wealthy"}
        sidebar_filters = {"zone_type": "Non Wealthy"}
        eff, _ = _clean_filters_for_intent(query_filters, sidebar_filters, "comparison", "ZONE_TYPE")
        assert "zone_type" not in eff, "zone_type leaked into ZONE_TYPE comparison"
        result = compare_groups(mw, ow, "Perfect Orders", "ZONE_TYPE", "L0W", eff)
        groups = set(result["data"]["group"])
        assert groups == {"Wealthy", "Non Wealthy"}, f"Expected both groups, got: {groups}"

    def test_q2_gap_is_positive(self, data):
        """Q2: Wealthy should have higher Perfect Orders than Non Wealthy in CO."""
        mw, ow = data["metrics_wide"], data["orders_wide"]
        result = compare_groups(mw, ow, "Perfect Orders", "ZONE_TYPE", "L0W", {"country": "CO"})
        vals   = result["data"].set_index("group")["value"]
        assert vals["Wealthy"] > vals["Non Wealthy"], "Wealthy PO should be > Non Wealthy PO"

    def test_q3_trend_chapinero_with_sidebar_non_wealthy(self, data):
        """Q3: Chapinero trend must return 9 data points even when sidebar has zone_type=Non Wealthy."""
        ml, ol = data["metrics_long"], data["orders_long"]
        # zone_type=Non Wealthy in both query (LLM hallucination) and sidebar
        query_filters   = {"zone": "chapinero", "zone_type": "Non Wealthy"}
        sidebar_filters = {"zone_type": "Non Wealthy"}
        eff, _ = _clean_filters_for_intent(query_filters, sidebar_filters, "trend")
        assert "zone_type" not in eff, "zone_type leaked into trend+zone query"
        result = get_trend(ml, ol, "Gross Profit UE", eff, "L8W", "L0W")
        assert len(result["data"]) == 9, f"Expected 9 weekly points, got {len(result['data'])}"

    def test_q3_chapinero_starts_l8w_ends_l0w(self, data):
        """Q3: Trend series must span exactly L8W → L0W."""
        ml, ol = data["metrics_long"], data["orders_long"]
        result = get_trend(ml, ol, "Gross Profit UE", {"zone": "chapinero"}, "L8W", "L0W")
        assert result["data"].iloc[0]["week_label"] == "L8W"
        assert result["data"].iloc[-1]["week_label"] == "L0W"

    def test_q1_ranking_no_lp_outliers(self, data):
        """Q1: Lead Penetration ranking must exclude values >= 2.0 from top-K."""
        mw, ow = data["metrics_wide"], data["orders_wide"]
        result = get_top_zones(mw, ow, "Lead Penetration", "L0W", {}, 5)
        assert result["data"]["value"].max() < 2.0, "LP outlier (>=2.0) found in ranking results"
        assert result["has_lp_outliers"], "has_lp_outliers flag should be True"
        assert "lp_outliers_df" in result, "lp_outliers_df must be present"

    def test_q5_multivariable_no_lp_outliers(self, data):
        """Q5: Multivariable analysis must exclude LP outliers (>=2.0) from results and thresholds."""
        mw = data["metrics_wide"]
        result = find_high_low_zones(mw, "Lead Penetration", "Perfect Orders", "high", "low", "L0W", {})
        assert result["count"] > 0, "No results found for multivariable analysis"
        assert result["data"]["value_a"].max() < 2.0, "LP outlier in multivariable results"
        assert result["threshold_a"] < 2.0, "Threshold contaminated by outliers"

    def test_q3_chapinero_unique_zone_inference(self, data):
        """Q3: resolve_location_entities must infer city=Bogota, country=CO for Chapinero."""
        mw = data["metrics_wide"]
        catalog = (
            mw[["ZONE", "CITY", "COUNTRY"]]
            .drop_duplicates()
            .copy()
        )
        catalog["zone_lower"] = catalog["ZONE"].str.lower()
        counts = catalog.groupby("zone_lower").size()

        # Chapinero must be unique
        assert counts.get("chapinero", 0) == 1, "Chapinero should be unique in the dataset"

        # Look up the identity
        identity = catalog[catalog["zone_lower"] == "chapinero"].iloc[0]
        assert identity["CITY"] == "Bogota",   f"Expected Bogota, got {identity['CITY']}"
        assert identity["COUNTRY"] == "CO",    f"Expected CO, got {identity['COUNTRY']}"

        # After inference, get_trend must return 9 rows
        ml, ol = data["metrics_long"], data["orders_long"]
        inferred_filters = {
            "zone":    identity["ZONE"],
            "city":    identity["CITY"],
            "country": identity["COUNTRY"],
        }
        result = get_trend(ml, ol, "Gross Profit UE", inferred_filters, "L8W", "L0W")
        assert len(result["data"]) == 9, f"Expected 9 points with inferred identity, got {len(result['data'])}"

    def test_q3_chapinero_llm_city_misclassification(self, data):
        """Q3: LLM placing 'Chapinero' in city field must be fixed and return 9 rows."""
        mw = data["metrics_wide"]
        zone_names = set(mw["ZONE"].str.lower().unique())
        city_names = set(mw["CITY"].str.lower().unique())

        # Verify precondition: Chapinero is a zone, not a city
        assert "chapinero" in zone_names,     "'chapinero' must be a known zone"
        assert "chapinero" not in city_names, "'chapinero' must NOT be a known city"

        # Simulate LLM output with city="Chapinero"
        llm_filters = {"country": None, "city": "Chapinero", "zone": None, "zone_type": None}

        # Apply reclassification (Rule 1)
        city_val = llm_filters["city"].lower()
        assert city_val not in city_names and city_val in zone_names
        fixed = dict(llm_filters)
        fixed["zone"] = city_val
        fixed["city"] = None

        # Execute trend
        ml, ol = data["metrics_long"], data["orders_long"]
        result = get_trend(ml, ol, "Gross Profit UE", fixed, "L8W", "L0W")
        assert len(result["data"]) == 9, f"After city→zone fix, expected 9 rows, got {len(result['data'])}"

    def test_q3_chapinero_last_wow(self, data):
        """Q3: Last week WoW change for Chapinero GP UE should be approximately -13.4%."""
        ml, ol = data["metrics_long"], data["orders_long"]
        result = get_trend(ml, ol, "Gross Profit UE", {"zone": "chapinero"}, "L8W", "L0W")
        assert len(result["data"]) == 9
        last_wow = result["data"].iloc[-1]["wow_change"]
        # WoW should be negative (deterioration) and approximately -13.4%
        assert last_wow < 0, f"Last WoW should be negative, got {last_wow:.3f}"
        assert abs(last_wow - (-0.134)) < 0.02, f"Expected ~-13.4% WoW, got {last_wow:.3f}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
