# Cortex VNext — Arquitectura Evidence-First
## Propuesta concreta para una IA de agentes con menos sesgo y más verdad

**Estado:** propuesta de evolución, no implementada todavía.
**Objetivo:** que el LLM deje de ser el cerebro y pase a ser solo un detector de novedad, conflicto y huecos de evidencia.

---

## 1. Tesis central

La arquitectura actual ya redujo el coste de razonamiento y corrigió la falsa promesa de H1. El siguiente salto no es gastar menos tokens por la misma narrativa, sino cambiar la función del LLM:

- El LLM no decide.
- El LLM no redacta una explicación larga para justificar la acción.
- El LLM solo detecta novedad, conflicto, contradicción no obvia y falta de evidencia.
- La decisión final la produce una política verificable basada en evidencia, abstención y umbrales.

Esto es más revolucionario porque separa:

- percepcion de evidencia,
- deteccion de conflicto,
- verificacion,
- y ejecucion de la decision.

---

## 2. Principios de diseño

1. Evidencia antes que narracion. Ninguna accion se ejecuta sin soporte trazable.
2. Abstencion por defecto cuando la evidencia es incompleta o conflictiva.
3. El LLM solo entra si hay ambiguedad real o novedad suficiente.
4. Toda salida del LLM debe ser JSON breve y validable.
5. Un critic adversarial intenta romper la propuesta antes de permitir accion.
6. La memoria guarda casos y resultados, no texto decorativo.
7. El sistema debe ser auditable de extremo a extremo.

---

## 3. Mapa de modulos propuestos

### 3.1 Modulos nuevos

- `cortex/evidence_ledger.py`
  - Estructuras `EvidenceItem`, `EvidenceBundle`, `EvidenceClaim`.
  - Registra soporte, contradicciones, frescura, cobertura y calidad de fuente.

- `cortex/novelty_router.py`
  - Calcula `novelty_score`, `conflict_score` y `evidence_gap`.
  - Decide si el caso pasa por ruta determinista o por revision LLM.

- `cortex/adversarial_critic.py`
  - Agente que busca la mejor refutacion posible de la propuesta.
  - Produce solo: `critique`, `missing_evidence`, `refutation_strength`.

- `cortex/verifier.py`
  - Verifica consistencia entre evidencia, decision y memoria historica.
  - Bloquea decisiones si faltan pruebas criticas.

- `cortex/abstention_policy.py`
  - Convierte incertidumbre y cobertura de evidencia en `EXECUTE`, `HOLD`, `BACKTRACK` o `ABSTAIN`.

- `cortex/decision_packet.py`
  - Paquete unico que viaja por todo el pipeline.
  - Unifica evidencia, critica, verificacion, confianza y accion final.

- `cortex/memory_retriever.py`
  - Recupera episodios historicos parecidos desde `data/memory/`.
  - Devuelve solo recuerdos relevantes con score y resultado real.

### 3.2 Modulos existentes que se reutilizan

- `cortex/layers/phi.py` sigue siendo el factor deterministico del estado.
- `cortex/layers/kappa.py` sigue siendo el critic numerico de delta.
- `cortex/layers/sigma.py` sigue orquestando subagentes, pero ahora consume un `DecisionPacket` mas rico.
- `cortex/layers/rho.py`, `tau.py` y `omicron.py` siguen como infraestructura y observabilidad.

---

## 4. Flujo operativo propuesto

### Fase A. Construccion de evidencia

1. `MarketData` extrae el estado actual.
2. `PhiLayer` factoriza el estado en Z.
3. `MemoryRetriever` busca casos historicos similares.
4. `EvidenceLedger` agrupa indicadores actuales, memoria y señales frescas.

### Fase B. Deteccion de novedad y conflicto

5. `NoveltyRouter` calcula:
   - `novelty_score`
   - `conflict_score`
   - `evidence_gap`
6. Si la señal es clara, el sistema sigue por ruta determinista.
7. Si hay ambiguedad real, se activa una revision LLM minima.

### Fase C. Revision LLM ultracompacta

8. El LLM recibe solo:
   - snapshot compactado del mercado,
   - top evidencias,
   - top contradicciones,
   - huecos de evidencia,
   - una hipotesis actual.
9. El LLM responde solo JSON con:
   - `novelty_flags`
   - `conflicts`
   - `missing_evidence`
   - `keep_or_flip`
10. No se le pide prosa larga ni razonamiento ornamental.

### Fase D. Critica adversarial y verificacion

11. `AdversarialCritic` intenta refutar la hipotesis y la accion propuesta.
12. `Verifier` comprueba que la evidencia soporte la decision.
13. Si el critic y el verifier discrepan de forma fuerte, se activa abstencion.

### Fase E. Politica final

14. `AbstentionPolicy` decide:
   - `EXECUTE` si la evidencia es suficiente y consistente.
   - `HOLD` si el mercado es ambiguo pero no hay riesgo critico.
   - `BACKTRACK` si la hipotesis contradice evidencia fuerte.
   - `ABSTAIN` si la cobertura es insuficiente.

### Fase F. Registro

15. `Omicron` registra el packet completo.
16. El log guarda la evidencia, la refutacion, la abstencion o la accion.

---

## 5. Cambios exactos en el pipeline

### Cambio 1. Sustituir la idea de "salida final de LLM"

La salida de `UnifiedLayer` deja de ser una pseudo-decision final basada en texto y pasa a ser un `DecisionPacket` con estos campos minimos:

- `best_hypothesis`
- `novelty_score`
- `conflict_score`
- `evidence_coverage`
- `critic_result`
- `verification_result`
- `final_action`
- `abstain_reason`
- `llm_used`
- `token_usage`

### Cambio 2. Reemplazo funcional de `UnifiedLayer`

`cortex/unified_layer.py` se convierte en una capa de orquestacion de evidencia, no en un agente narrativo.

Responsabilidad nueva:

- construir el packet,
- decidir si el LLM hace falta,
- invocar critic/verifier,
- devolver accion y abstencion.

### Cambio 3. Sigma consume decision, no relato

`SigmaLayer.orchestrate(...)` pasa a recibir un `decision_packet` o un resumen equivalente.

Sigma ya no depende de una historia textual para decidir subagentes. Depende de:

- accion final,
- confianza,
- cobertura de evidencia,
- nivel de conflicto.

### Cambio 4. Omicron registra evidencia, no solo resultado

El log de telemetria debe incluir:

- `novelty_score`
- `conflict_score`
- `evidence_coverage`
- `critic_refutation_strength`
- `abstain_reason`
- `token_usage_by_agent`

### Cambio 5. Kappa sigue igual

Kappa sigue siendo el critic matematico. No debe volverse un LLM. Ese es un error que este diseño evita.

---

## 6. Politica de abstencion

La abstencion debe ser una accion de primera clase.

Reglas iniciales:

- Si `evidence_coverage < 0.60`, abstenerse.
- Si `conflict_score > 0.70` y el critic no resuelve la contradiccion, abstenerse.
- Si la novedad es alta pero la memoria historica no ofrece anclaje, pedir mas evidencia o abstenerse.
- Si el verifier no puede confirmar puntos criticos, no se ejecuta orden.

Esto evita el sesgo tipico de IA de agentes: hablar mucho cuando no sabe suficiente.

---

## 7. Metricas nuevas que deberia medir Cortex

- `decision_per_token`
- `abstention_precision`
- `false_confidence_rate`
- `evidence_coverage_mean`
- `critic_refutation_rate`
- `verification_block_rate`
- `regret_post_decision`
- `latency_to_safe_action`

La meta ya no es solo tokens bajos. La meta es mejor decision por token y menor sesgo de confirmacion.

---

## 8. Fases de implementacion

### Fase 1. Scaffold

- Crear `decision_packet.py`, `evidence_ledger.py`, `novelty_router.py`.
- Mantener compatibilidad con `PhiState`, `OmegaHypothesis` y `LambdaValidation`.

### Fase 2. Shadow mode

- Correr el sistema evidence-first en paralelo con el pipeline actual.
- No ejecutar ordenes basadas en la ruta nueva todavia.
- Comparar decision, abstencion y regret.

### Fase 3. Activacion controlada

- Habilitar la nueva ruta solo cuando `novelty_score` y `evidence_coverage` superen umbrales.

### Fase 4. Sustitucion de UnifiedLayer

- Retirar la semantica de "una sola llamada LLM" como narrativa principal.
- El LLM pasa a ser detector y critic, no narrador.

---

## 9. Lo que cambia filosoficamente

La IA de agentes deja de ser un sistema que intenta sonar inteligente y pasa a ser un sistema que intenta no mentir.

Eso es mas serio que un prompt mas grande. Tambien es mas dificil. Pero es el camino correcto si el objetivo es una arquitectura realmente fiable.

---

## 10. Cierre

La version actual de Cortex ya mejoro la eficiencia tecnica.
La siguiente revolucion es epistemica:

- menos narrativa,
- mas evidencia,
- mas abstencion correcta,
- y un LLM relegado a detectar incertidumbre, no a inventar certeza.
