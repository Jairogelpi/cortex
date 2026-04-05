# Fase 9 — Capa Ο (Omicron): Observabilidad Completa

**Cortex V2 · Documentación técnica y científica**
**Estado: COMPLETA y VALIDADA con datos reales**
**Fecha de validación: 5 abril 2026**

---

## 1. Qué es Omicron y por qué es la última capa

### El principio del paper

La Sección 2.2 especifica:

> *"Metacognición: el sistema monitoriza su propio funcionamiento.
> Telemetría: δ, régimen, tokens, backtrack events publicados en
> GitHub cada día. El sistema es auditable en tiempo real."*

Sin observabilidad, Cortex V2 sería una caja negra. Nadie podría
verificar que las hipótesis H1-H7 se están midiendo correctamente.
Nadie podría detectar fallos antes de que sean costosos. Y el
pre-registro OSF no tendría valor si los resultados no son públicos.

Omicron cierra ese gap. Es la capa que convierte a Cortex V2 en
un sistema científicamente verificable.

### Por qué es la última capa

Omicron recibe el output de todas las capas anteriores y los
registra de forma permanente. No puede ejecutarse antes de que
las otras capas hayan producido sus resultados. Su posición
al final del pipeline es por diseño — registra el estado final
del sistema tras todas las decisiones.

---

## 2. Los dos formatos de log

### Formato 1: JSONL (telemetría de máquina)

`logs/cortex_YYYYMMDD.jsonl` — una línea JSON por evento.

```json
{
  "event_type": "HEARTBEAT",
  "timestamp": "2026-04-05T17:20:46.197441",
  "session_id": "session_20260405_172007",
  "delta": 0.5966,
  "regime": "INDETERMINATE",
  "signal": "CASH",
  "lambda_verdict": "CONFIRMED",
  "lambda_sim": 0.8445,
  "sigma_decision": "HOLD",
  "tau_approved": true,
  "rho_healthy": true,
  "portfolio_value": 100000.0,
  "notes": "Pipeline completo..."
}
```

Útil para: análisis programático, cálculo de métricas H1-H7,
detección automática de anomalías por GitHub Actions.

### Formato 2: Markdown (diario legible)

`logs/cortex_YYYYMMDD.md` — tabla legible por humanos.

```markdown
| Timestamp | Evento | Regimen | Delta | Senal | Lambda | Sigma | Tau | Rho | Portfolio |
|-----------|--------|---------|-------|-------|--------|-------|-----|-----|----------|
| 2026-04-05T17:20:46 | HEARTBEAT | INDETERMINATE | δ=0.5966 | CASH | Λ=CONFIRMED(0.845) | Σ=HOLD | ✓ | ✓ | $100,000 |
```

Útil para: revisión humana diaria, publicación en GitHub,
evidencia para el pre-registro OSF.

---

## 3. Los tipos de eventos registrados

| Evento | Cuándo se genera | Impacto |
|--------|-----------------|---------|
| HEARTBEAT | Cada ejecución del pipeline | Normal |
| BACKTRACK | Cuando Kappa activa backtrack | ALERTA |
| STOP_LOSS | Cuando Rho activa stop-loss | CRÍTICO |
| LAMBDA_CONTRADICTION | Cuando Lambda contradice a Omega | ALERTA |

Los eventos BACKTRACK, STOP_LOSS y LAMBDA_CONTRADICTION activan
`logger.critical()` — aparecen en rojo en los logs y generan
alertas en GitHub Actions.

---

## 4. La condición de confianza del paper

La Sección 5 especifica:

> *"Sistema observable en tiempo real. Señal de alarma: sistema
> ciego a sus propios fallos."*

Omicron implementa esto con dos verificaciones:
1. Si el log JSONL no se actualiza en > 4 horas durante E2,
   GitHub Actions falla el job y envía notificación
2. Si `rho_healthy=False` aparece en el log, el sistema está
   en estado de alerta y requiere intervención humana

---

## 5. Resultado de validación real (5 abril 2026)

### Log JSONL real generado hoy

```json
{
  "event_type": "HEARTBEAT",
  "timestamp": "2026-04-05T17:20:46.197441",
  "session_id": "session_20260405_172007",
  "delta": 0.5966,
  "regime": "INDETERMINATE",
  "signal": "CASH",
  "lambda_verdict": "CONFIRMED",
  "lambda_sim": 0.8445,
  "sigma_decision": "HOLD",
  "tau_approved": true,
  "rho_healthy": true,
  "portfolio_value": 100000.0
}
```

### Log Markdown real generado hoy

```
| 2026-04-05T17:20:46 | HEARTBEAT | INDETERMINATE | δ=0.5966 |
  CASH | Λ=CONFIRMED(0.845) | Σ=HOLD | ✓ | ✓ | $100,000 |
```

**Este es el primer registro del diario de Cortex V2.** En E2,
este archivo crecerá con una línea por cada ejecución del pipeline
(una al día mediante GitHub Actions), formando el historial completo
de 30 días que el paper requiere para H4 y H7.

---

## 6. Integración con GitHub Actions

El workflow `heartbeat.yml` ejecuta el pipeline cada día a las
09:00 UTC y hace commit automático del log actualizado en el
repositorio. Cualquier persona puede verificar el historial
completo en https://github.com/Jairogelpi/cortex/tree/main/logs

Esta publicación diaria es la implementación del requisito de
transparencia del paper (Sección 5):
> *"Resultados diarios en GitHub. Reproducible por cualquier
> investigador."*

---

## 7. Métricas acumuladas disponibles

`get_session_summary()` devuelve:

```python
{
  "total_events": N,
  "delta_mean": float,      # delta medio de la sesión
  "delta_min": float,       # peor delta visto
  "delta_max": float,       # mejor delta visto
  "backtracks": int,        # número de backtracks (H7)
  "regimes_seen": list,     # regímenes detectados
  "signals_seen": list,     # señales generadas
  "lambda_verdicts": list,  # veredictos de Lambda
}
```

En E2, estas métricas acumuladas durante 30 días son la evidencia
empírica para falsificar o confirmar H4, H5 y H7.

---

## 8. Referencias del paper

- **Sección 2.2:** "Metacognición. Telemetría: δ, régimen, tokens,
  backtrack events publicados en GitHub cada día."

- **Sección 5:** Condición de confianza — sistema observable en
  tiempo real. Señal de alarma: sistema ciego a sus fallos.

- **Sección 3, H7:** GitHub Actions monitoriza Rho y Tau 24/7.

- **Pre-registro OSF:** Los logs de Omicron son la evidencia
  pública que respalda el pre-registro.
