# Propuesta de ajuste de umbrales — Justificación científica
## Para revisión antes del pre-registro OSF

**Fecha:** 5 de abril de 2026
**Basado en:** análisis del techo natural del delta con datos reales

---

## El problema identificado

La fórmula delta tiene un techo natural con portfolio neutral:

```
δ_techo_neutral = 0.4 × RetornoNorm_neutral
                + 0.4 × (1 - DrawdownNorm_bajo)
                + 0.2 × RégimenConsistencia_máx

= 0.4 × 0.50   (portfolio igual a SPY)
+ 0.4 × 0.82   (drawdown contenido -5%)
+ 0.2 × 1.00   (régimen perfectamente consistente)

= 0.20 + 0.33 + 0.20 = 0.73
```

Con DELTA_CONSOLIDATE = 0.75, Mu solo consolidará cuando el portfolio
esté **batiendo activamente al benchmark SPY**. En condiciones normales
de mercado neutro, el sistema nunca consolidará.

Consecuencia directa: H5 no es testeable con los datos de E2 si Mu
raramente consolida. La hipótesis:
```
H5: δ_inicial con Mu ≥ 0.72 vs 0.65 sin Mu
```
...requiere que Mu tenga suficientes entradas consolidadas para
producir un δ_inicial mejorado. Si el umbral está por encima del
techo natural en condiciones neutras, H5 no puede falsificarse.

---

## La propuesta

**Cambiar DELTA_CONSOLIDATE de 0.75 a 0.70.**

DELTA_BACKTRACK permanece en 0.65 — está bien calibrado.

### Justificación

Con el umbral en 0.70:
- El sistema consolida cuando opera **3 puntos por encima** del techo
  natural en condiciones neutras (0.73 > 0.70 ✓)
- El sistema consolida cuando el régimen es claro y el portfolio
  funciona razonablemente — no solo cuando bate al mercado
- La zona entre DELTA_BACKTRACK y DELTA_CONSOLIDATE pasa de
  0.65–0.75 (banda de 10 puntos) a 0.65–0.70 (banda de 5 puntos)
- H5 es testeable: con δ≈0.73 en condiciones normales, Mu
  consolidará y podrá mejorar el δ_inicial de sesiones futuras

### Lo que NO cambia

- DELTA_BACKTRACK = 0.65 (correcto, bien calibrado por los datos)
- SIM_THRESHOLD = 0.65 (correcto, umbral de Omega del paper)
- STOP_LOSS_PCT = 0.15 (correcto, del paper)
- Los pesos 0.4/0.4/0.2 de la fórmula delta (correctos, del paper)

### Efecto sobre las hipótesis

| Hipótesis | Con 0.75 | Con 0.70 |
|-----------|----------|----------|
| H4 (Sharpe) | Sin cambio | Sin cambio |
| H5 (memoria) | Casi no testeable | Testeable |
| H7 (fiabilidad) | Sin cambio | Sin cambio |

---

## Cuándo aplicar este cambio

**ANTES del pre-registro en OSF, no después.**

Si el pre-registro ya está hecho con 0.75, el cambio a 0.70 no
puede hacerse sin invalidar el experimento. En ese caso, la
alternativa es documentar el problema como un gap conocido y
proponer el ajuste para Cortex V3.

Si el pre-registro aún no está hecho (estamos en fase de
construcción), este es el momento correcto para ajustar.

---

## Conclusión

El ajuste de 0.75 → 0.70 en DELTA_CONSOLIDATE es científicamente
justificado, mejora la testablidad de H5, y no afecta a las
hipótesis centrales del paper (H4, H7).

El ajuste de DELTA_BACKTRACK (0.65) no está justificado por
los datos actuales y no se propone.
