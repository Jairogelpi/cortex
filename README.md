# Cortex V2
## A Reliable Agentic Architecture for 2026

[![Paper Trading](https://img.shields.io/badge/Alpaca-Paper%20Trading-green)](https://alpaca.markets)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue)](LICENSE)
[![Pre-registro OSF](https://img.shields.io/badge/OSF-Pre--registro%20pendiente-orange)](https://osf.io)

Arquitectura agentiva de 10 capas para paper trading fiable.
**7 hipótesis falsables · 7 escenarios de fallo · Pre-registro OSF pendiente.**

---

## Estado del proyecto

| Fase | Capa | Estado | Resultado validado (5 abril 2026) |
|------|------|--------|-----------------------------------|
| 0 | Entorno + conexiones | ✅ | Alpaca $100K activo |
| 1 | Φ Factorizador de estado | ✅ | Ortogonalidad OK, var=0.2594 |
| 2 | Κ Critic externo (δ) | ✅ | δ=0.5966, HOLD_CASH |
| 3 | Ω Motor de hipótesis | ✅ | Lorenz Sim=0.9645, CASH |
| 4 | Λ Validación anti-sesgo | ✅ | Sim_adj=0.8445, CONFIRMED |
| 5 | Μ Memoria selectiva | ✅ | Rechazado correcto (δ<0.70) |
| 6 | Σ Orquestador | ✅ | HOLD, monitor_regime |
| 7 | Ρ Fiabilidad | ✅ | Stop-loss OK, checkpoint guardado |
| 8 | Τ Governance | ✅ | HOLD_NO_ACTION aprobado |
| 9 | Ο Observabilidad | ✅ | HEARTBEAT en logs/ |

---

## Resultado del día

```
Fecha:    5 abril 2026
VIX:      23.87 | SPY: $655.83 | Momentum: -4.02%
Régimen:  INDETERMINATE
Δ:        0.5966
Isomorfo: lorenz_attractor (Sim=0.9645)
Lambda:   CONFIRMED (Sim_adj=0.8445, 2 contradicciones detectadas)
Acción:   HOLD — 100% cash. No se ejecuta ninguna orden en Alpaca.
```

---

## Pipeline

```
INPUT → Φ → Κ → Ω → Λ → Μ → Σ → Ρ → Τ → Ο → ACTION
```

Cada capa opera sobre representaciones intermedias vía API.
Ninguna modifica el modelo LLM base.

---

## Setup rápido

```cmd
cd cortex_v2
setup.bat
```

Edita `.env` con tus claves (usa `.env.example` como plantilla).

```cmd
python -m cortex.pipeline
```

---

## Tests

```cmd
test_conexion.bat          # Alpaca + Yahoo Finance
test_phi.bat               # Capa Φ
test_kappa.bat             # Capa Κ (δ score)
test_omega.bat             # Capa Ω (isomorfos + Opus)
test_lambda.bat            # Capa Λ (validación anti-sesgo)
test_mu.bat                # Capa Μ (memoria selectiva)
test_pipeline_completo.bat # Pipeline completo 10 capas
```

---

## Modelos por capa (Plan-and-Execute heterogéneo)

| Capa | Modelo | Coste | Justificación |
|------|--------|-------|---------------|
| Φ | Claude Sonnet 4.6 | 1× | Comprensión semántica |
| Κ | Claude Haiku 4.5 | 0.1× | Fórmula determinista |
| Ω | Claude Opus 4.6 | 5× | Analogía cross-domain |
| Λ | Claude Sonnet 4.6 | 1× | Interpretación datos |
| Ξ | Claude Haiku 4.5 | 0.1× | Subagentes estructurados |
| Σ | Claude Sonnet 4.6 | 1× | Orquestación |

---

## Umbrales pre-registrados en OSF

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| DELTA_BACKTRACK | 0.65 | Límite inferior aceptable (8pts bajo techo natural) |
| DELTA_CONSOLIDATE | 0.70 | Ajustado 0.75→0.70 pre-OSF (techo natural=0.73) |
| SIM_THRESHOLD | 0.65 | Umbral activación isomorfos Omega |
| STOP_LOSS_PCT | 0.15 | Stop-loss absoluto 15% |

---

## Estructura

```
cortex_v2/
├── cortex/
│   ├── config.py           # Umbrales pre-registrables
│   ├── market_data.py      # Alpaca + Yahoo Finance
│   └── layers/
│       ├── phi.py          # Φ Factorizador
│       ├── kappa.py        # Κ Critic externo
│       ├── omega.py        # Ω Motor hipótesis
│       ├── lambda_.py      # Λ Validación
│       ├── mu.py           # Μ Memoria
│       ├── sigma.py        # Σ Orquestador
│       ├── rho.py          # Ρ Fiabilidad
│       ├── tau.py          # Τ Governance
│       └── omicron.py      # Ο Observabilidad
├── cortex/pipeline.py      # Pipeline completo
├── docs/                   # Documentación científica
│   ├── DOCUMENTACION_MAESTRA.md
│   ├── FASE_1_CAPA_PHI.md ... FASE_5_CAPA_MU.md
│   └── CHANGELOG_UMBRALES.md
└── .env.example            # Plantilla de claves
```

---

## Diario de trading (Omicron)

Los logs se publican diariamente. Ver `logs/` para el historial completo.

---

## Referencias

- Lee et al. (Nature Communications 2025) — fundamento Φ
- Zhou et al. (Nature Neuroscience 2025) — fundamento Κ
- Bellmund et al. (Nature Neuroscience 2025) — fundamento Ω
- PHANTOM (NeurIPS 2025) — riesgo confabulación
- CMU + AI2 (febrero 2026) — seguridad agentes multi-turno

---

## Licencia

MIT License — ver `LICENSE`

## Contacto

github.com/jairogelpi/cortex — issues para code, data, validation, review
