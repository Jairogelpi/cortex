# E3 — Evaluación ciega de isomorfos de mercado
## Cortex V2 | Evaluador externo
### Pre-registro OSF: https://osf.io/wdkcx

---

## INSTRUCCIONES

Para cada día de mercado, identifica cuál de los 5 estados físicos
describe mejor el comportamiento del mercado en ese momento.
**Usa solo los datos de la tabla** — no busques información adicional.
**No uses el retorno futuro** — evalúa el estado presente del mercado.

### Los 5 isomorfos físicos:

| Código | Estado del mercado |
|--------|--------------------|
| **GAS_EXP** | Bull run sostenido: tendencia alcista clara, VIX < 18, momentum positivo fuerte, mercado 'libre' |
| **COMP_GAS** | Acumulación pre-rally: mercado lateral-alcista, VIX moderado-alto, tensión acumulada esperando ruptura |
| **PHASE** | Transición de régimen: alta volatilidad, VIX escalando, cambio estructural en curso, ruptura de tendencia |
| **OVER_DAMP** | Amortiguamiento lento: recuperación gradual sin impulso, VIX bajando lentamente, regreso al equilibrio |
| **LORENZ** | Caos determinista: trayectorias impredecibles, momentum negativo, VIX elevado sin resolución clara |

### Escala de confianza:
- **1** = muy inseguro (podría ser otro isomorfo)
- **2** = algo inseguro
- **3** = bastante seguro
- **4** = muy seguro (señal inequívoca)

---

## Los 50 pares de evaluación

| # | Fecha | SPY ($) | VIX | Mom.21d | Vol.real | Drawdown | Régimen detectado | Dificultad | Tu isomorfo | Confianza |
|---|-------|---------|-----|---------|----------|---------|-------------------|------------|-------------|-----------|
|  1 | 2025-10-02 | 665 | 16.6 | +4.2% | 6.3% | 0.0% | R1_EXPANSION | Fácil | | |
|  2 | 2025-10-03 | 665 | 16.6 | +3.4% | 5.9% | -0.0% | R1_EXPANSION | Fácil | | |
|  3 | 2025-10-06 | 668 | 16.4 | +4.0% | 5.7% | 0.0% | R1_EXPANSION | Media | | |
|  4 | 2025-10-09 | 667 | 16.4 | +3.2% | 6.4% | -0.3% | R1_EXPANSION | Fácil | | |
|  5 | 2025-10-13 | 659 | 19.0 | +1.1% | 12.6% | -1.5% | R1_EXPANSION | Media | | |
|  6 | 2025-10-15 | 661 | 20.6 | +1.1% | 12.6% | -1.2% | R2_ACCUMULATION | Difícil | | |
|  7 | 2025-10-16 | 657 | 25.3 | +0.5% | 12.8% | -1.9% | R2_ACCUMULATION | Media | | |
|  8 | 2025-10-17 | 661 | 20.8 | +0.6% | 12.8% | -1.3% | R2_ACCUMULATION | Difícil | | |
|  9 | 2025-10-24 | 673 | 16.4 | +2.9% | 13.3% | 0.0% | R1_EXPANSION | Media | | |
| 10 | 2025-10-29 | 684 | 16.9 | +3.2% | 13.7% | 0.0% | R1_EXPANSION | Fácil | | |
| 11 | 2025-11-06 | 667 | 19.5 | -0.4% | 15.3% | -2.5% | INDETERMINATE | Difícil | | |
| 12 | 2025-11-07 | 667 | 19.1 | -0.0% | 15.3% | -2.4% | INDETERMINATE | Difícil | | |
| 13 | 2025-11-10 | 678 | 17.6 | +4.3% | 12.7% | -0.9% | R1_EXPANSION | Fácil | | |
| 14 | 2025-11-12 | 680 | 17.5 | +3.2% | 11.7% | -0.6% | R1_EXPANSION | Fácil | | |
| 15 | 2025-11-17 | 662 | 22.4 | +0.2% | 13.3% | -3.2% | R2_ACCUMULATION | Media | | |
| 16 | 2025-11-18 | 656 | 24.7 | -1.7% | 13.0% | -4.0% | R2_ACCUMULATION | Difícil | | |
| 17 | 2025-11-19 | 659 | 23.7 | -1.3% | 13.1% | -3.6% | R2_ACCUMULATION | Difícil | | |
| 18 | 2025-11-20 | 649 | 26.4 | -2.3% | 14.0% | -5.1% | INDETERMINATE | Media | | |
| 19 | 2025-11-21 | 655 | 23.4 | -1.9% | 14.3% | -4.1% | R2_ACCUMULATION | Media | | |
| 20 | 2025-11-28 | 680 | 16.4 | -0.6% | 15.1% | -0.6% | INDETERMINATE | Difícil | | |
| 21 | 2025-12-02 | 678 | 16.6 | -0.1% | 14.7% | -0.8% | INDETERMINATE | Difícil | | |
| 22 | 2025-12-03 | 680 | 16.1 | +0.1% | 14.7% | -0.5% | R1_EXPANSION | Difícil | | |
| 23 | 2025-12-12 | 678 | 15.7 | -0.2% | 13.2% | -1.1% | INDETERMINATE | Difícil | | |
| 24 | 2025-12-19 | 679 | 14.9 | +3.0% | 12.1% | -0.9% | R1_EXPANSION | Media | | |
| 25 | 2025-12-22 | 683 | 14.1 | +5.3% | 10.5% | -0.3% | R1_EXPANSION | Fácil | | |
| 26 | 2025-12-23 | 686 | 14.0 | +4.7% | 10.2% | 0.0% | R1_EXPANSION | Fácil | | |
| 27 | 2026-02-04 | 684 | 18.6 | -0.2% | 10.5% | -1.3% | INDETERMINATE | Media | | |
| 28 | 2026-02-05 | 676 | 21.8 | -2.0% | 11.1% | -2.6% | INDETERMINATE | Difícil | | |
| 29 | 2026-02-09 | 692 | 17.4 | +0.6% | 13.2% | -0.2% | R1_EXPANSION | Difícil | | |
| 30 | 2026-02-10 | 690 | 17.8 | -0.3% | 13.0% | -0.5% | INDETERMINATE | Media | | |
| 31 | 2026-02-18 | 684 | 19.6 | -0.8% | 14.1% | -1.3% | INDETERMINATE | Difícil | | |
| 32 | 2026-02-24 | 685 | 19.6 | -0.3% | 12.4% | -1.2% | INDETERMINATE | Difícil | | |
| 33 | 2026-02-26 | 687 | 18.6 | -0.9% | 12.7% | -0.9% | INDETERMINATE | Difícil | | |
| 34 | 2026-03-03 | 678 | 23.6 | -1.7% | 13.0% | -2.2% | R2_ACCUMULATION | Media | | |
| 35 | 2026-03-05 | 679 | 23.8 | -1.2% | 13.0% | -2.0% | R2_ACCUMULATION | Difícil | | |
| 36 | 2026-03-06 | 671 | 29.5 | -2.0% | 13.6% | -3.3% | R3_TRANSITION | Media | | |
| 37 | 2026-03-09 | 676 | 25.5 | +0.1% | 13.3% | -2.5% | R2_ACCUMULATION | Media | | |
| 38 | 2026-03-10 | 675 | 24.9 | -1.9% | 11.4% | -2.6% | R2_ACCUMULATION | Difícil | | |
| 39 | 2026-03-12 | 664 | 27.3 | -3.8% | 12.2% | -4.2% | INDETERMINATE | Fácil | | |
| 40 | 2026-03-13 | 660 | 27.2 | -4.3% | 12.3% | -4.8% | INDETERMINATE | Fácil | | |
| 41 | 2026-03-16 | 667 | 23.5 | -1.8% | 11.9% | -3.8% | R2_ACCUMULATION | Difícil | | |
| 42 | 2026-03-17 | 669 | 22.4 | -1.6% | 12.0% | -3.5% | R2_ACCUMULATION | Difícil | | |
| 43 | 2026-03-18 | 660 | 25.1 | -3.1% | 12.8% | -4.9% | INDETERMINATE | Fácil | | |
| 44 | 2026-03-20 | 649 | 26.8 | -5.0% | 13.3% | -6.5% | INDETERMINATE | Fácil | | |
| 45 | 2026-03-23 | 655 | 26.1 | -4.7% | 13.7% | -5.5% | INDETERMINATE | Fácil | | |
| 46 | 2026-03-24 | 653 | 26.9 | -4.0% | 13.3% | -5.8% | INDETERMINATE | Difícil | | |
| 47 | 2026-03-25 | 657 | 25.3 | -4.2% | 13.2% | -5.3% | INDETERMINATE | Difícil | | |
| 48 | 2026-03-26 | 645 | 27.4 | -6.7% | 13.7% | -7.0% | INDETERMINATE | Fácil | | |
| 49 | 2026-03-27 | 634 | 31.1 | -7.8% | 14.5% | -8.6% | R3_TRANSITION | Fácil | | |
| 50 | 2026-03-30 | 632 | 30.6 | -7.6% | 14.5% | -8.9% | R3_TRANSITION | Fácil | | |

---

## Contexto adicional — pares difíciles

Para los pares de dificultad 'Difícil', información contextual adicional:

**Par 6 (2025-10-15):** Dia de transicion de regimen. Sistema: gas_expansion

**Par 8 (2025-10-17):** Dia de transicion de regimen. Sistema: gas_expansion

**Par 11 (2025-11-06):** Frontera gas/lorenz: mom=-0.4%, margen=0.005. Sistema: lorenz_attractor

**Par 12 (2025-11-07):** Frontera gas/lorenz: mom=-0.0%, margen=0.001. Sistema: lorenz_attractor

**Par 16 (2025-11-18):** overdamped_system tiene sim=0.630. Sistema elige lorenz_attractor. ¿Cual es el correcto?

**Par 17 (2025-11-19):** Dia de transicion de regimen. Sistema: lorenz_attractor

**Par 20 (2025-11-28):** Frontera gas/lorenz: mom=-0.6%, margen=0.024. Sistema: lorenz_attractor

**Par 21 (2025-12-02):** Frontera gas/lorenz: mom=-0.1%, margen=0.009. Sistema: lorenz_attractor

**Par 22 (2025-12-03):** Dia de transicion de regimen. Sistema: gas_expansion

**Par 23 (2025-12-12):** Frontera gas/lorenz: mom=-0.2%, margen=0.013. Sistema: lorenz_attractor

**Par 28 (2026-02-05):** Dia de transicion de regimen. Sistema: lorenz_attractor

**Par 29 (2026-02-09):** Dia de transicion de regimen. Sistema: gas_expansion

**Par 31 (2026-02-18):** Frontera gas/lorenz: mom=-0.8%, margen=0.022. Sistema: lorenz_attractor

**Par 32 (2026-02-24):** Frontera gas/lorenz: mom=-0.3%, margen=0.010. Sistema: lorenz_attractor

**Par 33 (2026-02-26):** Frontera gas/lorenz: mom=-0.9%, margen=0.026. Sistema: lorenz_attractor

**Par 35 (2026-03-05):** overdamped_system tiene sim=0.635. Sistema elige lorenz_attractor. ¿Cual es el correcto?

**Par 38 (2026-03-10):** Frontera gas/lorenz: mom=-1.9%, margen=0.021. Sistema: lorenz_attractor

**Par 41 (2026-03-16):** Frontera gas/lorenz: mom=-1.8%, margen=0.016. Sistema: lorenz_attractor

**Par 42 (2026-03-17):** overdamped_system tiene sim=0.622. Sistema elige lorenz_attractor. ¿Cual es el correcto?

**Par 46 (2026-03-24):** overdamped_system tiene sim=0.654. Sistema elige lorenz_attractor. ¿Cual es el correcto?

**Par 47 (2026-03-25):** overdamped_system tiene sim=0.655. Sistema elige lorenz_attractor. ¿Cual es el correcto?

---

## Limitaciones de este conjunto de datos

- El período analizado (oct 2025 – mar 2026) no incluyó crisis profunda (VIX > 35).
  No hay pares del estado R4_CONTRACTION.
- El estado OVER_DAMP (sistema amortiguado) es muy infrecuente en este período.
  Si crees que algún par corresponde a ese estado, indícalo aunque sea raro.
- Los pares 'Difícil' son deliberadamente ambiguos — no hay respuesta única garantizada.

---

*Generado el 5 de abril de 2026 con semilla aleatoria 42 (reproducible).*
*Evaluación ciega: el evaluador no conoce la clasificación del sistema.*