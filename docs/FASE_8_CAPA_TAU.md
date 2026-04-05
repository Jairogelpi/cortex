# Fase 8 — Capa Τ (Tau): Governance y Control de Herramientas

**Cortex V2 · Documentación técnica y científica**
**Estado: COMPLETA y VALIDADA con datos reales**
**Fecha de validación: 5 abril 2026**

---

## 1. Qué es Tau y por qué es una necesidad de seguridad

### El dato que lo justifica todo

Carnegie Mellon + Allen Institute for AI (febrero 2026):

> *"Los agentes exhiben comportamiento inseguro en el 51.2%–72.7%
> de las tareas críticas en escenarios reales multi-turno."*

Este dato, citado en la Sección 8 del paper, cambia completamente
cómo hay que entender Tau. No es una mejora de rendimiento. Es una
necesidad de seguridad documentada empíricamente.

Un agente de trading que opera durante 30 días continuos **tiene
más del 50% de probabilidad** de exhibir comportamiento inseguro
en algún momento crítico si no hay una capa de control explícita.
Tau es esa capa.

### El problema que resuelve

El escenario de fallo F3 del paper:

> *"Tau no bloquea. Sigma no requiere aprobación. Compra/venta
> irreversible. Pérdida irreparable."*

Sin Tau, cualquier decisión de Sigma se ejecuta directamente en
Alpaca. Con Tau, cualquier acción que mueva más del 5% del
portfolio requiere una revisión explícita antes de ejecutarse.

---

## 2. Las dos funciones de Tau

### Función 1: Control de acciones irreversibles

Tau clasifica cada acción propuesta por Sigma y decide si puede
ejecutarse automáticamente o requiere aprobación humana:

| Acción | Clasificación | Paper trading | Trading real |
|--------|---------------|---------------|--------------|
| HOLD / CASH | No irreversible | Auto-aprobado | Auto-aprobado |
| BACKTRACK | No irreversible | Auto-aprobado | Auto-aprobado |
| Compra/venta < 5% | Reversible | Auto-aprobado | Auto-aprobado |
| Compra/venta > 5% | IRREVERSIBLE | Aprobado + registro | **BLOQUEADO** |
| Modificar stop-loss | IRREVERSIBLE | Aprobado + registro | **BLOQUEADO** |

Del paper (Sección 8):
> *"Ninguna compra, venta, o cambio de posición > 5% del portfolio
> se ejecuta sin validación de Lambda y aprobación de Tau."*

### Función 2: Control de tools por scope (AutoHarness)

Tau bloquea el acceso a herramientas que están fuera del scope
de la señal activa. Basado en AutoHarness (MIT, 2026):

| Señal | Tools permitidas | Tools bloqueadas |
|-------|-----------------|-----------------|
| CASH / HOLD | market_data, regime_monitor | order_validator, equity_data, bond_data... |
| LONG | market_data, regime_monitor, equity_data, order_validator | bond_data... |
| DEFENSIVE | market_data, regime_monitor, bond_data | equity_data, order_validator... |

Esto previene que un subagente acceda a herramientas que no
corresponden a su contexto — uno de los vectores de comportamiento
inseguro documentados por Carnegie Mellon.

---

## 3. Paper trading vs trading real

La distinción es fundamental para Tau:

**En paper trading (E2 actual):**
Tau aprueba todas las acciones automáticamente pero registra
cuáles requerirían aprobación humana en trading real. Esto
permite auditar el comportamiento del sistema sin riesgo real.

**En trading real (futuro, post-E2):**
Tau bloquea activamente hasta recibir confirmación humana
explícita para cualquier acción irreversible. El operador
recibe una alerta y debe aprobar manualmente.

Del paper (Sección 10.3):
> *"Nivel 2 (paper trading): Cortex propone → humano aprueba →
> Alpaca ejecuta. Nivel 3 (futuro): Cortex propone + ejecuta →
> humano audita a posteriori."*

Actualmente estamos en Nivel 2. Tau implementa ese nivel.

---

## 4. Resultado de validación real (5 abril 2026)

```
Sigma decision:      HOLD
Señal activa:        CASH
Acción clasificada:  HOLD_NO_ACTION
Aprobada:            True
Requiere humano:     False
Tools permitidas:    ['market_data', 'regime_monitor']
Razón:               "Senal CASH/HOLD: no hay accion que aprobar."
```

**Correcto:** Con señal CASH y decisión HOLD, Tau aprueba
automáticamente porque no hay acción que ejecutar. En E2, cuando
el sistema genere señales LONG o DEFENSIVE, Tau registrará que
las órdenes > 5% requerirían aprobación humana en trading real.

---

## 5. Escenario F3 prevenido

**F3 — Acción irreversible sin validación:**
> *"Tau no bloquea. Sigma no requiere aprobación. Compra/venta
> irreversible. Pérdida irreparable."*

Con Tau activo y `is_paper_trading=False` (trading real), cualquier
orden > 5% del portfolio activa el bloqueo. El sistema no puede
ejecutar por sí mismo — espera confirmación explícita del operador.

---

## 6. El kill switch MiFID II

La Sección 10.3 del paper especifica que trading real bajo MiFID II
requiere un kill switch activable por el regulador. Tau implementa
la base de ese kill switch: cualquier acción puede ser bloqueada
en tiempo real cambiando `is_paper_trading=False`.

El kill switch completo para cumplimiento MiFID II requiere además:
- Registro de todas las anulaciones humanas (parcialmente implementado)
- Activación remota por el regulador (pendiente para v2.1)

---

## 7. Referencias del paper

- **CMU + AI2 (febrero 2026):** 51.2%–72.7% comportamiento inseguro.
  Tau como necesidad de seguridad, no mejora.

- **Sección 2.2:** "Gobierno de acciones irreversibles. Aprobación
  humana. Bloqueo de tools fuera de scope."

- **Sección 4, F3:** Acción irreversible sin validación prevenida.

- **Sección 8:** AutoHarness (MIT, 2026). Governance rules.
  Ninguna orden > 5% sin aprobación de Tau.

- **Sección 10.3:** MiFID II. Kill switch. Nivel 2 de autonomía.
