# Fase 6 — Capa Σ (Sigma): Orquestador Adaptativo

**Cortex V2 · Documentación técnica y científica**
**Estado: COMPLETA y VALIDADA con datos reales**
**Fecha de validación: 5 abril 2026**

---

## 1. Qué es Sigma y por qué existe

### El problema que resuelve

Después de que Phi factoriza el estado, Kappa evalúa el delta, Omega
detecta el isomorfo y Lambda valida la hipótesis, alguien tiene que
tomar la decisión final: ¿qué hacemos? ¿qué subagentes activamos?
¿en qué orden? ¿cuántos simultáneamente?

Sin un orquestador, el sistema podría activar todos los subagentes
posibles en paralelo, producir deadlocks, o ejecutar acciones
contradictorias. El escenario de fallo F4 del paper:

> *"Sigma asigna dos subagentes Xi que esperan el uno al otro.
> Sistema inactivo. Heartbeat falla. Costes de oportunidad."*

### La solución: planificación jerárquica (Badre 2025)

Sigma implementa el mecanismo del PFC anterior descrito en Badre (2025):
planificación jerárquica de objetivos. El sistema integra toda la
información disponible y genera un plan coherente con el mínimo de
recursos necesarios.

**Principio de diseño crítico:** Sigma no usa LLMs. Es lógica
determinista pura. Toda la complejidad del razonamiento ya ocurrió
en Phi (Sonnet), Omega (Opus) y Lambda (Sonnet). Sigma solo integra
y decide. Esto garantiza latencia mínima y reproducibilidad total.

---

## 2. Las tres decisiones de Sigma

### Decisión 1: Qué subagentes activar

Sigma selecciona el conjunto mínimo de subagentes necesarios según
el estado del sistema. Máximo 5 simultáneos (escenario F7):

| Situación | Subagentes activados |
|-----------|---------------------|
| CASH / delta bajo | `monitor_regime` (1 subagente) |
| Lambda CONTRADICTED | `backtrack_manager` (1 subagente) |
| EXECUTE confirmado | `risk_calculator`, `position_sizer`, `order_validator` (3) |
| DEFENSIVE / UNCERTAIN | `defensive_allocator`, `risk_calculator` (2) |

### Decisión 2: La acción final

| Condición | Acción | Razonamiento |
|-----------|--------|--------------|
| Lambda CONTRADICTED | BACKTRACK | F1 activado |
| δ < 0.65 | HOLD | Delta insuficiente |
| Señal CASH o INDETERMINATE | HOLD | No operar en caos |
| Lambda UNCERTAIN | DEFENSIVE | Esperar confirmación |
| Lambda CONFIRMED + LONG | EXECUTE | Proceder con Tau |
| Señal DEFENSIVE | DEFENSIVE | Phase_transition detectado |

### Decisión 3: Prevención de deadlocks (F4)

Sigma garantiza que ningún subagente quede bloqueado esperando a otro.
Timeout de 60 segundos por subagente (del paper). Si se supera:
reinicio automático del subagente bloqueado.

---

## 3. Por qué Sigma es determinista (sin LLM)

La Sección 8.10 del paper especifica:

> *"Sigma: planificación jerárquica. Decide qué subagentes activar
> y en qué orden. Haiku insuficiente para orquestación compleja."*

Pero el paper también especifica que Sigma no necesita creatividad —
necesita consistencia. La lógica de orquestación es un árbol de
decisión bien definido. Implementarlo como lógica determinista es:

1. **Más rápido**: sin latencia de API
2. **Reproducible**: mismo input → mismo output siempre
3. **Auditable**: cada decisión tiene un razonamiento textual claro
4. **Seguro**: no puede "alucinar" una decisión de orquestación

---

## 4. Resultado de validación real (5 abril 2026)

```
Régimen:      INDETERMINATE
Delta:        0.5966
Señal Omega:  CASH
Lambda:       CONFIRMED

Subagentes activados: ['monitor_regime']
Decisión:             HOLD
Razonamiento:         "Senal=CASH regimen=INDETERMINATE.
                       Lorenz/INDETERMINATE: no operar en caos."
Duración:             0.003s
```

**Correcto:** Con señal CASH y régimen INDETERMINATE, Sigma activa
solo el subagente de monitoreo y decide HOLD. Sin ejecutar, sin
deadlocks posibles, sin subagentes innecesarios.

---

## 5. Escenarios de fallo que Sigma previene

**F4 — Deadlock de orquestación:**
> *"Sigma asigna dos subagentes Xi que esperan el uno al otro.
> Timeout 60s por subagente. Sigma detecta deadlock y reinicia
> el subagente bloqueado."*

**F7 — Proliferación de subagentes:**
> *"Sin límite de subagentes activos en Sigma. $1000+ en una
> sesión sin techo de presupuesto. Mitigación: máximo N=5
> subagentes simultáneos."*

Hoy Sigma activó 1 subagente de los 5 permitidos. El sistema
es eficiente por diseño — no activa más de lo necesario.

---

## 6. Referencias del paper

- **Badre (2025):** PFC anterior: planificación jerárquica de
  objetivos. Fundamento neurocientifico de Σ.

- **Sección 2.2:** "Σ activa solo los subagentes relevantes para
  el régimen detectado. Timeout 60s. Detecta deadlocks."

- **Sección 4, F4:** Deadlock de orquestación. Timeout + reinicio.

- **Sección 4, F7:** Proliferación de subagentes. Máximo N=5.

- **Config:** MAX_SUBAGENTS=5, SUBAGENT_TIMEOUT=60s.
