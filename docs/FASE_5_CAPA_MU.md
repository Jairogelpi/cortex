# Fase 5 — Capa Μ (Mu): Memoria Selectiva con Isolación

**Cortex V2 · Documentación técnica y científica**
**Estado: COMPLETA y VALIDADA con datos reales**
**Fecha de validación: 5 abril 2026**

---

## 1. Qué es Mu y por qué existe

### El fundamento neurocientifico: sleep replay hipocampal

El hipocampo no consolida todo lo que ocurre durante el día. Durante
el sueño profundo (slow-wave sleep), el hipocampo hace "replay" de los
episodios del día — pero solo de los más relevantes. Los episodios de
baja relevancia se descartan. Los de alta relevancia se transfieren a
la neocorteza para memoria a largo plazo.

Este es el mecanismo que Mu replica para Cortex V2:

- **Delta alto (≥ 0.70):** el estado es valioso → consolidar en memoria
- **Delta bajo (< 0.70):** el estado es de baja calidad → descartar

El paper original especificaba δ > 0.75. Ajustado a 0.70 antes del
pre-registro OSF — ver sección 2 de este documento.

### Por qué es importante para el sistema

Sin Mu, el sistema empieza cada sesión desde cero. Con Mu, cada nueva
sesión parte de un estado informado. La hipótesis H5 del paper mide
exactamente este efecto:

```
H5: Sesiones futuras con δ_inicial ≥ 0.71 vs 0.65 sin Mu
    Falsificación: sin diferencia en δ_inicial entre condiciones
```

---

## 2. El ajuste del umbral: de 0.75 a 0.70

### Por qué se ajustó (justificación matemática)

El techo natural del delta en condiciones neutrales de mercado es:

```
δ_techo_neutral = 0.4 × 0.50   (portfolio igual a SPY)
                + 0.4 × 0.82   (drawdown contenido, -5%)
                + 0.2 × 1.00   (régimen perfectamente consistente)
                = 0.73
```

Con el umbral original en 0.75, Mu solo consolidaría cuando el
portfolio **bate activamente al benchmark SPY** — lo cual es infrecuente
en condiciones normales de mercado. Consecuencia: H5 no es testeable
en E2 porque Mu raramente consolidaría.

Con el umbral en 0.70, Mu consolida cuando el sistema opera 3 puntos
por encima del techo natural en condiciones neutras (0.73 > 0.70 ✓).
Preserva la selectividad del sleep replay hipocampal y hace H5 testeable.

### Cuándo se aplicó

Este ajuste se realizó **antes del pre-registro en OSF**, en la fase
de construcción del sistema. Una vez pre-registrado, el umbral no puede
modificarse sin invalidar el experimento. El momento correcto para
ajustar es ahora.

Ver: `docs/CHANGELOG_UMBRALES.md` y `docs/PROPUESTA_AJUSTE_UMBRALES.md`

---

## 3. La condición de consolidación (ajustada, pre-OSF)

```python
if delta >= 0.70:   # DELTA_CONSOLIDATE ajustado
    CONSOLIDAR      # guardar en memoria permanente
else:
    RECHAZAR        # sleep replay descarta este estado
```

---

## 4. El escenario de fallo F2 — contaminación entre sesiones

El paper describe explícitamente este riesgo (Sección 4):

> *"F2: Contaminación de memoria Mu infla resultados de evaluación.
> Memoria de sesión A contamina evaluación de sesión B.
> Resultado: Sharpe inflado artificialmente. Falso positivo H4."*

### La mitigación: isolation layers + test de correlación

**1. Namespace por sesión:** cada sesión tiene su propio archivo JSON
en `data/memory/session_YYYYMMDD_HHMMSS.json`.

**2. Test de correlación entre sesiones:** si ρ ≥ 0.30 (umbral del
paper), hay posible leakage y se activa la alerta.

---

## 5. Resultado de validación real (5 abril 2026)

```
Delta actual:    0.5961
Umbral Mu:       0.70  (ajustado desde 0.75)
Decisión:        NO CONSOLIDAR
Rechazadas:      1
Consolidadas:    0
```

**Este es el comportamiento correcto.** Con δ=0.5961 < 0.70:
- El régimen es INDETERMINATE — sin régimen confirmado no hay
  conocimiento valioso que consolidar
- No hay posiciones abiertas — no hay decisión de trading que evaluar

El comportamiento no cambió con el ajuste: 0.5961 está por debajo
tanto de 0.70 como de 0.75. La diferencia se notará en E2 cuando
el sistema opere en régimen claro con δ ≈ 0.71–0.73.

---

## 6. Cuándo consolidará Mu en E2

Durante el experimento E2 (30 días de paper trading), Mu consolidará
cuando:

- El sistema tome una posición y δ ≥ 0.70 tras 4 horas
- El régimen cambie de INDETERMINATE a R1/R2/R3/R4 confirmado
- Lambda produzca CONFIRMED con similitud alta y δ posterior ≥ 0.70

Con el techo natural en 0.73, esto ocurrirá en condiciones normales
de mercado claro — no solo cuando el sistema bata activamente al SPY.

---

## 7. Persistencia en disco

```
data/
└── memory/
    ├── session_20260405_144023.json   ← sesión de hoy (0 consolidadas)
    └── ...
```

---

## 8. Referencias del paper

- **Hipocampo (sleep replay, bioRxiv feb 2026):** Fundamento
  neurocientifico de Mu. Consolidación selectiva durante el replay.

- **Sección 2.2:** "Mu replica el sleep replay hipocampal. Solo
  δ > 0.70. Reduce tokens 50%." (ajustado desde 0.75)

- **Sección 2.1:** Umbral DELTA_CONSOLIDATE = 0.70. Pre-OSF.

- **Sección 4, F2:** Contaminación de memoria entre sesiones.
  Isolation layers. Test de correlación ρ < 0.3.

- **Sección 5:** Condición de confianza de Mu — "isolación
  confirmada (no leakage). Señal de alarma: correlación > 0.3."

- **Sección 3, H5:** "Sesiones futuras con δ_inicial ≥ 0.71
  vs 0.65 sin Mu." Experimento E2.
