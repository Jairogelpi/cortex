# Análisis de Resultados — Experimento E1
## Cortex V2 | Backtesting sin look-ahead bias

**Fecha:** 5 de abril de 2026
**OSF:** https://osf.io/wdkcx
**Datos:** Yahoo Finance, SPY + VIX, sept 2025–mar 2026
**Código:** experiments/e1_fast.py

---

## 1. Qué hizo E1 exactamente — y qué no hizo

### Qué hizo

E1 descargó datos reales de SPY y VIX desde Yahoo Finance para el periodo
septiembre 2025–marzo 2026. Para cada día de mercado, calculó:

1. Los indicadores de régimen (VIX, momentum 21d, vol realizada, drawdown 90d)
2. El vector Z de Phi **de forma determinista** — sin llamar al LLM
3. El delta de Kappa **de forma determinista** — sin llamar al LLM
4. El isomorfo de Omega por similitud coseno pura — sin llamar a Opus

### Qué NO hizo — limitaciones reales

**E1 no es el sistema completo.** Es una versión determinista del sistema, sin LLMs.
Esto tiene consecuencias concretas que hay que documentar antes de E2:

1. **Phi sin LLM produce vectores más comprimidos.** La varianza Z media en E1
   fue 0.1068, vs 0.25 en producción con LLM. Los vectores Z son correctos en
   dirección pero con menor dispersión. Esto afecta las similitudes de Omega.

2. **RetornoNorm está fijado en 0.5 para todos los días.** En producción, Kappa
   calcula el retorno real del portfolio vs SPY. En E1, el portfolio siempre
   vale $100K (neutro). Esto hace que el delta de E1 sea el delta de un sistema
   que nunca ha tomado posiciones — no refleja el delta real durante E2 cuando
   haya posiciones abiertas.

3. **Lambda no se ejecutó en E1.** Lambda valida cada hipótesis de Omega contra
   datos frescos. En E1, la hipótesis de Omega se acepta directamente sin
   verificación anti-sesgo. El sistema real en E2 usará Lambda.

4. **Mu, Sigma, Rho, Tau, Omicron no se ejecutaron.** E1 es solo las capas de
   percepción (Phi, Kappa, Omega), no el pipeline completo.

**En resumen: E1 es calibración, no evaluación.** Sus resultados son válidos
para entender la distribución de regímenes e isomorfos del período, pero no
para predecir el rendimiento de E2.

---

## 2. Resultados reales — sin interpretación optimista

### 123 días procesados (2025-10-02 a 2026-03-30)

Los primeros 22 días (sept–oct 2025) se descartaron por necesitar al menos
22 días de historia para calcular momentum 21d. Esto es correcto por diseño.

### Distribución de regímenes

| Régimen | Días | % | δ medio | δ std |
|---------|------|---|---------|-------|
| R1_EXPANSION | 68 | 55.3% | 0.7648 | 0.0119 |
| R2_ACCUMULATION | 26 | 21.1% | 0.7092 | 0.0161 |
| INDETERMINATE | 26 | 21.1% | 0.6210 | 0.0272 |
| R3_TRANSITION | 3 | 2.4% | 0.6218 | 0.0340 |
| R4_CONTRACTION | 0 | 0.0% | — | — |

**Observación crítica:** R4_CONTRACTION no apareció en ningún día del periodo.
Lorenz_attractor (el isomorfo de R4) apareció 42 veces, pero clasificado bajo
regímenes R2_ACCUMULATION e INDETERMINATE — no bajo R4. Esto indica una
inconsistencia entre la clasificación de régimen (basada en umbrales de VIX)
y la detección de isomorfos (basada en similitud coseno del vector Z).

El VIX nunca superó 35 simultáneamente con momentum < -5% y drawdown < -15%
en este período, por eso R4 nunca se activó. Pero el sistema detectó el
patrón geométrico de Lorenz (caos) en días con VIX 20-28 y momentum negativo
moderado. Esto es información útil para E3.

### Distribución de isomorfos

| Isomorfo | Días | % | Señal |
|----------|------|---|-------|
| gas_expansion | 76 | 61.8% | LONG |
| lorenz_attractor | 42 | 34.1% | CASH |
| compressed_gas | 3 | 2.4% | LONG_PREPARE |
| phase_transition | 2 | 1.6% | DEFENSIVE |
| **overdamped_system** | **0** | **0.0%** | MEAN_REVERSION |

**Problema real: overdamped_system nunca apareció.**

Este es el hallazgo más importante de E1 para el diseño del sistema.
overdamped_system tiene vector Z de referencia:
`[-0.20, +0.10, +0.15, -0.10, -0.30, +0.80, -0.15, +0.10]`

Su característica principal es Z6=+0.80 (reversión alta) y Z8=+0.10
(baja complejidad). En el periodo sept 2025–mar 2026, ningún día del mercado
produjo un vector Z geométricamente similar a ese patrón. El mercado estuvo
o en expansión (R1) o en deterioro progresivo — nunca en el patrón de
reversión lenta a la media que overdamped_system captura.

Consecuencia para H2: el sistema nunca genera señal MEAN_REVERSION.
En E3, cuando se evalúen los 50 pares de isomorfos, si algunos pares
corresponden a mercados de reversión lenta, el sistema fallará en clasificarlos.
Esto hundirá el F1 de H2.

---

## 3. F1 baseline — análisis sin sesgos

**Macro F1 baseline = 0.278. Objetivo H2 = F1 >= 0.478.**

Esto significa que Cortex V2 necesita mejorar el F1 en +0.20 sobre un baseline
que ya está midiendo algo concreto. Hay que entender exactamente qué mide ese F1
antes de celebrar o preocuparse.

### La métrica mide predicción de dirección del día siguiente

La lógica de E1 asigna:
- gas_expansion / compressed_gas → predicción "bullish" (retorno siguiente > +0.3%)
- phase_transition / lorenz_attractor → predicción "bearish" (retorno siguiente < -0.3%)
- overdamped_system → predicción "neutral" (retorno entre -0.3% y +0.3%)

### El resultado por clase

**Bullish (76 días predichos):**
- 27 aciertos, 52 fallos → precisión 0.34
- El sistema predijo LONG 76 días, pero solo 27 veces el mercado subió >0.3% al día siguiente
- Esto no es sorprendente — el momentum de 21 días no predice el retorno del día siguiente

**Bearish (42 días predichos):**
- 16 aciertos, 27 fallos → precisión 0.37
- El sistema predijo CASH (lorenz) 42 días, el mercado bajó >0.3% solo 16 veces

**Neutral (0 días predichos):**
- F1 = 0.0 — el sistema nunca predijo neutral
- Hubo 40 días neutrales reales que el sistema clasificó como bullish o bearish

### El problema de fondo

El F1 de E1 mide si el isomorfo de Omega predice la dirección del día siguiente.
Esta no es exactamente la tarea de Omega en el sistema. Omega no está diseñado
para predecir el día siguiente — está diseñado para identificar el régimen actual
y generar una señal de trading apropiada para ese régimen (que puede durar días
o semanas, no solo el día siguiente).

Usar el retorno del día siguiente como "etiqueta correcta" es una proxy débil.
Es la mejor proxy disponible en E1 sin datos de evaluación externos, pero hay
que documentar esta limitación explícitamente antes de E3.

**En E3, los 50 pares serán evaluados por expertos que asignan el isomorfo
correcto según el contexto completo del régimen, no según el retorno del día
siguiente.** El F1 de E3 medirá algo distinto — y probablemente más relevante —
que el F1 de E1.

---

## 4. Lo que sí funciona bien

### Los umbrales están bien calibrados

La separación entre regímenes en términos de delta es real:

```
R1_EXPANSION:    δ_medio = 0.7648 (std=0.0119) → por encima de 0.70 ✓
R2_ACCUMULATION: δ_medio = 0.7092 (std=0.0161) → zona operable     ✓
INDETERMINATE:   δ_medio = 0.6210 (std=0.0272) → por debajo de 0.65 ✓
R3_TRANSITION:   δ_medio = 0.6218 (std=0.0340) → por debajo de 0.65 ✓
```

La separación entre R1 y INDETERMINATE es de 0.1438 con std pequeños.
Esto significa que los umbrales no son arbitrarios: cuando el mercado está
en R1, el delta es consistentemente alto; cuando está en INDETERMINATE o R3,
el delta cae consistentemente por debajo del umbral de backtrack.

Esta es la validación empírica de los umbrales pre-registrados en OSF.
Esto sí es un resultado sólido.

### El sistema habría evitado el deterioro de marzo 2026

En los últimos 12 días de marzo (20–30 de marzo), el mercado entró en
deterioro progresivo: VIX 25-31, momentum -4% a -8%, delta 0.56-0.60.
El sistema habría estado en HOLD/CASH durante todo ese período.

```
2026-03-20  INDETERMINATE  VIX=26.8  mom=-4.99%  δ=0.5747  CASH
2026-03-23  INDETERMINATE  VIX=26.1  mom=-4.68%  δ=0.5877  CASH
2026-03-24  INDETERMINATE  VIX=27.0  mom=-4.02%  δ=0.5835  CASH
2026-03-26  INDETERMINATE  VIX=27.4  mom=-6.68%  δ=0.5680  CASH
2026-03-27  R3_TRANSITION  VIX=31.0  mom=-7.76%  δ=0.5998  CASH
2026-03-30  R3_TRANSITION  VIX=30.6  mom=-7.62%  δ=0.5958  CASH
```

El delta de hoy (5 abril 2026, δ=0.5961) es consistente con este contexto.
El mercado actual es la continuación del deterioro que empezó en marzo.

---

## 5. Problemas que hay que resolver antes de E2

### Problema 1: overdamped_system nunca activa — DEBE RESOLVERSE

El vector Z de referencia de overdamped_system no coincide con ningún patrón
del mercado real en 123 días. Hay dos posibles causas:

**Causa A:** El mercado en el periodo estudiado no tuvo periodos de reversión
lenta a la media — posible, dado que el periodo estuvo dominado por expansión
y luego deterioro.

**Causa B:** El vector Z de referencia está mal calibrado. Si Z6=+0.80 es
demasiado alto como condición de activación, el isomorfo nunca se activa
en mercados normales.

**Acción antes de E2:** Analizar los días en que el mercado real estuvo en
reversión lateral (VIX 18-22, momentum entre -1% y +1%, drawdown < -5%) y
verificar si el vector Z de esos días se parece a overdamped_system o no.
Si no se parece, recalibrar el vector Z de referencia.

### Problema 2: La métrica F1 de H2 necesita refinamiento

El F1 de E1 (0.278) usa el retorno del día siguiente como proxy del isomorfo
correcto. Esta es una métrica débil. Antes de E3, hay que:

1. Definir explícitamente qué constituye el "isomorfo correcto" para cada par
   de los 50 pares de E3
2. Asegurarse de que los 50 pares incluyan ejemplos de todos los isomorfos,
   incluyendo overdamped_system
3. Documentar en el pre-registro de E3 que el F1 de E1 usa una proxy diferente
   al criterio de E3

### Problema 3: E1 no evaluó Lambda, Mu, ni las capas de infraestructura

E1 evaluó solo la percepción (Phi, Kappa, Omega). E2 evaluará el sistema
completo incluyendo Lambda (validación anti-sesgo), Mu (memoria), Sigma,
Rho, Tau y Omicron. Los resultados de E2 no son comparables directamente
con E1 — son experimentos que miden cosas distintas.

---

## 6. Qué significa esto para el paper

### Lo que puedes afirmar con los datos de E1

1. "Los umbrales δ=0.65 y δ=0.70 producen separación estadísticamente coherente
   entre regímenes en 123 días de datos reales post-cutoff."

2. "El sistema identifica correctamente el deterioro de mercado: en los 12 días
   de marzo 2026 con VIX>25 y momentum<-4%, el delta cayó consistentemente
   por debajo de 0.60 y la señal fue CASH."

3. "El isomorfo gas_expansion dominó el período oct 2025–ene 2026 (bull run),
   y lorenz_attractor dominó el período feb–mar 2026 (deterioro)."

### Lo que NO puedes afirmar con los datos de E1

1. No puedes afirmar que el sistema habría generado Sharpe ≥ 0.90 durante E1.
   E1 no ejecutó órdenes, no calculó retornos reales, no usó Lambda.

2. No puedes afirmar que el F1 de H2 será ≥ 0.478 en E3 basándote en E1.
   El F1 de E1 mide una proxy diferente.

3. No puedes afirmar que overdamped_system funciona — nunca se activó.

---

## 7. Próximos pasos inmediatos

En orden de prioridad antes de E2:

1. **Analizar overdamped_system:** buscar en e1_results.csv los días con
   mercado lateral y verificar si el vector Z se aproxima al isomorfo.

2. **Iniciar E2:** el sistema ya corre con GitHub Actions a las 09:00 UTC.
   El primer día de E2 es el próximo día laborable. Los logs se publicarán
   automáticamente.

3. **Documentar la diferencia E1 fast vs E1 completo:** el paper debe explicar
   que E1_fast usa Phi/Kappa/Omega deterministas, no los modelos LLM reales.
   La calibración de E1 es válida para parámetros estructurales, no para
   métricas de rendimiento.

---

*Documento generado el 5 de abril de 2026.*
*Basado exclusivamente en datos reales de E1.*
*Sin interpretación optimista. Sin ocultar los problemas.*
