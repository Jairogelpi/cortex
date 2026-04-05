# Cortex V2
## A Reliable Agentic Architecture for 2026

[![Paper Trading](https://img.shields.io/badge/Alpaca-Paper%20Trading-green)](https://alpaca.markets)
[![OSF Pre-registration](https://img.shields.io/badge/OSF-Pre--registered-blue)](https://osf.io/wdkcx)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue)](LICENSE)
[![Integration Tests](https://img.shields.io/badge/Tests-53%2F53%20PASS-brightgreen)](tests/test_integration.py)

Arquitectura agentiva de 10 capas para paper trading fiable.
**7 hipótesis falsables · 7 escenarios de fallo · Pre-registro OSF: https://osf.io/wdkcx**

---

## Estado del proyecto

| Fase | Capa | Estado | Resultado validado (5 abril 2026) |
|------|------|--------|-----------------------------------|
| 0 | Entorno + conexiones | ✅ | Alpaca $100K activo |
| 1 | Φ Factorizador de estado | ✅ | Ortogonalidad OK, var=0.2583 |
| 2 | Κ Critic externo (δ) | ✅ | δ=0.5961, HOLD_CASH |
| 3 | Ω Motor de hipótesis | ✅ | Lorenz Sim=0.9343, CASH |
| 4 | Λ Validación anti-sesgo | ✅ | Sim_adj=0.7922, CONFIRMED, FRED OK |
| 5 | Μ Memoria selectiva | ✅ | Rechazado correcto (δ<0.70) |
| 6 | Σ Orquestador | ✅ | HOLD, monitor_regime, 0.000s |
| 7 | Ρ Fiabilidad | ✅ | Stop-loss OK + activado en -16% |
| 8 | Τ Governance | ✅ | HOLD_NO_ACTION + bloqueo en real |
| 9 | Ο Observabilidad | ✅ | HEARTBEAT en logs/ + GitHub Actions |
| — | Test integración | ✅ | **53/53 checks pasados** |

---

## Pre-registro OSF

**https://osf.io/wdkcx** — sellado el 5 de abril de 2026

Los 7 parámetros y 7 hipótesis son inmutables desde este momento.
Cualquier resultado de E1-E5 que contradiga H1-H7 se publica completo.

---

## Resultado del día (5 abril 2026)

```
VIX: 23.87 | SPY: $655.83 | Momentum: -4.02% | Régimen: INDETERMINATE
δ: 0.5961 | Isomorfo: lorenz_attractor (Sim=0.9343)
Lambda: CONFIRMED (Sim_adj=0.7922) | FRED: T10Y2Y=0.51
Acción: HOLD — 100% cash
```

---

## Pipeline

```
INPUT → Φ → Κ → Ω → Λ → Μ → Σ → Ρ → Τ → Ο → ACTION
```

---

## Setup

```cmd
cd cortex_v2
call venv\Scripts\activate.bat
python -m cortex.pipeline
```

---

## Tests

```cmd
test_integracion.bat          # 53 checks — invariantes del paper
test_pipeline_completo.bat    # pipeline completo con datos reales
test_phi.bat / test_kappa.bat / test_omega.bat
test_lambda.bat / test_mu.bat
test_sigma.bat / test_rho.bat / test_tau.bat / test_omicron.bat
```

---

## Parámetros pre-registrados (inmutables)

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| DELTA_BACKTRACK | 0.65 | Límite inferior aceptable |
| DELTA_CONSOLIDATE | 0.70 | Techo natural=0.73, ajustado pre-OSF |
| SIM_THRESHOLD | 0.65 | Umbral activación isomorfos |
| STOP_LOSS_PCT | 0.15 | Stop-loss absoluto |

---

## Hipótesis falsables (H1–H7)

Ver pre-registro completo: **https://osf.io/wdkcx**

| H | Afirmación | Falsificación |
|---|-----------|---------------|
| H1 | Tokens_Cortex ≤ 0.45× baseline | Tokens_Cortex > 0.45× |
| H2 | F1_isomorfos ≥ F1_baseline + 0.20 | F1 < baseline + 0.20 |
| H3 | TPR_abstención ≥ 0.90 | TPR < 0.90 |
| H4 | Sharpe ≥ 0.90, MDD ≤ 50%×SPY | Sharpe < 0.90 o MDD > 50% |
| H5 | δ_inicial_Mu ≥ 0.71 vs 0.65 sin Mu | Sin diferencia |
| H6 | Lambda CONTRADICTED ≥ 85% casos incorrectos | <85% detección |
| H7 | Uptime ≥ 0.95, sin crash no gestionado | Crash o loop >$50 |

---

## Modelos por capa

| Capa | Modelo | Coste relativo |
|------|--------|----------------|
| Φ | claude-sonnet-4-6 (temp=0.1) | 1× |
| Κ | claude-haiku-4-5 | 0.1× |
| Ω | claude-opus-4-6 | 5× (1 llamada/régimen) |
| Λ | claude-sonnet-4-6 (temp=0.0) | 1× |

---

## Estructura

```
cortex_v2/
├── cortex/
│   ├── config.py              # umbrales pre-registrados
│   ├── market_data.py         # Alpaca + Yahoo Finance + FRED
│   ├── pipeline.py            # 10 capas en secuencia
│   └── layers/
│       ├── phi.py             # Φ — factorizador
│       ├── kappa.py           # Κ — critic externo
│       ├── omega.py           # Ω — motor hipótesis
│       ├── lambda_.py         # Λ — validación anti-sesgo
│       ├── mu.py              # Μ — memoria selectiva
│       ├── sigma.py           # Σ — orquestador
│       ├── rho.py             # Ρ — fiabilidad
│       ├── tau.py             # Τ — governance
│       └── omicron.py         # Ο — observabilidad
├── tests/
│   └── test_integration.py    # 53 checks
├── docs/
│   ├── PRE_REGISTRO_OSF.md    # parámetros + hipótesis completas
│   ├── DOCUMENTACION_MAESTRA.md
│   └── FASE_1_CAPA_PHI.md ... FASE_9_CAPA_OMICRON.md
├── logs/
│   ├── cortex_20260405.jsonl  # telemetría machine-readable
│   └── cortex_20260405.md     # diario para GitHub
└── .github/workflows/
    └── heartbeat.yml          # pipeline diario 09:00 UTC L-V
```

---

## Referencias

- Lee et al. (Nature Communications 2025) — fundamento Φ
- Zhou et al. (Nature Neuroscience 2025) — fundamento Κ
- Bellmund et al. (Nature Neuroscience 2025) — fundamento Ω
- Badre (2025) — fundamento Σ
- PHANTOM (NeurIPS 2025) — riesgo confabulación Lambda
- CMU + AI2 (febrero 2026) — seguridad agentes multi-turno

---

## Licencia

MIT — ver `LICENSE`

## Pre-registro

OSF: https://osf.io/wdkcx | GitHub: https://github.com/Jairogelpi/cortex
