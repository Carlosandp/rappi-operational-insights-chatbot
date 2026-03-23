# rappi-operational-insights-chatbot

AI-powered chatbot for operational analytics, natural language KPI queries, and automated executive insight generation.

## Overview

This project was developed as a technical solution for an AI Engineer case study. It enables users to query operational metrics in natural language, generate visual analyses, and produce automated executive insights from a structured dataset.

The system combines:
- A conversational analytics interface
- A deterministic analytical engine based on pandas
- Automated insight generation
- Executive report generation in Markdown and HTML

## Key Idea

The language model is used only for:
1. Interpreting user intent
2. Generating natural-language responses

All numerical calculations, aggregations, comparisons, and metric logic are executed deterministically with pandas and NumPy.

This design improves reproducibility, transparency, and control over results.

---

## Architecture

```text
User Question
     │
     ▼
┌─────────────────────┐
│ Query Parser        │
│ LLM + rule fallback │
│ → structured intent │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Analytical Executor │
│ pandas + NumPy      │
│ → validated results │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Response Generator  │
│ LLM or fallback     │
│ → narrative output  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Charts & Reports    │
│ Plotly + HTML/MD    │
└─────────────────────┘
