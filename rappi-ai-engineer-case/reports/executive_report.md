# Reporte Ejecutivo — Análisis de Operaciones Rappi
**Generado:** 2026-03-23 03:27  
**Fuente:** Sistema de Análisis Inteligente (AI Engineer Case)  

---

## Resumen Ejecutivo

Se analizaron **980 zonas** en **9 países**, evaluando **13 métricas operacionales** a lo largo de las últimas 9 semanas.

El análisis automático identificó **58 hallazgos** agrupados en 6 categorías:

- **🚨 Anomalías WoW (>10%):** 20 hallazgos
- **📉 Tendencias preocupantes (3+ semanas):** 10 hallazgos
- **📊 Outliers vs. pares:** 15 hallazgos
- **🔗 Correlaciones significativas:** 5 hallazgos
- **🌟 Oportunidades de mejora:** 8 hallazgos

---

## Top 5 Hallazgos Críticos

### 1. Deterioro sostenido de Perfect Orders — Manta Beach (EC)
**Categoría:** 📉 Tendencia Preocupante  
**Evidencia:** Perfect Orders ha caído 8 semanas consecutivas en Manta Beach (EC). Cambio acumulado: -9.8%. Valor actual: 0.776.  
**Por qué importa:** Un deterioro de 8+ semanas sugiere un problema estructural, no un evento puntual. Puede afectar retención y GMV.  
**Recomendación:** Priorizar revisión en Manta Beach: revisar tasa de defectos, cancelaciones y SLA de entrega.  

### 2. Deterioro brusca en Restaurants Markdowns / GMV — Raito de luz (EC)
**Categoría:** 🚨 Anomalía  
**Evidencia:** Restaurants Markdowns / GMV cambió +212.0% WoW (0.030 → 0.095) en Raito de luz.  
**Por qué importa:** Un cambio abrupto puede indicar un problema operacional puntual o una mejora inesperada que merece seguimiento.  
**Recomendación:** Investigar causa del deterioro en Raito de luz: revisar operaciones y datos de la zona.  

### 3. Subperformance en Perfect Orders — CDG La Hacienda (MX)
**Categoría:** 📊 Benchmarking  
**Evidencia:** CDG La Hacienda: Perfect Orders = 0.242 vs. promedio de pares (Non Wealthy, MX) = 0.867. Z-score: -6.78.  
**Por qué importa:** La divergencia respecto a pares puede revelar prácticas o condiciones específicas.  
**Recomendación:** Investigar qué falla en CDG La Hacienda y replicar al resto del grupo: revisar tasa de defectos, cancelaciones y SLA de entrega.  

### 4. Oportunidad de mejora en calidad — Colina (CL)
**Categoría:** 🌟 Oportunidad  
**Evidencia:** Alta oferta vs. pares (CL/Non Wealthy) — Lead Pen: 34.2%, Perfect Orders: 81.8% (umbral peers: 82.5%). Crecimiento órdenes (4w): +35.3% sobre base de 119 órdenes.  
**Por qué importa:** Esta zona tiene buena oferta y demanda creciente, pero calidad por debajo de sus pares. Mejorar Perfect Orders aquí puede amplificar el crecimiento.  
**Recomendación:** Activar plan de calidad en Colina: revisar operaciones y datos de la zona.  

### 5. Correlación positiva entre MLTV Top Verticals Adoption y Turbo Adoption
**Categoría:** 🔗 Correlación  
**Evidencia:** Correlación Pearson = 0.79 (79% de fuerza asociativa).  
**Por qué importa:** Zonas con alto MLTV Top Verticals Adoption tienden a tener también alto Turbo Adoption  
**Recomendación:** Usar esta relación para priorizar intervenciones: mejorar la métrica palanca puede impactar ambas simultáneamente.  

---

## Anomalías Detectadas

**🔴 1. Deterioro brusca en Restaurants Markdowns / GMV — Raito de luz (EC)**
- *Evidencia:* Restaurants Markdowns / GMV cambió +212.0% WoW (0.030 → 0.095) en Raito de luz.
- *Por qué importa:* Un cambio abrupto puede indicar un problema operacional puntual o una mejora inesperada que merece seguimiento.
- *Recomendación:* Investigar causa del deterioro en Raito de luz: revisar operaciones y datos de la zona.

**🔴 2. Deterioro brusca en Pro Adoption (Last Week Status) — Cinco Conjuntos (BR)**
- *Evidencia:* Pro Adoption (Last Week Status) cambió -100.0% WoW (0.333 → 0.000) en Cinco Conjuntos.
- *Por qué importa:* Un cambio abrupto puede indicar un problema operacional puntual o una mejora inesperada que merece seguimiento.
- *Recomendación:* Investigar causa del deterioro en Cinco Conjuntos: revisar comunicación y beneficios del programa Pro.

**🔴 3. Deterioro brusca en Retail SST > SS CVR — SC - FLN - Ilha Norte (BR)**
- *Evidencia:* Retail SST > SS CVR cambió -100.0% WoW (0.020 → 0.000) en SC - FLN - Ilha Norte.
- *Por qué importa:* Un cambio abrupto puede indicar un problema operacional puntual o una mejora inesperada que merece seguimiento.
- *Recomendación:* Investigar causa del deterioro en SC - FLN - Ilha Norte: revisar disponibilidad y presentación de supermercados.

**🔴 4. Deterioro brusca en Pro Adoption (Last Week Status) — Campina Grande MP (BR)**
- *Evidencia:* Pro Adoption (Last Week Status) cambió -100.0% WoW (0.250 → 0.000) en Campina Grande MP.
- *Por qué importa:* Un cambio abrupto puede indicar un problema operacional puntual o una mejora inesperada que merece seguimiento.
- *Recomendación:* Investigar causa del deterioro en Campina Grande MP: revisar comunicación y beneficios del programa Pro.

**🔴 5. Deterioro brusca en Non-Pro PTC > OP — TEZ_Centro (MX)**
- *Evidencia:* Non-Pro PTC > OP cambió -100.0% WoW (0.100 → 0.000) en TEZ_Centro.
- *Por qué importa:* Un cambio abrupto puede indicar un problema operacional puntual o una mejora inesperada que merece seguimiento.
- *Recomendación:* Investigar causa del deterioro en TEZ_Centro: revisar el funnel de checkout y posibles fricciones de pago.

**🔴 6. Deterioro brusca en Non-Pro PTC > OP — SC - FLN - Ilha Sul (BR)**
- *Evidencia:* Non-Pro PTC > OP cambió -100.0% WoW (0.083 → 0.000) en SC - FLN - Ilha Sul.
- *Por qué importa:* Un cambio abrupto puede indicar un problema operacional puntual o una mejora inesperada que merece seguimiento.
- *Recomendación:* Investigar causa del deterioro en SC - FLN - Ilha Sul: revisar el funnel de checkout y posibles fricciones de pago.

**🔴 7. Deterioro brusca en % PRO Users Who Breakeven — TLX San Diego Metepec (MX)**
- *Evidencia:* % PRO Users Who Breakeven cambió -100.0% WoW (0.067 → 0.000) en TLX San Diego Metepec.
- *Por qué importa:* Un cambio abrupto puede indicar un problema operacional puntual o una mejora inesperada que merece seguimiento.
- *Recomendación:* Investigar causa del deterioro en TLX San Diego Metepec: revisar operaciones y datos de la zona.

**🔴 8. Deterioro brusca en Pro Adoption (Last Week Status) — ZAZUE ESTE (CO)**
- *Evidencia:* Pro Adoption (Last Week Status) cambió -100.0% WoW (0.333 → 0.000) en ZAZUE ESTE.
- *Por qué importa:* Un cambio abrupto puede indicar un problema operacional puntual o una mejora inesperada que merece seguimiento.
- *Recomendación:* Investigar causa del deterioro en ZAZUE ESTE: revisar comunicación y beneficios del programa Pro.

---

## Tendencias Preocupantes

**🔴 1. Deterioro sostenido de Perfect Orders — Manta Beach (EC)**
- *Evidencia:* Perfect Orders ha caído 8 semanas consecutivas en Manta Beach (EC). Cambio acumulado: -9.8%. Valor actual: 0.776.
- *Por qué importa:* Un deterioro de 8+ semanas sugiere un problema estructural, no un evento puntual. Puede afectar retención y GMV.
- *Recomendación:* Priorizar revisión en Manta Beach: revisar tasa de defectos, cancelaciones y SLA de entrega.

**🔴 2. Deterioro sostenido de MLTV Top Verticals Adoption — Centro Historico Arequipa (PE)**
- *Evidencia:* MLTV Top Verticals Adoption ha caído 8 semanas consecutivas en Centro Historico Arequipa (PE). Cambio acumulado: -15.7%. Valor actual: 0.122.
- *Por qué importa:* Un deterioro de 8+ semanas sugiere un problema estructural, no un evento puntual. Puede afectar retención y GMV.
- *Recomendación:* Priorizar revisión en Centro Historico Arequipa: revisar operaciones y datos de la zona.

**🔴 3. Deterioro sostenido de MLTV Top Verticals Adoption — MG - BH - Contagem (BR)**
- *Evidencia:* MLTV Top Verticals Adoption ha caído 8 semanas consecutivas en MG - BH - Contagem (BR). Cambio acumulado: -100.0%. Valor actual: 0.000.
- *Por qué importa:* Un deterioro de 8+ semanas sugiere un problema estructural, no un evento puntual. Puede afectar retención y GMV.
- *Recomendación:* Priorizar revisión en MG - BH - Contagem: revisar operaciones y datos de la zona.

**🔴 4. Deterioro sostenido de MLTV Top Verticals Adoption — Contry (MX)**
- *Evidencia:* MLTV Top Verticals Adoption ha caído 8 semanas consecutivas en Contry (MX). Cambio acumulado: -7.1%. Valor actual: 0.289.
- *Por qué importa:* Un deterioro de 8+ semanas sugiere un problema estructural, no un evento puntual. Puede afectar retención y GMV.
- *Recomendación:* Priorizar revisión en Contry: revisar operaciones y datos de la zona.

**🔴 5. Deterioro sostenido de % Restaurants Sessions With Optimal Assortment — SP - SP - Socorro/Cidade Dutra (BR)**
- *Evidencia:* % Restaurants Sessions With Optimal Assortment ha caído 8 semanas consecutivas en SP - SP - Socorro/Cidade Dutra (BR). Cambio acumulado: -19.8%. Valor actual: 0.417.
- *Por qué importa:* Un deterioro de 8+ semanas sugiere un problema estructural, no un evento puntual. Puede afectar retención y GMV.
- *Recomendación:* Priorizar revisión en SP - SP - Socorro/Cidade Dutra: revisar operaciones y datos de la zona.

**🔴 6. Deterioro sostenido de Lead Penetration — SP - SP - Itaim Bibi (BR)**
- *Evidencia:* Lead Penetration ha caído 8 semanas consecutivas en SP - SP - Itaim Bibi (BR). Cambio acumulado: -11.1%. Valor actual: 0.155.
- *Por qué importa:* Un deterioro de 8+ semanas sugiere un problema estructural, no un evento puntual. Puede afectar retención y GMV.
- *Recomendación:* Priorizar revisión en SP - SP - Itaim Bibi: revisar habilitación de tiendas y densidad de oferta en la zona.

**🔴 7. Deterioro sostenido de % Restaurants Sessions With Optimal Assortment — SP - SP - Limao/Casa Verde (BR)**
- *Evidencia:* % Restaurants Sessions With Optimal Assortment ha caído 8 semanas consecutivas en SP - SP - Limao/Casa Verde (BR). Cambio acumulado: -3.5%. Valor actual: 0.864.
- *Por qué importa:* Un deterioro de 8+ semanas sugiere un problema estructural, no un evento puntual. Puede afectar retención y GMV.
- *Recomendación:* Priorizar revisión en SP - SP - Limao/Casa Verde: revisar operaciones y datos de la zona.

**🔴 8. Deterioro sostenido de Lead Penetration — DF - BSB - Lago Norte (BR)**
- *Evidencia:* Lead Penetration ha caído 8 semanas consecutivas en DF - BSB - Lago Norte (BR). Cambio acumulado: -23.2%. Valor actual: 0.231.
- *Por qué importa:* Un deterioro de 8+ semanas sugiere un problema estructural, no un evento puntual. Puede afectar retención y GMV.
- *Recomendación:* Priorizar revisión en DF - BSB - Lago Norte: revisar habilitación de tiendas y densidad de oferta en la zona.

---

## Benchmarking de Zonas

**🔴 1. Subperformance en Perfect Orders — CDG La Hacienda (MX)**
- *Evidencia:* CDG La Hacienda: Perfect Orders = 0.242 vs. promedio de pares (Non Wealthy, MX) = 0.867. Z-score: -6.78.
- *Por qué importa:* La divergencia respecto a pares puede revelar prácticas o condiciones específicas.
- *Recomendación:* Investigar qué falla en CDG La Hacienda y replicar al resto del grupo: revisar tasa de defectos, cancelaciones y SLA de entrega.

**🔴 2. Subperformance en Perfect Orders — CDG Centro (MX)**
- *Evidencia:* CDG Centro: Perfect Orders = 0.278 vs. promedio de pares (Non Wealthy, MX) = 0.867. Z-score: -6.39.
- *Por qué importa:* La divergencia respecto a pares puede revelar prácticas o condiciones específicas.
- *Recomendación:* Investigar qué falla en CDG Centro y replicar al resto del grupo: revisar tasa de defectos, cancelaciones y SLA de entrega.

**🔴 3. Subperformance en Perfect Orders — ACU Centro (MX)**
- *Evidencia:* ACU Centro: Perfect Orders = 0.320 vs. promedio de pares (Non Wealthy, MX) = 0.867. Z-score: -5.93.
- *Por qué importa:* La divergencia respecto a pares puede revelar prácticas o condiciones específicas.
- *Recomendación:* Investigar qué falla en ACU Centro y replicar al resto del grupo: revisar tasa de defectos, cancelaciones y SLA de entrega.

**🔴 4. Subperformance en Perfect Orders — GO - GYN - Jd. Novo Mundo (BR)**
- *Evidencia:* GO - GYN - Jd. Novo Mundo: Perfect Orders = 0.328 vs. promedio de pares (Wealthy, BR) = 0.849. Z-score: -4.92.
- *Por qué importa:* La divergencia respecto a pares puede revelar prácticas o condiciones específicas.
- *Recomendación:* Investigar qué falla en GO - GYN - Jd. Novo Mundo y replicar al resto del grupo: revisar tasa de defectos, cancelaciones y SLA de entrega.

**🔴 5. Subperformance en Perfect Orders — Usme (CO)**
- *Evidencia:* Usme: Perfect Orders = 0.694 vs. promedio de pares (Non Wealthy, CO) = 0.879. Z-score: -4.19.
- *Por qué importa:* La divergencia respecto a pares puede revelar prácticas o condiciones específicas.
- *Recomendación:* Investigar qué falla en Usme y replicar al resto del grupo: revisar tasa de defectos, cancelaciones y SLA de entrega.

**🔴 6. Sobreperformance en Lead Penetration — SP - VCP - Jardim Santa Lúcia (BR)**
- *Evidencia:* SP - VCP - Jardim Santa Lúcia: Lead Penetration = 1.100 vs. promedio de pares (Non Wealthy, BR) = 0.100. Z-score: +6.91.
- *Por qué importa:* La divergencia respecto a pares puede revelar prácticas o condiciones específicas.
- *Recomendación:* Identificar best practices de SP - VCP - Jardim Santa Lúcia y replicar al resto del grupo: revisar habilitación de tiendas y densidad de oferta en la zona.

**🔴 7. Sobreperformance en Lead Penetration — TLX CHIAUTEMPAN (MX)**
- *Evidencia:* TLX CHIAUTEMPAN: Lead Penetration = 0.933 vs. promedio de pares (Non Wealthy, MX) = 0.156. Z-score: +6.23.
- *Por qué importa:* La divergencia respecto a pares puede revelar prácticas o condiciones específicas.
- *Recomendación:* Identificar best practices de TLX CHIAUTEMPAN y replicar al resto del grupo: revisar habilitación de tiendas y densidad de oferta en la zona.

**🔴 8. Sobreperformance en Lead Penetration — GUA_SUR (MX)**
- *Evidencia:* GUA_SUR: Lead Penetration = 0.922 vs. promedio de pares (Non Wealthy, MX) = 0.156. Z-score: +6.14.
- *Por qué importa:* La divergencia respecto a pares puede revelar prácticas o condiciones específicas.
- *Recomendación:* Identificar best practices de GUA_SUR y replicar al resto del grupo: revisar habilitación de tiendas y densidad de oferta en la zona.

---

## Correlaciones entre Métricas

**🔴 1. Correlación positiva entre MLTV Top Verticals Adoption y Turbo Adoption**
- *Evidencia:* Correlación Pearson = 0.79 (79% de fuerza asociativa).
- *Por qué importa:* Zonas con alto MLTV Top Verticals Adoption tienden a tener también alto Turbo Adoption
- *Recomendación:* Usar esta relación para priorizar intervenciones: mejorar la métrica palanca puede impactar ambas simultáneamente.

**🟠 2. Correlación positiva entre Non-Pro PTC > OP y Restaurants SS > ATC CVR**
- *Evidencia:* Correlación Pearson = 0.69 (69% de fuerza asociativa).
- *Por qué importa:* Zonas con alto Non-Pro PTC > OP tienden a tener también alto Restaurants SS > ATC CVR
- *Recomendación:* Usar esta relación para priorizar intervenciones: mejorar la métrica palanca puede impactar ambas simultáneamente.

**🟠 3. Correlación positiva entre MLTV Top Verticals Adoption y Pro Adoption (Last Week Status)**
- *Evidencia:* Correlación Pearson = 0.68 (68% de fuerza asociativa).
- *Por qué importa:* Zonas con alto MLTV Top Verticals Adoption tienden a tener también alto Pro Adoption (Last Week Status)
- *Recomendación:* Usar esta relación para priorizar intervenciones: mejorar la métrica palanca puede impactar ambas simultáneamente.

**🟠 4. Correlación positiva entre % Restaurants Sessions With Optimal Assortment y Restaurants SS > ATC CVR**
- *Evidencia:* Correlación Pearson = 0.67 (67% de fuerza asociativa).
- *Por qué importa:* Zonas con alto % Restaurants Sessions With Optimal Assortment tienden a tener también alto Restaurants SS > ATC CVR
- *Recomendación:* Usar esta relación para priorizar intervenciones: mejorar la métrica palanca puede impactar ambas simultáneamente.

**🟠 5. Correlación positiva entre % PRO Users Who Breakeven y Restaurants SS > ATC CVR**
- *Evidencia:* Correlación Pearson = 0.65 (65% de fuerza asociativa).
- *Por qué importa:* Zonas con alto % PRO Users Who Breakeven tienden a tener también alto Restaurants SS > ATC CVR
- *Recomendación:* Usar esta relación para priorizar intervenciones: mejorar la métrica palanca puede impactar ambas simultáneamente.

---

## Oportunidades Identificadas

**🟠 1. Oportunidad de mejora en calidad — Colina (CL)**
- *Evidencia:* Alta oferta vs. pares (CL/Non Wealthy) — Lead Pen: 34.2%, Perfect Orders: 81.8% (umbral peers: 82.5%). Crecimiento órdenes (4w): +35.3% sobre base de 119 órdenes.
- *Por qué importa:* Esta zona tiene buena oferta y demanda creciente, pero calidad por debajo de sus pares. Mejorar Perfect Orders aquí puede amplificar el crecimiento.
- *Recomendación:* Activar plan de calidad en Colina: revisar operaciones y datos de la zona.

**🟠 2. Oportunidad de mejora en calidad — TCE Santa Anita (MX)**
- *Evidencia:* Alta oferta vs. pares (MX/Non Wealthy) — Lead Pen: 66.7%, Perfect Orders: 71.7% (umbral peers: 88.3%). Crecimiento órdenes (4w): +21.6% sobre base de 51 órdenes.
- *Por qué importa:* Esta zona tiene buena oferta y demanda creciente, pero calidad por debajo de sus pares. Mejorar Perfect Orders aquí puede amplificar el crecimiento.
- *Recomendación:* Activar plan de calidad en TCE Santa Anita: revisar operaciones y datos de la zona.

**🟠 3. Oportunidad de mejora en calidad — VALL Centro (MX)**
- *Evidencia:* Alta oferta vs. pares (MX/Non Wealthy) — Lead Pen: 49.5%, Perfect Orders: 68.5% (umbral peers: 88.3%). Crecimiento órdenes (4w): +14.0% sobre base de 86 órdenes.
- *Por qué importa:* Esta zona tiene buena oferta y demanda creciente, pero calidad por debajo de sus pares. Mejorar Perfect Orders aquí puede amplificar el crecimiento.
- *Recomendación:* Activar plan de calidad en VALL Centro: revisar operaciones y datos de la zona.

**🟠 4. Oportunidad de mejora en calidad — Curauma (CL)**
- *Evidencia:* Alta oferta vs. pares (CL/Non Wealthy) — Lead Pen: 31.8%, Perfect Orders: 81.8% (umbral peers: 82.5%). Crecimiento órdenes (4w): +12.6% sobre base de 198 órdenes.
- *Por qué importa:* Esta zona tiene buena oferta y demanda creciente, pero calidad por debajo de sus pares. Mejorar Perfect Orders aquí puede amplificar el crecimiento.
- *Recomendación:* Activar plan de calidad en Curauma: revisar operaciones y datos de la zona.

**🟠 5. Oportunidad de mejora en calidad — ZAC Tres Cruces (MX)**
- *Evidencia:* Alta oferta vs. pares (MX/Non Wealthy) — Lead Pen: 80.8%, Perfect Orders: 86.7% (umbral peers: 88.3%). Crecimiento órdenes (4w): +12.4% sobre base de 477 órdenes.
- *Por qué importa:* Esta zona tiene buena oferta y demanda creciente, pero calidad por debajo de sus pares. Mejorar Perfect Orders aquí puede amplificar el crecimiento.
- *Recomendación:* Activar plan de calidad en ZAC Tres Cruces: revisar operaciones y datos de la zona.

**🟠 6. Oportunidad de mejora en calidad — Envigado (CO)**
- *Evidencia:* Alta oferta vs. pares (CO/Non Wealthy) — Lead Pen: 43.0%, Perfect Orders: 85.5% (umbral peers: 87.7%). Crecimiento órdenes (4w): +12.3% sobre base de 43,804 órdenes.
- *Por qué importa:* Esta zona tiene buena oferta y demanda creciente, pero calidad por debajo de sus pares. Mejorar Perfect Orders aquí puede amplificar el crecimiento.
- *Recomendación:* Activar plan de calidad en Envigado: revisar operaciones y datos de la zona.

**🟠 7. Oportunidad de mejora en calidad — Troncal (CO)**
- *Evidencia:* Alta oferta vs. pares (CO/Non Wealthy) — Lead Pen: 31.7%, Perfect Orders: 87.3% (umbral peers: 87.7%). Crecimiento órdenes (4w): +10.7% sobre base de 6,087 órdenes.
- *Por qué importa:* Esta zona tiene buena oferta y demanda creciente, pero calidad por debajo de sus pares. Mejorar Perfect Orders aquí puede amplificar el crecimiento.
- *Recomendación:* Activar plan de calidad en Troncal: revisar operaciones y datos de la zona.

**🟠 8. Oportunidad de mejora en calidad — Poblado_guayabal (CO)**
- *Evidencia:* Alta oferta vs. pares (CO/Wealthy) — Lead Pen: 47.3%, Perfect Orders: 87.4% (umbral peers: 89.6%). Crecimiento órdenes (4w): +10.3% sobre base de 106,785 órdenes.
- *Por qué importa:* Esta zona tiene buena oferta y demanda creciente, pero calidad por debajo de sus pares. Mejorar Perfect Orders aquí puede amplificar el crecimiento.
- *Recomendación:* Activar plan de calidad en Poblado_guayabal: revisar operaciones y datos de la zona.

---

## Alertas de Calidad de Datos

**🟠 1. Valor fuera de rango: Lead Penetration = 2.000 en MG - BHZ - Sul (BR)**
- *Evidencia:* Lead Penetration reporta 2.000 en MG - BHZ - Sul. Rango esperado: [0, 2.0].
- *Por qué importa:* Valores fuera de rango pueden distorsionar benchmarks, correlaciones y rankings.
- *Recomendación:* Validar fuente de datos para MG - BHZ - Sul — Lead Penetration. Excluir de análisis comparativos hasta confirmar.

**🔴 2. Valor fuera de rango: Lead Penetration = 35.900 en Orquideas (EC)**
- *Evidencia:* Lead Penetration reporta 35.900 en Orquideas. Rango esperado: [0, 2.0].
- *Por qué importa:* Valores fuera de rango pueden distorsionar benchmarks, correlaciones y rankings.
- *Recomendación:* Validar fuente de datos para Orquideas — Lead Penetration. Excluir de análisis comparativos hasta confirmar.

**🔴 3. Valor fuera de rango: Lead Penetration = 13.600 en Chaullabamba (EC)**
- *Evidencia:* Lead Penetration reporta 13.600 en Chaullabamba. Rango esperado: [0, 2.0].
- *Por qué importa:* Valores fuera de rango pueden distorsionar benchmarks, correlaciones y rankings.
- *Recomendación:* Validar fuente de datos para Chaullabamba — Lead Penetration. Excluir de análisis comparativos hasta confirmar.

**🟠 4. Valor fuera de rango: Lead Penetration = 3.000 en Varzea Paulista (BR)**
- *Evidencia:* Lead Penetration reporta 3.000 en Varzea Paulista. Rango esperado: [0, 2.0].
- *Por qué importa:* Valores fuera de rango pueden distorsionar benchmarks, correlaciones y rankings.
- *Recomendación:* Validar fuente de datos para Varzea Paulista — Lead Penetration. Excluir de análisis comparativos hasta confirmar.

**🔴 5. Valor fuera de rango: Lead Penetration = 141.300 en Antiguo Aeropuerto (EC)**
- *Evidencia:* Lead Penetration reporta 141.300 en Antiguo Aeropuerto. Rango esperado: [0, 2.0].
- *Por qué importa:* Valores fuera de rango pueden distorsionar benchmarks, correlaciones y rankings.
- *Recomendación:* Validar fuente de datos para Antiguo Aeropuerto — Lead Penetration. Excluir de análisis comparativos hasta confirmar.

**🔴 6. Valor fuera de rango: Lead Penetration = 21.600 en Centro Lima Red (PE)**
- *Evidencia:* Lead Penetration reporta 21.600 en Centro Lima Red. Rango esperado: [0, 2.0].
- *Por qué importa:* Valores fuera de rango pueden distorsionar benchmarks, correlaciones y rankings.
- *Recomendación:* Validar fuente de datos para Centro Lima Red — Lead Penetration. Excluir de análisis comparativos hasta confirmar.

**🔴 7. Valor fuera de rango: Lead Penetration = 34.800 en SAMARIA_2_PEI (CO)**
- *Evidencia:* Lead Penetration reporta 34.800 en SAMARIA_2_PEI. Rango esperado: [0, 2.0].
- *Por qué importa:* Valores fuera de rango pueden distorsionar benchmarks, correlaciones y rankings.
- *Recomendación:* Validar fuente de datos para SAMARIA_2_PEI — Lead Penetration. Excluir de análisis comparativos hasta confirmar.

**🟠 8. Valor fuera de rango: Lead Penetration = 2.500 en Eden del Valle (EC)**
- *Evidencia:* Lead Penetration reporta 2.500 en Eden del Valle. Rango esperado: [0, 2.0].
- *Por qué importa:* Valores fuera de rango pueden distorsionar benchmarks, correlaciones y rankings.
- *Recomendación:* Validar fuente de datos para Eden del Valle — Lead Penetration. Excluir de análisis comparativos hasta confirmar.

---

## Recomendaciones Finales

1. **Priorizar zonas de alta severidad** con deterioro consistente en métricas de calidad (Perfect Orders).
2. **Capitalizar las oportunidades identificadas** donde la oferta está lista pero la ejecución es subóptima.
3. **Investigar correlaciones** para diseñar intervenciones que impacten múltiples métricas simultáneamente.
4. **Monitorear semanalmente** las anomalías detectadas para validar si son eventos puntuales o tendencias.
5. **Replicar best practices** de zonas que superan a sus pares en métricas clave.

---
*Reporte generado automáticamente por el Sistema de Análisis Inteligente Rappi — 2026-03-23 03:27*