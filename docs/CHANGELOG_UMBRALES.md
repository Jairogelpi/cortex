# Historial de cambios en umbrales
## Registro de decisiones de calibración pre-OSF

| Fecha | Parámetro | Valor original | Valor nuevo | Justificación |
|-------|-----------|---------------|-------------|---------------|
| 5 abril 2026 | DELTA_CONSOLIDATE | 0.75 | 0.70 | Techo natural delta=0.73. Con 0.75 Mu nunca consolida en condiciones neutras. H5 no testeable. |
| — | DELTA_BACKTRACK | 0.65 | 0.65 | Sin cambio. Validado con datos reales. |
| — | SIM_THRESHOLD | 0.65 | 0.65 | Sin cambio. Del paper. |
| — | STOP_LOSS_PCT | 0.15 | 0.15 | Sin cambio. Del paper. |

## Por qué este es el momento correcto

Este cambio se aplica en la fase de construcción, ANTES del pre-registro
en OSF. Una vez pre-registrado, ningún umbral puede modificarse sin
invalidar el experimento. Cambiar ahora es metodológicamente correcto.

## Efecto en las hipótesis

- H5 pasa de casi no testeable a testeable con datos de E2
- H4, H7 no se ven afectadas
- El razonamiento completo está en PROPUESTA_AJUSTE_UMBRALES.md
