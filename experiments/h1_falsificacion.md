# H1 — Token Efficiency: Análisis de Falsificación
## Cortex V2 | OSF: https://osf.io/wdkcx
## Fecha: 7 abril 2026 | Datos reales de E2 día 1

---

## Resultado

**H1 SE FALSIFICA con los datos reales de E2.**

| Métrica | Valor | Objetivo pre-registrado |
|---------|-------|------------------------|
| Tokens A (Cortex completo) | 2284 | ≤ 178 |
| Tokens B (LLM base) | 396 | — (baseline) |
| Ratio A/B | 5.77 | ≤ 0.45 |
| Resultado | **FAIL** | PASS |

---

## Desglose real de tokens en Condición A

| Capa | Tokens in | Tokens out | Total | Modelo |
|------|-----------|------------|-------|--------|
| Phi  | 294 | 166 | 460 | Sonnet 4.6 |
| Kappa| 104 |  68 | 172 | Haiku 4.5 |
| Omega| 346 | 376 | 722 | **Opus 4.6** |
| Lambda| 380 | 550 | 930 | Sonnet 4.6 |
| **TOTAL** | **1124** | **1160** | **2284** | — |

Lambda es la capa más costosa (930 tokens) por su output largo de
razonamiento crítico. Omega es la segunda (722 tokens) por el tamaño
del prompt a Opus.

---

## Por qué H1 falla — análisis honesto

El paper afirma (Sección 3, H1):

> "Tokens_Cortex ≤ 0.45 × Tokens_baseline (OpenRouter API)"

La hipótesis asume que Phi "poda el contexto" antes de pasarlo al resto
del sistema, reduciendo los tokens totales netos. El razonamiento era:

1. Phi factoriza el estado en Z₁...Z₈ (vector compacto de 8 números)
2. Omega y Lambda reciben Z en vez del contexto bruto completo
3. Por tanto el contexto total de A < contexto de B × 5 capas

**El error de razonamiento:**

Esto es verdad para el tamaño del CONTEXTO por llamada (cada capa de A
recibe un prompt más pequeño que el que recibiría sin Phi). Pero H1
mide tokens TOTALES acumulados, no tokens por llamada.

A hace 4 llamadas LLM. B hace 1 llamada LLM.
4 llamadas × ~570 tokens/llamada = ~2284 tokens.
1 llamada × 396 tokens = 396 tokens.

La poda semántica de Phi reduce el tamaño de cada llamada, pero no
puede compensar el factor multiplicador de hacer 4 llamadas en vez de 1.

---

## Qué implica esto científicamente

### Lo que H1 falsificada NO implica:
- No implica que Cortex V2 sea peor que B
- No implica que la arquitectura no tenga valor
- No implica que el sistema sea ineficiente para el valor que produce

### Lo que H1 falsificada SÍ implica:
- La afirmación de "token efficiency" del paper es incorrecta tal como
  está formulada
- El claim de "ahorro del 87%" en la Sección 7 (tabla de eficiencia)
  no es reproducible con la implementación actual
- H6 (coste subagentes < 0.30× coste total) tampoco se puede sostener
  con la arquitectura actual

---

## Reformulación honesta post-falsificación

H1 debe reformularse para ser testeable y falsifiable con los datos reales.

**H1 reformulada (compatible con los datos):**

> "La calidad de decisión por token es superior en A vs B:
> A produce mejor abstracción semántica (mayor similitud isomorfo)
> con tokens de contexto por llamada LLM ≤ B."

Esta formulación captura el valor real de Phi (poda semántica por
llamada) sin hacer el claim incorrecto de tokens totales menores.

**H1 alternativa (para E5 si se implementa):**

> "Para la misma tarea de análisis de régimen de mercado, A usa
> ≤ 0.45× tokens que un sistema sin factorización semántica que
> necesita pasar el contexto completo a cada modelo."

Esto requeriría implementar un sistema B' que pase el contexto bruto
completo a cada una de las 4 llamadas, para comparación justa.

---

## Impacto en el paper

### Secciones afectadas:
1. **Sección 3 (H1):** criterio de falsificación debe actualizarse
2. **Sección 7 (Tabla de token efficiency):** cifras de ahorro 87%/75%
   son teóricas, no empíricas con la implementación actual
3. **Abstract:** eliminar o calificar el claim de token efficiency

### Lo que NO cambia:
- H4, H5, H7 siguen siendo testeables y no falsificadas
- H2, H3 siguen siendo testeables
- La ablación (D dice BACKTRACK incorrecto, A no) sigue siendo evidencia
  real del valor de la arquitectura completa
- La arquitectura técnica es sólida — solo el claim de eficiencia falla

---

## Protocolo de publicación honesta

Per el pre-registro OSF (osf.io/wdkcx):

> "Si alguna se falsifica, ese resultado se publica completo — no se oculta."

El resultado completo de H1 se publicará en el paper:
- Tokens reales medidos: A=2284, B=396, ratio=5.77
- Fecha de medición: 7 abril 2026 (día 1 de E2)
- Conclusión: H1 falsificada con implementación actual
- Reformulación propuesta incluida en sección de discusión

---

## Datos verificables

El log que contiene estos datos:
`logs/e2_ablation_20260407.jsonl` (GitHub: Jairogelpi/cortex)

Token breakdown registrado en pipeline.py via token_tracker.py.
Reproducible ejecutando `run_ablacion.py` con las mismas condiciones
de mercado (o datos archivados de ese día).

*Documento generado el 7 de abril de 2026.*
*Basado exclusivamente en datos reales. Sin interpretación optimista.*
