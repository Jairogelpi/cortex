# E2 — Análisis de Ablación: Estado Real sin Sesgos
## Cortex V2 | OSF: https://osf.io/wdkcx
## Generado: 7 abril 2026

---

## Estado general: ¿Funciona como debe?

**La infraestructura funciona.** Las 4 condiciones corren con datos reales,
se registran en logs, se suben a GitHub automáticamente cada mañana a las
09:00 UTC. No hay simulaciones ni mocks en ninguna capa.

**Los datos científicos son reales.** VIX, SPY, FRED, Alpaca — todo real.
El portfolio empezó en $100,000 y hoy tiene $100,007.62 (intereses del cash).

**Lo que NO está funcionando como el paper promete:**

---

## Problema 1 — H1 FALLA: A usa 7× más tokens que B

El paper dice: "Tokens_Cortex ≤ 0.45 × Tokens_baseline"

**Realidad medida hoy:**
- Condición A (Cortex completo): ~2800 tokens (estimación)
- Condición B (LLM base): ~400 tokens (medido exactamente)
- Ratio: 7.0 (el paper requiere ≤ 0.45)

**Por qué falla:**
Cortex V2 hace 5 llamadas LLM por sesión (Phi, Kappa, Omega, Lambda ×2).
B hace 1 llamada. La hipótesis H1 asume que Phi "poda el contexto" reduciendo
los tokens NETOS del sistema, pero en la práctica multiplica las llamadas.

**Lo que hay que hacer honestamente:**
1. Medir tokens reales de A (no usar la estimación de 2800 — conectar la
   telemetría real de tokens de OpenRouter a Omicron)
2. Si los tokens reales de A son > 0.45 × B, H1 se falsifica
3. El paper tiene un error de razonamiento en H1: confunde "tokens por
   decisión de trading" con "tokens por llamada LLM"

**Esto no invalida el sistema — invalida una hipótesis específica.**
Un sistema puede ser científicamente valioso aunque use más tokens que
un baseline simple, si produce mejores decisiones (H4).

---

## Problema 2 — D comete un error que A no comete

**Hallazgo del día 1 (positivo para la tesis):**

Condición D (solo Kappa+Rho) produjo BACKTRACK con delta=0.6206.
Condición A (Cortex completo) produjo HOLD con delta=0.5959.

La diferencia es que D no sabe que el portfolio está en 100% cash.
Sin Phi (que factoriza el estado completo incluyendo posiciones), D
aplica la regla delta < 0.65 → BACKTRACK mecánicamente, incluso cuando
no hay posición que retroceder.

**Esto es exactamente lo que la ablación debe mostrar:** la arquitectura
completa tiene información contextual que la ablación parcial no tiene.
D no es "más simple pero igual de bueno" — D comete errores que A evita.

Este hallazgo ya aparece en el día 1 y es reproducible.

---

## Problema 3 — H5 no es medible todavía

delta_A=0.5957 vs delta_C=0.5954 → diff=+0.0003 (prácticamente igual)

H5 requiere que Mu haya consolidado memorias para que A tenga ventaja
sobre C en el delta inicial de sesiones futuras. Mu solo consolida cuando
delta ≥ 0.70, lo que ocurre en R1_EXPANSION.

Con el mercado actual (INDETERMINATE, delta ~0.596), Mu no consolida nada.
H5 es INCALCULABLE hoy — no es FAIL, es "pendiente de datos".

H5 requiere al menos 5-10 días de R1_EXPANSION donde Mu consolide y
luego se pueda comparar el delta inicial de A (con memorias) vs C (sin ellas).

---

## Lo que sí funciona exactamente como debe

### Decisiones coherentes con el mercado real
Las 4 condiciones toman HOLD o CASH — ninguna sugiere LONG en un mercado
con VIX=24.17, momentum=-3.02%, y régimen INDETERMINATE. La dirección es
correcta en todas las condiciones.

### Lambda añade información que C no tiene
A detectó 6 contradicciones en la hipótesis de Lorenz gracias a Lambda.
C acepta Lorenz directamente sin verificación. En la práctica hoy llegan
a la misma decisión (HOLD/HOLD_CASH), pero en un mercado con señales
más mixtas, Lambda podría cambiar la decisión donde C no lo haría.

### H7 uptime: 12/12 = 100%
Todas las ejecuciones de hoy completaron sin crash. El sistema es estable.

### GitHub Actions funciona con LLMs reales
El run automático del 6 de abril a las 21:08 UTC usó LLMs reales:
Phi, Kappa, Omega, Lambda — todas las capas. No fue fallback determinista.
FRED también conectó correctamente.

---

## Acciones pendientes antes de que E2 tenga valor científico

### Urgente (esta semana)
1. **Medir tokens reales de A:** conectar OpenRouter usage a Omicron para
   registrar tokens exactos en cada sesión. Sin esto, H1 usa una estimación.

2. **Limpiar el log de hoy:** el log del 7 de abril tiene 12 líneas de 3
   runs de test. La corrección aplicada (sobreescribir por condición) funciona
   desde el próximo run, pero el log de hoy está contaminado.

3. **Documentar H1 como potencialmente falsificada:** si los tokens reales
   de A confirman el ratio >0.45, H1 se falsifica en E2. Eso hay que
   pre-documentarlo antes de tener los datos completos de 30 días.

### Esta semana
4. **Conseguir evaluadores para E3:** los 50 pares están listos.
   Sin E3 no se puede medir H2.

### En 30 días (fin de E2)
5. **Calcular Sharpe y MDD por condición:** requiere los 30 días completos
   con decisiones reales ejecutadas en Alpaca. Hoy todo es HOLD — no hay
   suficiente variabilidad para calcular Sharpe todavía.

---

## Resumen ejecutivo honesto

El sistema **funciona** en el sentido técnico. Produce decisiones reales,
las registra, las sube a GitHub, las compara entre condiciones.

El sistema **puede no cumplir H1** (token efficiency). Esto hay que medirlo
correctamente y publicar el resultado sea cual sea.

El sistema **ya demuestra en día 1** que la ablación D produce errores que
A no produce (BACKTRACK incorrecto en cash). Eso es evidencia real de que
la arquitectura completa añade valor sobre el baseline mínimo.

El sistema **necesita mercado variable** (R1_EXPANSION seguido de deterioro)
para que H4, H5 tengan datos suficientes. El mercado actual (INDETERMINATE)
produce HOLD constante en todas las condiciones — no hay señal diferenciadora.

*Documento generado el 7 de abril de 2026.*
*Basado exclusivamente en datos reales del log e2_ablation_20260407.jsonl.*
*Sin interpretación optimista. Sin ocultar los problemas.*
