# 📊 Rappi Operations Analytics — AI Engineer Case

Sistema de análisis inteligente para operaciones Rappi. Permite consultas en lenguaje natural sobre métricas operacionales con respuestas precisas, visualizaciones automáticas e insights accionables.

---

## 🏗️ Arquitectura

```
Pregunta del usuario
       │
       ▼
┌─────────────────┐
│  query_parser   │  ← LLM (google.genai / Groq) — solo interpreta
│  + fallback     │    Rule-based si LLM falla
│  → JSON intent  │    Credenciales leídas DINÁMICAMENTE en cada llamada
└────────┬────────┘
         │  normalize via semantic_layer
         ▼
┌─────────────────┐
│    executor     │  ← pandas + numpy PURO — zero alucinaciones
│  → DataFrame   │    Todos los cálculos aquí
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    chatbot      │  ← LLM — solo redacta la narrativa
│  → Respuesta   │    Fallback determinístico si LLM no disponible
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     charts      │  ← Plotly con formato por unidad de métrica
└─────────────────┘
```

**Principio clave:** El LLM **nunca** calcula. Solo interpreta intención y redacta. Todos los números vienen de pandas.

---

## 📁 Estructura del Proyecto

```
rappi-ai-engineer-case/
│
├── app/
│   ├── streamlit_app.py
│   ├── query_parser.py
│   ├── executor.py
│   ├── chatbot.py
│   ├── insights.py
│   ├── semantic_layer.py
│   ├── charts.py
│   ├── report_generator.py
│   └── utils.py
│
├── data/
│   ├── raw/
│   │   └── dummy_data.xlsx
│   ├── processed/
│   └── metric_dictionary.json
│
├── notebooks/
│   └── eda.ipynb
│
├── reports/
│   ├── executive_report.html
│   └── executive_report.md
│
├── tests/
│   └── test_queries.py
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Instalación y Ejecución

### 1. Preparar entorno

```bash
git clone <repo-url> && cd rappi-ai-engineer-case
python -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

### 2. Configurar API Key

```bash
cp .env.example .env
```

Edita `.env`:

```
# Opción A — Google Gemini Flash (recomendado, gratis en aistudio.google.com)
GEMINI_API_KEY=tu_key_aqui
LLM_PROVIDER=gemini

# Opción B — Groq + Llama 3.3 70B (alternativa, gratis en console.groq.com)
GROQ_API_KEY=tu_key_aqui
LLM_PROVIDER=groq
```

> **Sin API key:** el sistema usa el parser de reglas determinístico — todas las 6 preguntas demo funcionan igual.

### 3. Datos

```bash
# El Excel ya viene incluido en data/raw/dummy_data.xlsx
```

### 4. Ejecutar

```bash
cd app
streamlit run streamlit_app.py
# Abre: http://localhost:8501
```

---

## 💬 6 Preguntas Demo (pre-probadas)

| # | Pregunta | Intent | Funciona sin LLM |
|---|----------|--------|:---:|
| 1 | `¿Cuáles son las 5 zonas con mayor Lead Penetration esta semana?` | ranking | ✅ |
| 2 | `Compara Perfect Orders entre Wealthy y Non Wealthy en Colombia` | comparison | ✅ |
| 3 | `Muestra la evolución de Gross Profit UE en Chapinero últimas 8 semanas` | trend | ✅ |
| 4 | `¿Cuál es el promedio de Lead Penetration por país?` | aggregation | ✅ |
| 5 | `¿Qué zonas tienen alto Lead Penetration pero bajo Perfect Orders?` | multivariable | ✅ |
| 6 | `¿Cuáles son las zonas que más crecen en órdenes en las últimas 5 semanas?` | growth_explanation | ✅ |

**Follow-ups contextuales:**
- `¿y ahora solo en Colombia?` → reutiliza métrica del turno anterior
- `Compáralo contra zonas High Priority` → reutiliza contexto de país
- Click en cualquier sugerencia → ejecuta automáticamente

---

## 🔍 Sistema de Insights Automáticos (6 categorías)

| Categoría | Regla | Sin LLM |
|-----------|-------|:-------:|
| 🚨 Anomalías | Cambio WoW > 10% con umbral absoluto mínimo por métrica | ✅ |
| 📉 Tendencias | 3+ semanas consecutivas de deterioro | ✅ |
| 📊 Benchmarking | Z-score > 1.5 vs. pares (mismo país + zone_type), sin outliers | ✅ |
| 🔗 Correlaciones | Pearson > 0.5 entre pares de métricas | ✅ |
| 🌟 Oportunidades | Alto Lead Pen + órdenes crecientes + bajo PO vs. **pares**, base ≥ 50 órdenes | ✅ |
| ⚠️ Calidad de datos | Valores fuera de rango esperado por métrica | ✅ |

---

## ⚙️ Decisiones Técnicas

### LLM solo interpreta — pandas calcula todo
Un agente libre que genera código puede alucinar. La arquitectura híbrida garantiza reproducibilidad y auditabilidad. El LLM hace exactamente dos cosas: parsear intención y redactar narrativa.

### Parser con fallback por reglas
Si el LLM no está disponible o devuelve JSON inválido, un parser determinístico cubre los 6 intents core. Detección dinámica de zonas/ciudades sin hardcoding.

### google.genai (nuevo SDK)
Migrado desde el deprecado `google.generativeai`. Con fallback al legacy si no está instalado. Groq usa `llama-3.3-70b-versatile`.

### Credenciales 100% dinámicas
`_get_llm_config()` lee `os.environ` en cada llamada. El sidebar actualiza `os.environ` antes de cualquier llamada LLM. Elimina el bug de credenciales cacheadas al importar.

### Cache con invalidación automática
El pickle de datos procesados se invalida cuando cambia el Excel fuente (mtime + size fingerprint). No hay riesgo de leer datos viejos.

### Formato de valores por unidad de métrica
`metric_dictionary.json` define la unidad de cada métrica. `_fmt_val()` y `_axis_fmt()` usan esa fuente única — nunca heurísticas ad-hoc.

### Anomalías con dual threshold
Cambio relativo > 10% Y cambio absoluto > mínimo por tipo de métrica. Elimina artefactos por denominadores cerca de cero (e.g. GP UE de 0.001 → 1.5 ya no genera -134,000%).

---

## 🧪 Tests

```bash
cd rappi-ai-engineer-case
python tests/test_queries.py   # 57 tests, sin pytest ni LLM requerido
```

Cobertura: semantic layer, parser, executor (6 intents), insights (6 categorías), reports, consistency.

---

## 💰 Costo estimado por uso

| Escenario | Provider | Costo |
|-----------|----------|-------|
| Demo completa (10-15 preguntas) | Gemini Free | $0 |
| 100 preguntas/día | Gemini Free | $0 |
| Sin API key (fallback) | — | $0 |
| Alta carga (>1500 req/día) | Gemini paid | ~$0.01-0.05/sesión |

---

## ⚠️ Limitaciones conocidas

1. **Datos simulados:** El dataset es dummy/anonimizado. Los insights son demostrativos, no operacionales.
2. **Memoria conversacional en sesión:** `st.session_state` — se pierde al recargar la página.
3. **Sin deployment:** Funciona en localhost. Para producción: Streamlit Cloud + autenticación.
4. **GP UE con valores extremos:** Algunos valores están fuera de rango esperado (documentados como `data_quality` alerts en el reporte).
5. **Granularidad semanal:** No hay datos intra-semana.

---

## 🔮 Próximos pasos

- [ ] Integración con warehouse real (BigQuery / Redshift)
- [ ] Alertas automáticas por email/Slack al detectar anomalías de alta severidad
- [ ] Deployment en Streamlit Cloud con autenticación SSO
- [ ] Forecasting semanal con Prophet/ARIMA
- [ ] Export a PDF con gráficos embebidos
- [ ] Tests de UI con Streamlit testing framework

---

## 📦 Stack

`Python 3.12` · `Streamlit` · `pandas` · `NumPy` · `Plotly` · `google.genai` · `groq`
