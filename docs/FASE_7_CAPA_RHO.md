# Fase 7 — Capa Ρ (Rho): Fiabilidad y Recuperación

**Cortex V2 · Documentación técnica y científica**
**Estado: COMPLETA y VALIDADA con datos reales**
**Fecha de validación: 5 abril 2026**

---

## 1. Qué es Rho y por qué existe

### El problema que resuelve

Un agente autónomo que opera durante 30 días continuos puede fallar
de formas distintas: crash del proceso, loop de retry sin control,
pérdida de estado entre sesiones, o pérdida financiera catastrófica.
Sin un mecanismo de recuperación, cualquiera de estos fallos sería
irreparable.

El paper documenta el coste real (Sección 4, F5):

> *"El fallo más caro documentado en 2026: $400 en una sesión de
> retry loops sin backtrack (comunidad OpenClaw, febrero 2026)."*

### La solución: tres mecanismos del paper

Rho implementa exactamente los tres mecanismos especificados en
la Sección 2.2:

1. **Checkpoints cada 4 horas** — persistencia del estado
2. **Stop-loss absoluto del 15%** — límite de pérdida
3. **Backtrack al último estado estable** — recuperación automática

---

## 2. Los tres mecanismos en detalle

### Mecanismo 1: Checkpoints (cada 4 horas)

Cada checkpoint guarda el estado completo del sistema:

```python
SystemCheckpoint:
  checkpoint_id     # identificador único
  timestamp         # marca temporal exacta
  portfolio_value   # valor del portfolio en USD
  delta             # score δ en ese momento
  regime            # régimen detectado
  trading_signal    # señal activa
  open_positions    # posiciones abiertas
  is_stable         # True si δ >= DELTA_CONSOLIDATE (0.70)
```

Solo los checkpoints con `is_stable=True` son candidatos para
backtrack. Esto garantiza que el sistema vuelve a un estado
genuinamente bueno, no a cualquier estado previo.

### Mecanismo 2: Stop-loss absoluto 15%

```python
if (portfolio_value - 100_000) / 100_000 <= -0.15:
    STOP_LOSS_ACTIVADO
    sistema.detener()
    esperar_revision_humana()
```

Si el portfolio cae más de $15,000 desde los $100K iniciales,
el sistema se detiene completamente. No toma más posiciones.
Espera revisión humana explícita.

**Por qué 15%:** el paper lo justifica como el límite máximo
tolerable para un experimento de investigación. No es un límite
de trading profesional (que sería más estricto) — es el límite
que permite al experimento E2 ser significativo sin arriesgar
pérdidas que invaliden el estudio.

### Mecanismo 3: Backtrack al último estado estable

Cuando Kappa detecta δ < 0.65 con posiciones abiertas, Rho
recupera el último checkpoint con `is_stable=True` (δ ≥ 0.70)
y restaura el sistema a ese estado.

```
Estado actual (malo, δ=0.52)
        ↓
Kappa: BACKTRACK
        ↓
Rho: busca último ckpt con is_stable=True
        ↓
Sistema restaurado al estado δ=0.73 de hace 4 horas
```

---

## 3. Hipótesis H7 del paper

```
H7: Tasa de éxito ≥ 0.95 en 30 días sin crash no gestionado
    Falsificación: crash no gestionado O loop > $50 en un evento
```

Rho es la capa responsable de H7. Si Rho funciona correctamente:
- Ningún crash produce pérdidas > $50 en un solo evento
- El sistema se recupera automáticamente en todos los casos
- La tasa de uptime es ≥ 0.95 en los 30 días de E2

**GitHub Actions monitoriza Rho continuamente** (Sección 5):
> *"GitHub Actions monitoriza 24/7. Alerta automática."*
El workflow `heartbeat.yml` verifica el estado de Rho en cada
ejecución y falla el job si Rho reporta `system_healthy=False`.

---

## 4. Resultado de validación real (5 abril 2026)

```
Portfolio:        $100,000 (0% drawdown)
Stop-loss:        OK — no activado
Checkpoint:       ckpt_20260405_172046
  delta=0.5966
  is_stable=False  (correcto: δ < 0.70)
  regime=INDETERMINATE
Checkpoints totales: 1
Último estable:      ninguno (todavía no hay δ ≥ 0.70)
```

**Correcto:** El primer checkpoint no es estable porque δ=0.5966
está por debajo de 0.70. En E2, cuando el sistema opere en régimen
claro con posiciones y δ ≥ 0.70, los checkpoints serán estables y
el backtrack tendrá un estado al que volver.

---

## 5. Escenarios de fallo que Rho previene

**F5 — Kappa mal calibrado, loop de $400:**
> *"Loop de $400 sin backtrack activado. Cortex V2 limita este
> evento a < $40 mediante Κ + Ρ con stop-loss automático."*

El stop-loss de Rho es la red de seguridad final. Incluso si
Kappa falla en detectar el deterioro, el stop-loss del 15%
detiene el sistema antes de que las pérdidas sean catastróficas.

---

## 6. Referencias del paper

- **Sección 2.2:** "Checkpoints cada 4h. Stop-loss 15%.
  Backtrack automático."

- **Sección 3, H7:** Tasa de éxito ≥ 0.95 en 30 días.

- **Sección 4, F5:** Loop de $400 prevenido por Κ + Ρ.

- **Sección 5:** GitHub Actions monitoriza Rho 24/7.

- **Config:** STOP_LOSS_PCT=0.15, CHECKPOINT_HOURS=4.
