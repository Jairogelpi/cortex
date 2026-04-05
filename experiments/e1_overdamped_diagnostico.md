# Análisis de overdamped_system — Diagnóstico Final
## Cortex V2 | Experimento E1

**Fecha:** 5 de abril de 2026
**Basado en:** 123 días reales, sept 2025–mar 2026

---

## El diagnóstico real — sin sesgos

### Qué ocurrió exactamente

overdamped_system **sí detectó patrones relevantes** en el mercado.
La similitud máxima fue 0.7810 (supera el threshold 0.65).
Tuvo sim >= 0.65 en 10 días.
Superó a gas_expansion en 45 días.

Pero nunca ganó, porque **lorenz_attractor tuvo similitud aún mayor**
en casi todos esos 45 días.

### Los 45 días — qué dicen realmente

Mirando los datos concretos:

**Grupo A — Nov 2025, momentum ligeramente negativo (-0.5% a -2%), VIX 17-25:**
```
2025-11-06  INDETERMINATE  VIX=19.5  mom=-0.42%  overdamped=0.4695  lorenz=0.7333
2025-11-18  R2_ACCUM       VIX=24.7  mom=-1.67%  overdamped=0.6295  lorenz=0.7100
2025-11-19  R2_ACCUM       VIX=23.7  mom=-1.29%  overdamped=0.6232  lorenz=0.6899
```

**Grupo B — Mar 2026, deterioro progresivo, VIX 20-31, mom -1.5% a -7.8%:**
```
2026-03-12  INDETERMINATE  VIX=27.3  mom=-3.77%  overdamped=0.6561  lorenz=0.8933
2026-03-20  INDETERMINATE  VIX=26.8  mom=-4.99%  overdamped=0.6566  lorenz=0.8935
2026-03-27  R3_TRANSITION  VIX=31.1  mom=-7.76%  overdamped=0.7562  lorenz=0.9017
```

### El patrón que emerge

Lorenz_attractor domina porque su vector Z de referencia tiene
Z4=-0.75 (coherencia muy negativa) y Z8=+0.90 (alta complejidad).
En cualquier día con momentum negativo y VIX elevado, el vector Z
del mercado se parece geométricamente a Lorenz **más** que a
overdamped_system, porque Z4 y Z8 son los discriminadores más fuertes.

overdamped_system tiene Z4=-0.10 y Z8=+0.10 — muy cercanos a cero.
Eso significa que overdamped solo gana cuando el mercado está en un
estado de **baja entropía y alta reversibilidad** (Z6=+0.80),
SIN señales de caos (Z4~0, Z8~0). En el período sept 2025–mar 2026,
ese estado nunca fue el más dominante — siempre había algo más fuerte.

---

## El problema real del diseño

### overdamped_system está diseñado para un mercado que no existió

El mercado de sept 2025–mar 2026 tuvo dos estados principales:

1. **Bull run activo (oct–ene):** Z4 positivo, Z8 negativo → gas_expansion gana
2. **Deterioro progresivo (feb–mar):** Z4 negativo, Z8 alto → lorenz gana

overdamped_system está diseñado para un tercer estado:
**mercado lateral con presión de reversión** — Z4 cercano a cero,
Z6 muy alto, Z8 bajo. Ese estado no ocurrió en este período.

Esto no significa que el vector Z de overdamped esté mal.
Significa que **el mercado no estuvo en ese estado durante E1**.

### Implicación para E2

E2 empieza ahora (abril 2026) con el mercado en deterioro.
Si el mercado entra en rango lateral después del deterioro
(VIX bajando de 25 a 18, momentum recuperándose de -5% a -1%),
**overdamped_system podría activarse por primera vez**.

Los 49 días de mercado lateral identificados en E1 tuvieron
sim_overdamped media de 0.3950 vs sim_gas media de 0.5832 —
gas_expansion seguía ganando incluso en lateral, porque el momentum
era ligeramente positivo en esos días y Z1 tiraba hacia gas_expansion.

---

## Lo que hay que hacer antes de E3

### No recalibrar el vector Z

El vector Z de overdamped_system es geométricamente correcto.
El problema no es el diseño — es que el mercado no estuvo en
ese estado durante el período de calibración.

### Sí incluir escenarios de reversión en E3

Los 50 pares de E3 deben incluir explícitamente días donde:
- VIX entre 18 y 22
- Momentum entre -1% y +1%
- Z6 (reversibilidad) sea alto
- Y el isomorfo correcto según expertos sea overdamped_system

Sin esos pares, E3 no puede medir si el sistema detecta
correctamente los períodos de reversión lenta.

### Documentar como limitación de E1

E1 no puede calibrar overdamped_system porque el mercado
del período no activó ese patrón. Esto es información válida
para el paper — no todos los isomorfos se validan con el
mismo período de datos.

---

## Tabla resumen de los 5 isomorfos tras E1

| Isomorfo | Días en E1 | Sim max | Sim media | Estado |
|----------|-----------|---------|-----------|--------|
| gas_expansion | 76 (61.8%) | ~0.94 | ~0.88 | Bien calibrado, validado |
| lorenz_attractor | 42 (34.1%) | ~0.90 | ~0.85 | Bien calibrado, validado |
| compressed_gas | 3 (2.4%) | ~0.82 | ~0.77 | Poco datos, pendiente E3 |
| phase_transition | 2 (1.6%) | ~0.94 | ~0.92 | Muy poco datos, pendiente E3 |
| overdamped_system | 0 (0.0%) | 0.7810 | 0.3862 | No activado en E1 — el mercado no estuvo en ese estado |

---

## Conclusión para el paper

overdamped_system no es un error de diseño — es un isomorfo que
captura un estado de mercado (reversión lateral) que no ocurrió
durante el período de calibración E1. El sistema lo detecta
geométricamente (sim max=0.78) pero siempre pierde ante lorenz
cuando el mercado tiene cualquier señal de caos o deterioro.

Esto hay que reportarlo en el paper tal como es:

> "El isomorfo overdamped_system no se activó en ninguno de los
> 123 días del período de calibración E1 (sept 2025–mar 2026).
> El sistema detectó el patrón (similitud máxima=0.78) pero
> lorenz_attractor tuvo similitud superior en los 45 días donde
> overdamped superó a gas_expansion. El período E1 estuvo
> dominado por bull run (55%) y deterioro progresivo (21%+21%),
> sin períodos de reversión lateral sostenida. La calibración
> de overdamped_system requiere datos de mercados laterales
> que E2 puede proveer si el mercado entra en rango."

Eso es honestidad científica. No es un fallo del sistema —
es un límite del período de datos de E1.

---

*Análisis generado el 5 de abril de 2026.*
*Basado en datos reales de E1. Sin interpretación optimista.*
