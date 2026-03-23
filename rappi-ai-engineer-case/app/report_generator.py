"""
report_generator.py — Generates executive reports in Markdown and HTML.
Uses pre-computed insights. No LLM required for report structure.
"""

from datetime import datetime

import pandas as pd

from insights import format_insight_card


RAPPI_ORANGE = "#FF441F"

HTML_STYLE = f"""
<style>
  body {{ font-family: 'Inter', -apple-system, sans-serif; margin: 0; background: #f8f9fa; color: #1a1a2e; }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 40px 20px; }}
  .header {{ background: linear-gradient(135deg, {RAPPI_ORANGE} 0%, #ff6b4a 100%);
             color: white; padding: 40px; border-radius: 16px; margin-bottom: 32px; }}
  .header h1 {{ margin: 0; font-size: 2rem; }}
  .header p {{ margin: 8px 0 0; opacity: 0.9; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                   gap: 16px; margin-bottom: 32px; }}
  .stat-card {{ background: white; border-radius: 12px; padding: 20px; text-align: center;
                box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
  .stat-card .number {{ font-size: 2rem; font-weight: 700; color: {RAPPI_ORANGE}; }}
  .stat-card .label {{ font-size: 0.85rem; color: #666; margin-top: 4px; }}
  .section {{ margin-bottom: 32px; }}
  .section h2 {{ font-size: 1.3rem; border-bottom: 3px solid {RAPPI_ORANGE}; padding-bottom: 8px;
                 margin-bottom: 20px; }}
  .insight-card {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 16px;
                   box-shadow: 0 2px 8px rgba(0,0,0,.06); border-left: 4px solid {RAPPI_ORANGE}; }}
  .insight-card.alta {{ border-left-color: #e74c3c; }}
  .insight-card.media {{ border-left-color: {RAPPI_ORANGE}; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 0.8rem;
            font-weight: 600; background: #fff3f0; color: {RAPPI_ORANGE}; margin-bottom: 8px; }}
  .badge.alta {{ background: #ffeaea; color: #c0392b; }}
  .insight-title {{ font-size: 1rem; font-weight: 700; margin: 0 0 10px; }}
  .insight-field {{ margin-bottom: 6px; font-size: 0.9rem; }}
  .insight-field strong {{ color: #333; }}
  .footer {{ text-align: center; font-size: 0.8rem; color: #999; margin-top: 48px; }}
</style>
"""


def _severity_badge(severity: str) -> str:
    cls = "alta" if severity == "alta" else "media"
    label = "🔴 Alta" if severity == "alta" else "🟠 Media"
    return f'<span class="badge {cls}">{label}</span>'


def _insight_html(card: dict, idx: int) -> str:
    sev = card.get("severity", "media")
    return f"""
  <div class="insight-card {sev}">
    {_severity_badge(sev)}
    <p class="badge">{card.get('category','')}</p>
    <h3 class="insight-title">{idx}. {card.get('title','')}</h3>
    <div class="insight-field"><strong>📋 Evidencia:</strong> {card.get('evidence','')}</div>
    <div class="insight-field"><strong>❓ Por qué importa:</strong> {card.get('why_it_matters','')}</div>
    <div class="insight-field"><strong>✅ Recomendación:</strong> {card.get('recommendation','')}</div>
  </div>"""


def generate_markdown_report(insights_data: dict, summary_stats: dict) -> str:
    """Generate executive report in Markdown format."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Reporte Ejecutivo — Análisis de Operaciones Rappi",
        f"**Generado:** {now}  ",
        f"**Fuente:** Sistema de Análisis Inteligente (AI Engineer Case)  ",
        "",
        "---",
        "",
        "## Resumen Ejecutivo",
        "",
        f"Se analizaron **{summary_stats.get('n_zones', 0):,} zonas** en "
        f"**{summary_stats.get('n_countries', 0)} países**, evaluando "
        f"**{summary_stats.get('n_metrics', 0)} métricas operacionales** a lo largo de las últimas 9 semanas.",
        "",
        f"El análisis automático identificó **{insights_data.get('total', 0)} hallazgos** agrupados en 6 categorías:",
        "",
    ]

    # Summary bullets
    cats = [
        ("anomalies", "🚨 Anomalías WoW (>10%)"),
        ("trends", "📉 Tendencias preocupantes (3+ semanas)"),
        ("benchmarks", "📊 Outliers vs. pares"),
        ("correlations", "🔗 Correlaciones significativas"),
        ("opportunities", "🌟 Oportunidades de mejora"),
    ]
    for key, label in cats:
        n = len(insights_data.get(key, []))
        lines.append(f"- **{label}:** {n} hallazgos")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Top critical findings
    all_insights = []
    for key in ["trends", "anomalies", "benchmarks", "opportunities", "correlations"]:
        for raw in insights_data.get(key, []):
            card = format_insight_card(raw)
            card["_raw_type"] = key
            all_insights.append(card)

    # Diversified top-5: one per category, then fill with highest severity
    top_findings = []
    seen_categories = set()
    priority_keys = ["trends", "anomalies", "benchmarks", "opportunities", "correlations", "data_quality"]
    for key in priority_keys:
        for raw in insights_data.get(key, []):
            card = format_insight_card(raw)
            if card["category"] not in seen_categories:
                seen_categories.add(card["category"])
                top_findings.append(card)
                break
    # Fill remaining slots with highest severity
    remaining = [c for c in all_insights if c not in top_findings]
    remaining.sort(key=lambda x: x.get("severity", "media") == "alta", reverse=True)
    top_findings = (top_findings + remaining)[:5]

    lines.append("## Top 5 Hallazgos Críticos")
    lines.append("")
    for i, card in enumerate(top_findings, 1):
        lines.append(f"### {i}. {card['title']}")
        lines.append(f"**Categoría:** {card['category']}  ")
        lines.append(f"**Evidencia:** {card['evidence']}  ")
        lines.append(f"**Por qué importa:** {card['why_it_matters']}  ")
        lines.append(f"**Recomendación:** {card['recommendation']}  ")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Detail by category
    section_map = [
        ("anomalies", "Anomalías Detectadas"),
        ("trends", "Tendencias Preocupantes"),
        ("benchmarks", "Benchmarking de Zonas"),
        ("correlations", "Correlaciones entre Métricas"),
        ("opportunities", "Oportunidades Identificadas"),
        ("data_quality", "Alertas de Calidad de Datos"),
    ]

    for key, title in section_map:
        raw_list = insights_data.get(key, [])
        if not raw_list:
            continue
        lines.append(f"## {title}")
        lines.append("")
        for i, raw in enumerate(raw_list[:8], 1):
            card = format_insight_card(raw)
            severity_icon = "🔴" if card.get("severity") == "alta" else "🟠"
            lines.append(f"**{severity_icon} {i}. {card['title']}**")
            lines.append(f"- *Evidencia:* {card['evidence']}")
            lines.append(f"- *Por qué importa:* {card['why_it_matters']}")
            lines.append(f"- *Recomendación:* {card['recommendation']}")
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Recomendaciones Finales")
    lines.append("")
    lines.append("1. **Priorizar zonas de alta severidad** con deterioro consistente en métricas de calidad (Perfect Orders).")
    lines.append("2. **Capitalizar las oportunidades identificadas** donde la oferta está lista pero la ejecución es subóptima.")
    lines.append("3. **Investigar correlaciones** para diseñar intervenciones que impacten múltiples métricas simultáneamente.")
    lines.append("4. **Monitorear semanalmente** las anomalías detectadas para validar si son eventos puntuales o tendencias.")
    lines.append("5. **Replicar best practices** de zonas que superan a sus pares en métricas clave.")
    lines.append("")
    lines.append("---")
    lines.append(f"*Reporte generado automáticamente por el Sistema de Análisis Inteligente Rappi — {now}*")

    return "\n".join(lines)


def generate_html_report(insights_data: dict, summary_stats: dict) -> str:
    """Generate executive report in HTML format."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    all_insights = []
    for key in ["trends", "anomalies", "benchmarks", "opportunities", "correlations"]:
        for raw in insights_data.get(key, []):
            card = format_insight_card(raw)
            card["_key"] = key
            all_insights.append(card)

    # Diversified top-5: one per category, then fill with highest severity
    top_findings = []
    seen_categories = set()
    priority_keys = ["trends", "anomalies", "benchmarks", "opportunities", "correlations", "data_quality"]
    for key in priority_keys:
        for raw in insights_data.get(key, []):
            card = format_insight_card(raw)
            if card["category"] not in seen_categories:
                seen_categories.add(card["category"])
                top_findings.append(card)
                break
    # Fill remaining slots with highest severity
    remaining = [c for c in all_insights if c not in top_findings]
    remaining.sort(key=lambda x: x.get("severity", "media") == "alta", reverse=True)
    top_findings = (top_findings + remaining)[:5]

    # Build sections HTML
    sections_html = ""

    # Top 5 findings
    top_html = "".join(_insight_html(card, i+1) for i, card in enumerate(top_findings))
    sections_html += f"""
  <div class="section">
    <h2>🏆 Top 5 Hallazgos Críticos</h2>
    {top_html}
  </div>"""

    section_map = [
        ("anomalies", "🚨 Anomalías Detectadas"),
        ("trends", "📉 Tendencias Preocupantes"),
        ("benchmarks", "📊 Benchmarking de Zonas"),
        ("correlations", "🔗 Correlaciones entre Métricas"),
        ("opportunities", "🌟 Oportunidades Identificadas"),
        ("data_quality", "⚠️ Alertas de Calidad de Datos"),
    ]

    for key, title in section_map:
        raw_list = insights_data.get(key, [])
        if not raw_list:
            continue
        cards_html = "".join(
            _insight_html(format_insight_card(raw), i+1)
            for i, raw in enumerate(raw_list[:8])
        )
        sections_html += f"""
  <div class="section">
    <h2>{title}</h2>
    {cards_html}
  </div>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reporte Ejecutivo — Rappi Ops Analytics</title>
  {HTML_STYLE}
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>📊 Reporte Ejecutivo — Operaciones Rappi</h1>
      <p>Sistema de Análisis Inteligente | Generado: {now}</p>
    </div>

    <div class="summary-grid">
      <div class="stat-card">
        <div class="number">{summary_stats.get('n_zones', 0):,}</div>
        <div class="label">Zonas analizadas</div>
      </div>
      <div class="stat-card">
        <div class="number">{summary_stats.get('n_countries', 0)}</div>
        <div class="label">Países</div>
      </div>
      <div class="stat-card">
        <div class="number">{summary_stats.get('n_metrics', 0)}</div>
        <div class="label">Métricas</div>
      </div>
      <div class="stat-card">
        <div class="number">{len(insights_data.get('anomalies', []))}</div>
        <div class="label">Anomalías</div>
      </div>
      <div class="stat-card">
        <div class="number">{len(insights_data.get('trends', []))}</div>
        <div class="label">Tendencias preoc.</div>
      </div>
      <div class="stat-card">
        <div class="number">{len(insights_data.get('opportunities', []))}</div>
        <div class="label">Oportunidades</div>
      </div>
    </div>

    {sections_html}

    <div class="section">
      <h2>✅ Recomendaciones Finales</h2>
      <div class="insight-card">
        <ol>
          <li><strong>Priorizar zonas de alta severidad</strong> con deterioro consistente en métricas de calidad (Perfect Orders).</li>
          <li><strong>Capitalizar las oportunidades identificadas</strong> donde la oferta está lista pero la ejecución es subóptima.</li>
          <li><strong>Investigar correlaciones</strong> para diseñar intervenciones que impacten múltiples métricas simultáneamente.</li>
          <li><strong>Monitorear semanalmente</strong> las anomalías detectadas para validar si son eventos puntuales o tendencias.</li>
          <li><strong>Replicar best practices</strong> de zonas que superan a sus pares en métricas clave.</li>
        </ol>
      </div>
    </div>

    <div class="footer">
      Reporte generado automáticamente por el Sistema de Análisis Inteligente Rappi — {now}
    </div>
  </div>
</body>
</html>"""

    return html
