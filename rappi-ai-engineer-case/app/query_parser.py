"""
query_parser.py — LLM → structured JSON intent parser.

Fixes applied:
- Dynamic LLM credentials (never module-level globals)
- Migrated from google.generativeai (deprecated) to google.genai
- Groq uses llama-3.3-70b-versatile (Qwen removed from free tier)
- Rule-based fallback covers all 6 intents without hardcoded zone names
- resolve_zone() / resolve_city() used for dynamic zone detection
- Post-LLM semantic normalization via semantic_layer
"""

import json, os, re
from dotenv import load_dotenv
load_dotenv()


def _get_llm_config() -> dict:
    """Read credentials from os.environ at call time — never module-level."""
    return {
        "provider":   os.environ.get("LLM_PROVIDER", "gemini").lower(),
        "gemini_key": os.environ.get("GEMINI_API_KEY", ""),
        "groq_key":   os.environ.get("GROQ_API_KEY", ""),
    }


PARSE_SYSTEM_PROMPT = """You are a query parser for a Rappi operations analytics system.
Return ONLY a valid JSON object. No markdown, no explanation, no extra text.

Intents: ranking, comparison, trend, aggregation, multivariable, growth_explanation, anomaly

Metrics (exact names only):
Lead Penetration, Perfect Orders, Gross Profit UE, Pro Adoption (Last Week Status),
% PRO Users Who Breakeven, MLTV Top Verticals Adoption, Restaurants SS > ATC CVR,
Restaurants SST > SS CVR, Retail SST > SS CVR,
% Restaurants Sessions With Optimal Assortment, Non-Pro PTC > OP,
Turbo Adoption, Restaurants Markdowns / GMV, Orders

Countries: AR, BR, CL, CO, CR, EC, MX, PE, UY
Zone types: "Wealthy", "Non Wealthy"
Prioritization: "High Priority", "Prioritized", "Not Prioritized"

Schema:
{"intent":"<>","metric":"<exact or null>","metric_a":"<>","metric_b":"<>",
"metric_a_direction":"high","metric_b_direction":"low",
"filters":{"country":"<2-letter or null>","city":"<or null>","zone":"<or null>",
"zone_type":"<or null>","prioritization":"<or null>"},
"time_scope":"L0W","n_weeks":null,"top_k":5,"sort":"desc",
"group_by":"<country/ZONE_TYPE/city/ZONE_PRIORITIZATION or null>","aggregation":"mean or null"}

Rules:
- "promedio por pais"/"average by country" → intent=aggregation, group_by=country
- "compara"/"compare" → intent=comparison
- "evolucion" + location → intent=trend
- "alto X pero bajo Y" → intent=multivariable
- "crecen en ordenes"/"growing in orders" → intent=growth_explanation, metric=Orders, n_weeks=5
- Return ONLY raw JSON."""


def _call_gemini(question: str, api_key: str) -> str:
    """Use google.genai (new SDK, replaces deprecated google.generativeai)."""
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=PARSE_SYSTEM_PROMPT,
                temperature=0.1,
            ),
        )
        return response.text
    except ImportError:
        # Fallback to legacy google.generativeai if new SDK not installed
        # Suppress the FutureWarning about the deprecated package
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            import google.generativeai as genai_legacy
        genai_legacy.configure(api_key=api_key)
        model = genai_legacy.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=PARSE_SYSTEM_PROMPT,
        )
        return model.generate_content(question).text


def _call_groq(question: str, api_key: str) -> str:
    from groq import Groq
    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
        messages=[
            {"role": "system", "content": PARSE_SYSTEM_PROMPT},
            {"role": "user",   "content": question},
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.1,
    )
    return resp.choices[0].message.content


def _extract_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(cleaned)


# ── Dynamic zone/city resolution (no hardcoding) ─────────────────────────
def _get_known_zones_and_cities():
    """Load zone and city lists from processed data for dynamic matching."""
    try:
        from utils import get_processed_data
        data = get_processed_data()
        mw   = data["metrics_wide"]
        zones  = set(mw["ZONE"].str.lower().unique())
        cities = set(mw["CITY"].str.lower().unique())
        return zones, cities
    except Exception:
        return set(), set()


def _detect_zone_or_city(q: str) -> tuple[str | None, str | None]:
    """
    Detect if any known zone or city name appears in the question.
    Returns (zone, city) — both can be None.
    """
    zones, cities = _get_known_zones_and_cities()
    q_lower = q.lower()
    detected_zone = None
    detected_city = None
    # Check zones (longer names first to avoid partial matches)
    for z in sorted(zones, key=len, reverse=True):
        if len(z) >= 4 and z in q_lower:
            detected_zone = z
            break
    for c in sorted(cities, key=len, reverse=True):
        if len(c) >= 4 and c in q_lower:
            detected_city = c
            break
    return detected_zone, detected_city


# ── Rule-based fallback parser ────────────────────────────────────────────
def _rule_based_parse(question: str, context: dict) -> dict:
    """Deterministic fallback — covers all 6 core intents without hardcoded names."""
    from semantic_layer import (
        resolve_metric, resolve_country, resolve_zone_type,
        resolve_prioritization, get_all_canonical_metrics,
    )

    q = question.lower()
    all_metrics = get_all_canonical_metrics()

    # ── Intent ───────────────────────────────────────────────────────────
    # growth_explanation FIRST (before trend check)
    if any(k in q for k in ["crecen", "crecimiento", "growing", "fastest",
                              "más crecen", "mayor crecimiento"]) and \
       any(k in q for k in ["orden", "órdenes", "ordenes", "order", "pedido"]):
        intent = "growth_explanation"

    elif any(k in q for k in ["promedio", "average", "mean", "avg",
                                "por país", "por pais", "by country",
                                "per country", "por ciudad", "por zona"]):
        intent = "aggregation"

    elif any(k in q for k in ["compara", "compare", "vs ", "versus",
                                "diferencia entre", "wealthy vs"]):
        intent = "comparison"

    else:
        intent = "ranking"

    # Override to trend if evolution keywords + spatial reference
    if intent == "ranking":
        if any(k in q for k in ["evolución", "evolucion", "trend", "tendencia"]):
            intent = "trend"
        elif re.search(r"últimas?\s*\d+\s*semanas?|last\s*\d+\s*weeks?", q):
            # Trend only if a zone/city is mentioned
            dz, dc = _detect_zone_or_city(q)
            if dz or dc:
                intent = "trend"

    # Multivariable
    if any(k in q for k in ["alto", "alta", "high"]) and \
       any(k in q for k in ["pero", "but", "bajo", "baja", "low"]):
        intent = "multivariable"

    if any(k in q for k in ["anomalía", "anomalia", "anomaly", "cambio brusco"]):
        intent = "anomaly"

    # ── Metric ────────────────────────────────────────────────────────────
    metric = None
    for m in all_metrics:
        if m.lower() in q:
            metric = m
            break
    if not metric:
        for token in re.findall(r"[\w\s%>/()\-]+", q):
            resolved = resolve_metric(token.strip())
            if resolved:
                metric = resolved
                break
    if not metric and context.get("last_metric"):
        metric = context["last_metric"]

    # ── Multivariable metrics ─────────────────────────────────────────────
    metric_a, metric_b = None, None
    if intent == "multivariable":
        found = [m for m in all_metrics if m.lower() in q]
        if len(found) >= 2:
            metric_a, metric_b = found[0], found[1]
        elif len(found) == 1:
            metric_a = found[0]
            metric_b = "Perfect Orders" if found[0] != "Perfect Orders" else "Lead Penetration"
        else:
            metric_a, metric_b = "Lead Penetration", "Perfect Orders"
        metric = None

    # ── Country ───────────────────────────────────────────────────────────
    country_map = {
        "colombia": "CO", "méxico": "MX", "mexico": "MX",
        "brasil": "BR", "brazil": "BR", "argentina": "AR",
        "chile": "CL", "perú": "PE", "peru": "PE",
        "ecuador": "EC", "uruguay": "UY", "costa rica": "CR",
    }
    country = None
    for name, code in country_map.items():
        if name in q:
            country = code
            break
    if not country:
        for code in ["CO","MX","BR","AR","CL","PE","EC","UY","CR"]:
            if f" {code.lower()} " in f" {q} ":
                country = code
                break
    # Context carryover only for explicit follow-up signals
    if not country and context.get("last_country"):
        if any(k in q for k in ["y ahora", "ahora solo", "and now", "mismo", "same"]):
            country = context["last_country"]

    # ── Zone / City (dynamic, no hardcoding) ──────────────────────────────
    detected_zone, detected_city = _detect_zone_or_city(q)
    zone = detected_zone  # raw lowercase; executor uses contains()
    city = detected_city if not detected_zone else None

    # Context zone carryover
    if not zone and context.get("last_zone"):
        if any(k in q for k in ["misma", "same", "también", "también"]):
            zone = context["last_zone"]

    # ── Zone type / Prioritization ────────────────────────────────────────
    zone_type = None
    if "non wealthy" in q or "no wealthy" in q:
        zone_type = "Non Wealthy"
    elif "wealthy" in q:
        zone_type = "Wealthy"

    prioritization = None
    if "high priority" in q or "alta prioridad" in q:
        prioritization = "High Priority"
    elif "not prioritized" in q or "sin prioridad" in q or "no priorizado" in q:
        prioritization = "Not Prioritized"
    elif "prioritized" in q or "priorizado" in q:
        prioritization = "Prioritized"

    # ── Group by ──────────────────────────────────────────────────────────
    group_by = None
    if any(k in q for k in ["por país", "por pais", "by country", "per country"]):
        group_by = "country"
    elif "zone type" in q or ("wealthy" in q and intent == "comparison"):
        group_by = "ZONE_TYPE"
    elif any(k in q for k in ["por ciudad", "by city"]):
        group_by = "city"
    elif any(k in q for k in ["por prioridad", "by prioritization"]):
        group_by = "ZONE_PRIORITIZATION"

    # ── Weeks ─────────────────────────────────────────────────────────────
    time_scope = "L0W"
    n_weeks = None
    m_wk = re.search(r"últimas?\s*(\d+)\s*semanas?|last\s*(\d+)\s*weeks?", q)
    if m_wk:
        n_weeks = int(m_wk.group(1) or m_wk.group(2))
        n_weeks = min(n_weeks, 8)
        time_scope = f"L{n_weeks}W-L0W"

    # ── Top K ─────────────────────────────────────────────────────────────
    top_k = 5
    m_top = re.search(r"top\s*(\d+)|(\d+)\s*(?:zonas?|zones?)", q)
    if m_top:
        top_k = int(next(g for g in m_top.groups() if g))

    agg = "mean" if intent == "aggregation" else None

    return {
        "intent": intent,
        "metric": metric,
        "metric_a": metric_a,
        "metric_b": metric_b,
        "metric_a_direction": "high",
        "metric_b_direction": "low",
        "filters": {
            "country": country, "city": city, "zone": zone,
            "zone_type": zone_type, "prioritization": prioritization,
        },
        "time_scope": time_scope,
        "n_weeks": n_weeks,
        "top_k": top_k,
        "sort": "desc",
        "group_by": group_by,
        "aggregation": agg,
        "_source": "rule_based",
    }


def _normalize_parsed(parsed: dict) -> dict:
    """Canonicalize all entity names through semantic_layer after LLM parse."""
    from semantic_layer import (
        resolve_metric, resolve_country,
        resolve_zone_type, resolve_prioritization,
    )
    if parsed.get("metric"):
        r = resolve_metric(parsed["metric"])
        if r: parsed["metric"] = r
    for key in ("metric_a", "metric_b"):
        if parsed.get(key):
            r = resolve_metric(parsed[key])
            if r: parsed[key] = r
    filters = parsed.get("filters", {})
    if filters.get("country"):
        r = resolve_country(filters["country"])
        if r: filters["country"] = r
    if filters.get("zone_type"):
        r = resolve_zone_type(filters["zone_type"])
        if r: filters["zone_type"] = r
    if filters.get("prioritization"):
        r = resolve_prioritization(filters["prioritization"])
        if r: filters["prioritization"] = r
    parsed["filters"] = filters

    group_map = {
        "zone_type": "ZONE_TYPE", "country": "country",
        "city": "city", "prioritization": "ZONE_PRIORITIZATION",
    }
    if parsed.get("group_by"):
        parsed["group_by"] = group_map.get(parsed["group_by"].lower(), parsed["group_by"])

    if not parsed.get("n_weeks") and parsed.get("time_scope"):
        m = re.search(r"L(\d+)W", str(parsed["time_scope"]))
        if m and int(m.group(1)) > 0:
            parsed["n_weeks"] = int(m.group(1))

    return parsed


def parse_query(question: str, context: dict | None = None) -> dict:
    """
    Parse user question → structured intent dict.
    1. Try LLM (credentials read dynamically)
    2. Normalize through semantic_layer
    3. Fall back to rule-based parser
    """
    context = context or {}
    ctx_parts = []
    if context.get("last_metric"):
        ctx_parts.append(f"[Context: previous metric={context['last_metric']}]")
    if context.get("last_country"):
        ctx_parts.append(f"[Context: previous country={context['last_country']}]")
    if context.get("last_zone"):
        ctx_parts.append(f"[Context: previous zone={context['last_zone']}]")
    effective_q = (" ".join(ctx_parts) + " " + question).strip() if ctx_parts else question

    cfg = _get_llm_config()
    raw, llm_error = None, None
    try:
        if cfg["provider"] == "gemini" and cfg["gemini_key"]:
            raw = _call_gemini(effective_q, cfg["gemini_key"])
        elif cfg["provider"] == "groq" and cfg["groq_key"]:
            raw = _call_groq(effective_q, cfg["groq_key"])
        elif cfg["gemini_key"]:
            raw = _call_gemini(effective_q, cfg["gemini_key"])
        elif cfg["groq_key"]:
            raw = _call_groq(effective_q, cfg["groq_key"])
        else:
            llm_error = "no_api_key"
    except Exception as e:
        llm_error = str(e)

    if raw:
        try:
            result = _extract_json(raw)
            result.setdefault("intent", "unknown")
            result.setdefault("metric", None)
            result.setdefault("filters", {})
            result.setdefault("time_scope", "L0W")
            result.setdefault("top_k", 5)
            result.setdefault("sort", "desc")
            result.setdefault("group_by", None)
            result.setdefault("aggregation", None)
            result = _normalize_parsed(result)
            result["_source"] = "llm"
            result["_llm_error"] = None
            if result.get("intent") != "unknown":
                return result
        except Exception as e:
            llm_error = f"json_parse_error: {e}"

    fallback = _rule_based_parse(question, context)
    fallback["_llm_error"] = llm_error
    return fallback
