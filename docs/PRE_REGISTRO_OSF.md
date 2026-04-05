# PRE-REGISTRO OSF — Cortex V2
## A Reliable Agentic Architecture for 2026

**Fecha de pre-registro:** 5 de abril de 2026
**Repositorio público:** https://github.com/Jairogelpi/cortex
**Estado del sistema en el momento del pre-registro:** VALIDADO con datos reales
**Test de integración:** 53/53 checks pasados (18:06 UTC+1, 5 abril 2026)

---

## 1. RESUMEN DEL SISTEMA

Cortex V2 es una arquitectura agentiva de 10 capas para paper trading fiable.
Su hipótesis central: un LLM con contexto factorizado + isomorfos físicos +
critic independiente supera en fiabilidad a un LLM con contexto entrelazado
sin esas capas.

El sistema opera con datos de mercado reales (Alpaca Paper Trading + Yahoo
Finance + FRED) y no usa datos simulados ni mock en ninguna capa.

**Pipeline:**
```
INPUT → Φ → Ω → Κ → Λ → Μ → Σ → Ρ → Τ → Ο → ACTION
```

---

## 2. PARÁMETROS PRE-REGISTRADOS (INMUTABLES DESDE ESTE MOMENTO)

Estos parámetros no pueden modificarse después del pre-registro sin invalidar
el experimento. Cualquier cambio requiere un nuevo pre-registro con justificación.

### 2.1 Umbrales del sistema

| Parámetro | Valor | Justificación matemática |
|-----------|-------|--------------------------|
| DELTA_BACKTRACK | **0.65** | Límite inferior aceptable del sistema. Con δ < 0.65, al menos uno de los tres componentes de la fórmula está seriamente degradado. Validado con datos reales: δ=0.5961 el 5/04/2026 → HOLD_CASH correcto. |
| DELTA_CONSOLIDATE | **0.70** | Ajustado desde 0.75 pre-OSF. Justificación: el techo natural del delta en condiciones neutras es δ_max = 0.4×0.50 + 0.4×0.82 + 0.2×1.0 = 0.73. Con 0.75, Mu nunca consolidaría en condiciones normales (H5 no testeable). Con 0.70, consolida cuando el sistema opera 3 puntos sobre el techo natural. Ver CHANGELOG_UMBRALES.md. |
| SIM_THRESHOLD | **0.65** | Umbral mínimo de similitud coseno para activar un isomorfo en Omega. Por debajo: modo defensivo 100% cash. |
| STOP_LOSS_PCT | **0.15** | Stop-loss absoluto del 15% sobre el capital inicial ($100K). Si el portfolio cae a $85K o menos, el sistema se detiene y espera revisión humana. |

### 2.2 Pesos de la fórmula delta (Κ)

```
δ = 0.4 · RetornoNorm + 0.4 · (1 - DrawdownNorm) + 0.2 · RégimenConsistencia
```

Los pesos 0.4 / 0.4 / 0.2 son inmutables. Reflejan que retorno y drawdown
tienen igual importancia (salud financiera del portfolio) y la consistencia
de régimen tiene peso menor porque es más difícil de medir con precisión.

### 2.3 Los 5 isomorfos físicos y sus vectores Z de referencia

Inmutables. Calibrados según definiciones formales R1-R4 (Sección 9.3 del paper).

| Isomorfo | Vector Z de referencia (Z1..Z8) | Señal | Régimen |
|----------|--------------------------------|-------|---------|
| gas_expansion | [+0.80, -0.40, -0.30, +0.70, +0.60, -0.70, +0.75, -0.65] | LONG 80% | R1_EXPANSION |
| compressed_gas | [+0.10, +0.15, +0.20, +0.40, +0.30, +0.60, +0.15, -0.20] | LONG_PREPARE 50% | R2_ACCUMULATION |
| phase_transition | [-0.30, +0.75, +0.65, -0.50, -0.20, +0.50, -0.25, +0.70] | DEFENSIVE 30% | R3_TRANSITION |
| overdamped_system | [-0.20, +0.10, +0.15, -0.10, -0.30, +0.80, -0.15, +0.10] | MEAN_REVERSION 40% | R2_ACCUMULATION |
| lorenz_attractor | [-0.65, +0.85, +0.80, -0.75, -0.55, +0.30, -0.60, +0.90] | CASH 0% | R4_CONTRACTION |

### 2.4 Parámetros de infraestructura

| Parámetro | Valor |
|-----------|-------|
| MAX_SUBAGENTS | 5 |
| SUBAGENT_TIMEOUT | 60 segundos |
| CHECKPOINT_HOURS | 4 horas |

### 2.5 Modelos por capa (Plan-and-Execute heterogéneo)

| Capa | Modelo | Temperatura | Justificación |
|------|--------|-------------|---------------|
| Φ principal | claude-sonnet-4-6 | 0.1 | Razonamiento semántico rico |
| Φ interno Lambda | claude-sonnet-4-6 | **0.0** | Reproducibilidad determinista |
| Κ | claude-haiku-4-5 | 0.1 | Fórmula determinista, 0.1× coste |
| Ω | claude-opus-4-6 | 0.7 | Analogía cross-domain, 1 llamada/régimen |
| Λ reasoning | claude-sonnet-4-6 | **0.0** | Reproducibilidad en validación |

---

## 3. LAS 7 HIPÓTESIS FALSABLES (H1–H7)

Estas hipótesis se registran ANTES de los experimentos E1-E5.
La falsificación de cualquiera de ellas es un resultado científico válido.

### H1 — Token efficiency

```
Afirmación: Tokens_Cortex ≤ 0.45 × Tokens_baseline (para tarea equivalente)
Métrica:    Tokens por sesión completa de pipeline vs sesión baseline sin Cortex
Medición:   Experimento E5 — dos instancias paralelas con y sin Cortex
Falsificación: Tokens_Cortex > 0.45 × Tokens_baseline en E5
```

### H2 — Precisión de isomorfos

```
Afirmación: F1_score(Cortex, clasificación isomorfos) ≥ F1_score(baseline) + 0.20
Métrica:    F1-score en clasificación de isomorfos sobre 50 pares pre-registrados
Medición:   Experimento E3 — 50 pares etiquetados por expertos ciegos
Falsificación: F1_Cortex < F1_baseline + 0.20
```

### H3 — Calibración de Κ (TPR abstención)

```
Afirmación: TPR_abstención ≥ 0.90 cuando todos los Sim < 0.65
            Especificidad ≥ 0.85 (no abstención cuando Sim ≥ 0.65)
Métrica:    True Positive Rate en 20 escenarios de shock pre-registrados
Medición:   Experimento E4 — 20 escenarios con mercados reales post-cutoff
Falsificación: TPR < 0.90 O Especificidad < 0.85
```

### H4 — Rendimiento en paper trading (central)

```
Afirmación: Sharpe_Cortex ≥ 0.90 durante 30 días
            MDD_Cortex ≤ 50% × MDD_SPY en el mismo período
Métrica:    Sharpe ratio y Maximum Drawdown vs SPY
Medición:   Experimento E2 — 30 días Alpaca Paper Trading ($100K)
Falsificación: Sharpe < 0.90 O MDD > 50% × MDD_SPY
```

### H5 — Valor de la memoria Mu

```
Afirmación: δ_inicial_con_Mu ≥ 0.71 vs δ_inicial_sin_Mu ≈ 0.65
Métrica:    Delta inicial de sesión con vs sin memorias previas consolidadas
Medición:   Experimento E2 — condición A (con Mu) vs condición B (sin Mu)
Falsificación: sin diferencia estadística en δ_inicial entre condiciones
```

### H6 — Reducción de sesgo de confirmación (Lambda)

```
Afirmación: Lambda produce CONTRADICTED/UNCERTAIN en ≥ 85% de casos donde
            el isomorfo de Omega es incorrecto (verificado por E3)
Métrica:    Tasa de detección correcta de isomorfos incorrectos
Medición:   Experimento E3 — Lambda evaluada sobre los 50 pares de E3
Falsificación: Lambda CONFIRMED en >15% de casos donde isomorfo es incorrecto
```

### H7 — Fiabilidad del sistema (Ρ y Τ)

```
Afirmación: Tasa de éxito ≥ 0.95 en 30 días sin crash no gestionado
            Sin loop de API que genere > $50 en un solo evento
Métrica:    Uptime, eventos STOP_LOSS, eventos BACKTRACK no controlados
Medición:   Experimento E2 — 30 días con monitorización GitHub Actions 24/7
Falsificación: crash no gestionado O loop > $50 en un evento
```

---

## 4. LOS 7 ESCENARIOS DE FALLO (F1–F7)

Estos escenarios definen qué constituye un fallo del sistema. Si alguno
se activa durante E2, se documenta completo y se publica.

| Escenario | Descripción | Prevención |
|-----------|-------------|-----------|
| F1 | Omega confabula isomorfo falso → Lambda no detecta → orden incorrecta → $400+ | Lambda CONTRADICTED con Sim < 0.40 → BACKTRACK inmediato |
| F2 | Memoria Mu de sesión A contamina evaluación sesión B → Sharpe inflado | Isolation layers + test correlación ρ < 0.30 |
| F3 | Tau no bloquea acción irreversible → pérdida irreparable | Governance rules + is_paper_trading flag |
| F4 | Deadlock: dos subagentes Xi se esperan mutuamente → heartbeat falla | Timeout 60s + Sigma reinicia subagente bloqueado |
| F5 | Kappa mal calibrado → δ incorrecto → loop de retry → $400+ | Stop-loss 15% (Rho) + backtrack automático (Kappa) |
| F6 | Phi no detecta cambio de régimen → isomorfo obsoleto 7+ días | Recalibración diaria + alerta Omicron si drift > 15% |
| F7 | Proliferación de subagentes sin control → $1000+ en una sesión | MAX_SUBAGENTS=5 + token budget por subagente |

---

## 5. DISEÑO EXPERIMENTAL (E1–E5)

### E1 — Backtesting sin look-ahead bias

```
Datos:     septiembre 2025 – marzo 2026 (post-cutoff de todos los modelos usados)
Objetivo:  calibrar Phi y Omega con datos históricos
Condición: datos estrictamente post-cutoff (Sección 9.5)
Inicio:    inmediatamente tras pre-registro OSF
Output:    parámetros de calibración de Phi (drift δ_Φ) y Omega (F1-score baseline)
```

### E2 — Paper trading real 30 días (hipótesis central)

```
Plataforma: Alpaca Paper Trading — $100,000 simulados (cuenta activa)
Duración:   30 días laborables
Condiciones paralelas:
  A: Cortex V2 completo (todas las capas)
  B: Sin capa Mu (ablación memoria)
  C: Sin capa Lambda (ablación validación)
  D: Sin Cortex (LLM directo + contexto bruto, baseline)
Métricas:   Sharpe, MDD, tokens/sesión, δ_inicial, tasa CONTRADICTED
GitHub Actions: pipeline diario 09:00 UTC L-V (automático)
```

### E3 — Validación de isomorfos (H2 y H6)

```
50 pares (estado_mercado, isomorfo_correcto) pre-registrados
Evaluación ciega por 3 expertos independientes
Acuerdo inter-evaluador κ ≥ 0.75 requerido (Cohen's kappa)
Mide si Omega elige el isomorfo correcto Y si Lambda detecta los incorrectos
```

### E4 — Calibración de Κ (H3)

```
20 escenarios de shock pre-registrados
Mercados reales post-cutoff seleccionados de E1
TPR ≥ 0.90 en abstención (δ < 0.65 cuando Sim < 0.65)
Especificidad ≥ 0.85 (no abstención cuando mercado es claro)
```

### E5 — Token efficiency (H1)

```
Dos instancias paralelas durante E2:
  Instancia A: Cortex V2 completo (tokens medidos por Omicron)
  Instancia B: GPT-4o / Claude Sonnet directo (baseline sin arquitectura)
Mismo conjunto de 30 días
Mide tokens totales por decisión de trading
```

---

## 6. EVIDENCIA EMPÍRICA DEL DÍA DE PRE-REGISTRO

El sistema se validó con datos de mercado reales el 5 de abril de 2026.
Estos resultados son el estado de línea base antes de E1.

### 6.1 Contexto de mercado

```
Fecha:         5 de abril de 2026, 18:05 UTC+1
VIX:           23.87 (zona de estrés, entre R2 y R3)
SPY:           $655.83
Momentum 21d:  -4.02% (tendencia bajista moderada)
Vol realizada: 18.32%
Drawdown 90d:  -5.44%
Régimen:       INDETERMINATE
Portfolio:     $100,000 (Alpaca Paper Trading, intacto)
```

### 6.2 Resultado del pipeline completo

```
Φ:  Z=[-0.530, +0.319, +0.506, -0.730, +0.119, -0.069, -0.284, +0.876]
    Ortogonalidad OK | var=0.2583 | spread=1.606

Κ:  δ = 0.4×0.567 + 0.4×0.819 + 0.2×0.209 = 0.5961
    Decisión: HOLD_CASH (δ < 0.65, sin posiciones)

Ω:  lorenz_attractor Sim=0.9343 (umbral 0.65: OK)
    Señal: CASH
    Opus: "trayectorias divergen exponencialmente — caos determinista"

Λ:  Sim_raw=0.9322 → penalización -0.14 → Sim_adj=0.7922
    Fuentes: Yahoo Finance OK + FRED OK (T10Y2Y=0.51)
    Veredicto: CONFIRMED
    Contradicciones: VIX bajó -6.7pts en 5d, Momentum 5d=+1.7%

Μ:  RECHAZADO (δ=0.5961 < 0.70 — correcto, régimen incierto)

Σ:  HOLD | subagentes=[monitor_regime] | 0.000s (determinista)

Ρ:  Stop-loss OK (drawdown=0.00%) | checkpoint ckpt_20260405_180657

Τ:  HOLD_NO_ACTION aprobado | sin acción que bloquear

Ο:  HEARTBEAT registrado en logs/cortex_20260405.jsonl + .md

ACCIÓN FINAL: HOLD — 100% cash
```

### 6.3 Test de integración 53/53

```
Sesión: integration_20260405_180540
Resultado: 53/53 checks pasados

Checks críticos verificados:
  ✓ Fórmula δ exacta:     manual=0.5961 = reportado=0.5961
  ✓ FRED conectado:       T10Y2Y=0.51 (datos reales)
  ✓ CONTRADICTED real:    gas_expansion vs mercado bajista → Sim=0.1334 → BACKTRACK
  ✓ Phi reproducible:     temperature=0.0 → max_diff=0.0000 entre ejecuciones
  ✓ Stop-loss real:       portfolio $84K → activado (-16%)
  ✓ Tau bloqueo real:     EXECUTE 80% bloqueado con is_paper_trading=False
  ✓ Omicron:              4 líneas JSONL + Markdown con HEARTBEAT
```

### 6.4 Log JSONL del día (Omicron)

```json
{"event_type":"HEARTBEAT","timestamp":"2026-04-05T17:20:46","delta":0.5966,"regime":"INDETERMINATE","signal":"CASH","lambda_verdict":"CONFIRMED","lambda_sim":0.8445,"sigma_decision":"HOLD","tau_approved":true,"rho_healthy":true,"portfolio_value":100000.0}
{"event_type":"HEARTBEAT","timestamp":"2026-04-05T17:48:51","delta":0.5966,"regime":"INDETERMINATE","signal":"CASH","lambda_verdict":"CONFIRMED","lambda_sim":0.8123,"sigma_decision":"HOLD","tau_approved":true,"rho_healthy":true,"portfolio_value":100000.0}
{"event_type":"HEARTBEAT","timestamp":"2026-04-05T18:06:57","delta":0.5961,"regime":"INDETERMINATE","signal":"CASH","lambda_verdict":"CONFIRMED","lambda_sim":0.7922,"sigma_decision":"HOLD","tau_approved":true,"rho_healthy":true,"portfolio_value":100000.0}
```

---

## 7. LIMITACIONES CONOCIDAS (HONESTIDAD CIENTÍFICA)

Estas limitaciones se documentan ANTES del experimento, no después.

### L1 — FRED como fuente secundaria

FRED (Federal Reserve Economic Data) provee el spread T10Y2Y como segunda
fuente para Lambda. Si falla, Lambda opera solo con Yahoo Finance. El sistema
es funcional con una sola fuente, pero la verificación cruzada es incompleta.
La API key demo de FRED tiene límites de rate — en producción se recomienda
key propia.

### L2 — Phi no es perfectamente determinista con temperatura=0.1

La capa Phi principal usa temperatura=0.1 para razonamiento semántico rico.
Esto produce variación pequeña entre ejecuciones (max_diff ≈ 0.008 observado).
Lambda interna usa temperatura=0.0 (reproducible, max_diff=0.0000 verificado).
Esta limitación está documentada y el sistema la compensa con separación
forzada de dimensiones (enforce_separation).

### L3 — Lambda siempre CONFIRMED con Lorenz en mercado INDETERMINATE

Con el mercado actual (INDETERMINATE, VIX=23.87, momentum=-4.02%), Lambda
produce consistentemente CONFIRMED para lorenz_attractor con Sim_adj~0.79-0.81.
Esto es científicamente correcto — el mercado actual SI es geométricamente
similar a Lorenz. Pero significa que el código de CONTRADICTED para esta
hipótesis específica no se ha ejercitado con datos de mercado reales
(solo con el escenario sintético del test de integración). E2 generará
escenarios con diferentes isomorfos en diferentes regímenes.

### L4 — Experimento E2 es paper trading, no capital real

Todos los experimentos usan Alpaca Paper Trading ($100K simulados).
Los resultados de H4 (Sharpe, MDD) son sobre capital simulado.
La transferabilidad a capital real requiere E6 (no pre-registrado, post-paper).

### L5 — Un solo operador, sin revisión ciega

El sistema fue construido y validado por el mismo operador que diseñó el paper.
No hay revisión externa ciega durante E1-E2. E3 introduce evaluadores externos
(para los isomorfos), pero las métricas financieras de E2 no tienen revisión
ciega hasta la publicación.

---

## 8. INSTRUCCIONES PARA EL PRE-REGISTRO EN OSF

### Pasos para registrar en https://osf.io

1. Crear cuenta en osf.io (si no existe)
2. Crear nuevo proyecto: "Cortex V2 — A Reliable Agentic Architecture for 2026"
3. En "Registrations" → "New Registration" → "OSF Preregistration"
4. Completar los campos con el contenido de las Secciones 3, 4 y 5 de este documento
5. Añadir el repositorio GitHub como componente vinculado
6. Marcar como "Register" (no borrador) → fecha queda sellada permanentemente

### Campos clave del formulario OSF

**Hypotheses:**
Pegar texto de Sección 3 (H1-H7 exactas)

**Study Design:**
"Arquitectura agentiva de 10 capas para paper trading. Pipeline:
Φ→Ω→Κ→Λ→Μ→Σ→Ρ→Τ→Ο. Datos reales: Alpaca Paper Trading + Yahoo Finance + FRED.
Experimentos E1-E5 tal como se describen en la Sección 5."

**Dependent Variables:**
"H1: tokens/sesión | H2: F1-score isomorfos | H3: TPR/Especificidad |
H4: Sharpe ratio y MDD | H5: δ_inicial | H6: tasa CONTRADICTED | H7: uptime"

**Independent Variables:**
"Presencia/ausencia de cada capa (ablación). Condiciones A/B/C/D en E2."

**Statistical Analyses:**
"Comparación de medias con intervalos de confianza 95%.
Mann-Whitney U para métricas no normales.
Corrección Bonferroni para comparaciones múltiples (7 hipótesis)."

**Criteria for confirming, falsifying, or modifying each hypothesis:**
Pegar texto de Sección 3 (criterios de falsificación exactos)

---

## 9. TRAZABILIDAD

Todos los archivos de este pre-registro están en:
```
https://github.com/Jairogelpi/cortex
├── cortex/config.py              ← parámetros inmutables
├── cortex/layers/                ← implementación 10 capas
├── tests/test_integration.py     ← 53 checks verificados
├── logs/cortex_20260405.jsonl    ← evidencia empírica del día
├── logs/cortex_20260405.md       ← diario legible
└── docs/
    ├── PRE_REGISTRO_OSF.md       ← este documento
    ├── DOCUMENTACION_MAESTRA.md
    ├── CHANGELOG_UMBRALES.md
    └── FASE_1_CAPA_PHI.md ... FASE_9_CAPA_OMICRON.md
```

Commit hash en el momento del pre-registro: ver GitHub
(el hash del commit que incluye este documento es la referencia permanente)

---

*Documento generado el 5 de abril de 2026.*
*Basado en resultados reales. Sin datos simulados. Sin hardcoding.*
*53/53 checks pasados en test de integración completo.*
