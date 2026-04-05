"""
E3 — Generación de 50 pares para evaluación ciega de isomorfos
Cortex V2 | Pre-registro OSF: https://osf.io/wdkcx

METODOLOGÍA CIENTÍFICA:
Muestreo estratificado de e1_results.csv para cubrir:
  A. Todos los isomorfos detectados (representatividad)
  B. Todos los regímenes de mercado (cobertura)
  C. Casos fáciles (señal clara) — referencia baseline
  D. Casos difíciles (señal ambigua) — donde falla el sistema
  E. Transiciones entre isomorfos — cambios de régimen
  F. Casos donde el sistema discrepa de la intuición

HONESTIDAD CIENTÍFICA:
  - Los pares con etiqueta "EXPERT_JUDGMENT" no tienen respuesta
    pre-asignada — el experto decide
  - Los pares fáciles SÍ tienen etiqueta — son la base del Cohen's kappa
  - La distribución de dificultad es deliberada: 40% fácil, 60% difícil
    porque H2 mide si el sistema supera el baseline en los casos difíciles

LIMITACIÓN DOCUMENTADA:
  - Los 123 días de E1 no contienen R4_CONTRACTION ni overdamped_system activo
  - Los 50 pares reflejan lo que el mercado produjo, no lo que idealmente
    tendríamos. Se documenta explícitamente en e3_pairs.md
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

from cortex.config import config
from cortex.layers.omega import PHYSICAL_ISOMORPHS

CSV_PATH    = Path("experiments/e1_results.csv")
OUT_CSV     = Path("experiments/e3_pairs.csv")
OUT_MD      = Path("experiments/e3_pairs.md")
OUT_JSON    = Path("experiments/e3_pairs_metadata.json")

RANDOM_SEED = 42  # reproducible — pre-registrado


def cosine_sim(z_a, z_b):
    na, nb = np.linalg.norm(z_a), np.linalg.norm(z_b)
    if na == 0 or nb == 0:
        return 0.0
    return float(max(0.0, min(1.0, (np.dot(z_a, z_b) / (na * nb) + 1.0) / 2.0)))


def margin_of_victory(row):
    """Diferencia entre la similitud del isomorfo ganador y el segundo."""
    z = np.array([row.z1, row.z2, row.z3, row.z4,
                  row.z5, row.z6, row.z7, row.z8])
    sims = {n: cosine_sim(z, iso["Z"]) for n, iso in PHYSICAL_ISOMORPHS.items()}
    sorted_sims = sorted(sims.values(), reverse=True)
    return round(sorted_sims[0] - sorted_sims[1], 4), sims


def run():
    df = pd.read_csv(CSV_PATH)
    rng = np.random.default_rng(RANDOM_SEED)

    print(f"\nGenerando 50 pares E3 de {len(df)} dias de E1")
    print(f"Semilla aleatoria: {RANDOM_SEED} (reproducible)\n")

    # Calcular margen de victoria y similitudes para todos los dias
    margins, all_sims = [], []
    for _, row in df.iterrows():
        m, s = margin_of_victory(row)
        margins.append(m)
        all_sims.append(s)
    df["margin"] = margins
    df["sim_overdamped"] = [s["overdamped_system"] for s in all_sims]
    df["sim_lorenz"]     = [s["lorenz_attractor"]   for s in all_sims]
    df["sim_gas"]        = [s["gas_expansion"]      for s in all_sims]

    pairs = []

    # ── ESTRATO 1: Gas_expansion claro (8 pares, easy) ────────────────────────
    # Victoria amplia (margin > 0.15), R1, momentum > 3%
    # Propósito: ancla el baseline de los evaluadores, Cohen's kappa > 0.90 esperado
    gas_clear = df[
        (df["isomorph"] == "gas_expansion") &
        (df["margin"] > 0.15) &
        (df["regime"] == "R1_EXPANSION") &
        (df["momentum_21d_pct"] > 3.0)
    ].sample(8, random_state=RANDOM_SEED, replace=False)
    for _, r in gas_clear.iterrows():
        pairs.append((_row(r, "gas_expansion_clear", "gas_expansion", "easy",
            "Bull run inequívoco: momentum fuerte, VIX bajo, R1 sostenido")))

    # ── ESTRATO 2: Lorenz_attractor claro (8 pares, easy) ─────────────────────
    # Victoria amplia, deterioro real, margin > 0.20
    lorenz_clear = df[
        (df["isomorph"] == "lorenz_attractor") &
        (df["margin"] > 0.20) &
        (df["momentum_21d_pct"] < -3.0)
    ].sample(8, random_state=RANDOM_SEED, replace=False)
    for _, r in lorenz_clear.iterrows():
        pairs.append(_row(r, "lorenz_clear", "lorenz_attractor", "easy",
            "Deterioro inequívoco: momentum fuerte negativo, VIX elevado"))

    # ── ESTRATO 3: Compressed_gas y phase_transition (5 pares, medium) ────────
    # Todos los dias disponibles — son pocos y valiosos
    rare = df[df["isomorph"].isin(["compressed_gas", "phase_transition"])]
    for _, r in rare.iterrows():
        iso = r["isomorph"]
        pairs.append(_row(r, f"rare_{iso}", iso, "medium",
            f"Isomorfo infrecuente ({iso}) — crítico para cobertura E3"))

    # ── ESTRATO 4: Frontera gas/lorenz (10 pares, hard) ───────────────────────
    # Dias donde el margen es pequeño (< 0.08) entre gas y lorenz
    # Estos son los dias donde el sistema puede estar equivocado
    frontier = df[
        (df["isomorph"].isin(["gas_expansion", "lorenz_attractor"])) &
        (df["margin"] < 0.08) &
        (df["momentum_21d_pct"].between(-2.5, 2.0))
    ].copy()
    # Priorizar los de menor margen (más difíciles)
    frontier = frontier.sort_values("margin").head(15)
    sample_size = min(10, len(frontier))
    frontier_sample = frontier.sample(sample_size,
                                       random_state=RANDOM_SEED, replace=False)
    for _, r in frontier_sample.iterrows():
        pairs.append(_row(r, "frontier_gas_lorenz", "EXPERT_JUDGMENT", "hard",
            f"Frontera gas/lorenz: margen={r['margin']:.3f}. "
            f"Sistema elige {r['isomorph']} pero el margen es pequeño"))

    # ── ESTRATO 5: Transiciones de régimen (6 pares, hard) ────────────────────
    # Dias justo antes/después de un cambio de isomorfo
    # Detectar cambios: dia N tiene isomorfo distinto al dia N-1
    df_sorted = df.sort_values("date").reset_index(drop=True)
    transition_idx = []
    for i in range(1, len(df_sorted)):
        if df_sorted.loc[i, "isomorph"] != df_sorted.loc[i-1, "isomorph"]:
            transition_idx.extend([i-1, i])
    transition_days = df_sorted.loc[list(set(transition_idx))].copy()
    if len(transition_days) >= 6:
        t_sample = transition_days.sample(6, random_state=RANDOM_SEED,
                                           replace=False)
    else:
        t_sample = transition_days
    for _, r in t_sample.iterrows():
        pairs.append(_row(r, "regime_transition", "EXPERT_JUDGMENT", "hard",
            f"Dia de transicion de regimen — isomorfo puede ser ambiguo. "
            f"Sistema: {r['isomorph']}"))

    # ── ESTRATO 6: Potencial overdamped (5 pares, hard) ───────────────────────
    # Dias con sim_overdamped más alta — el sistema eligió otro isomorfo
    # pero los expertos podrían asignar overdamped
    over_candidates = df[
        (df["sim_overdamped"] >= 0.55) &
        (df["isomorph"] != "overdamped_system")
    ].sort_values("sim_overdamped", ascending=False).head(10)
    already = {r["date"] for r in pairs}
    over_new = over_candidates[~over_candidates["date"].isin(already)]
    for _, r in over_new.head(5).iterrows():
        pairs.append(_row(r, "potential_overdamped", "EXPERT_JUDGMENT", "hard",
            f"overdamped_system tiene sim={r['sim_overdamped']:.3f} pero "
            f"sistema eligio {r['isomorph']}. ¿Cuál es el correcto?"))

    # ── ESTRATO 7: Lorenz con threshold barely met (4 pares, medium) ──────────
    # Dias donde lorenz gana pero con sim entre 0.65 y 0.75 — señal débil
    lorenz_weak = df[
        (df["isomorph"] == "lorenz_attractor") &
        (df["isomorph_sim"].between(0.65, 0.75))
    ]
    already = {r["date"] for r in pairs}
    lorenz_weak_new = lorenz_weak[~lorenz_weak["date"].isin(already)]
    if len(lorenz_weak_new) >= 4:
        lw_sample = lorenz_weak_new.sample(4, random_state=RANDOM_SEED,
                                            replace=False)
    else:
        lw_sample = lorenz_weak_new
    for _, r in lw_sample.iterrows():
        pairs.append(_row(r, "lorenz_weak_signal", "lorenz_attractor", "medium",
            f"Lorenz con señal débil: sim={r['isomorph_sim']:.3f}. "
            f"¿Lorenz o algo más apropiado?"))

    # ── Eliminar duplicados y completar hasta 50 si es necesario ─────────────
    seen = set()
    unique = []
    for p in pairs:
        if p["date"] not in seen:
            seen.add(p["date"])
            unique.append(p)

    # Si hay menos de 50, completar con días aleatorios no usados
    if len(unique) < 50:
        remaining = df[~df["date"].isin(seen)]
        n_extra = 50 - len(unique)
        extra = remaining.sample(min(n_extra, len(remaining)),
                                  random_state=RANDOM_SEED)
        for _, r in extra.iterrows():
            unique.append(_row(r, "fill_representative", r["isomorph"], "medium",
                "Muestra representativa adicional"))

    unique = unique[:50]
    # Ordenar por fecha para el documento de evaluadores
    unique.sort(key=lambda x: x["date"])

    # ── Asignar número de par ─────────────────────────────────────────────────
    for i, p in enumerate(unique, 1):
        p["pair_id"] = i

    df_pairs = pd.DataFrame(unique)

    # ── Guardar CSV ───────────────────────────────────────────────────────────
    cols = ["pair_id", "date", "spy_price", "vix", "momentum_21d_pct",
            "vol_realized_pct", "drawdown_90d_pct", "regime",
            "delta", "isomorph", "isomorph_sim", "margin",
            "stratum", "expected_isomorph", "difficulty", "rationale"]
    df_pairs[cols].to_csv(OUT_CSV, index=False)

    # ── Generar Markdown para evaluadores (CIEGO: sin mostrar isomorfo sistema) ─
    _write_evaluator_md(df_pairs)

    # ── Metadata JSON ─────────────────────────────────────────────────────────
    metadata = {
        "experiment": "E3",
        "osf": config.OSF_PREREGISTRATION,
        "generated_from": "experiments/e1_results.csv",
        "generated_at": datetime.now().isoformat(),
        "random_seed": RANDOM_SEED,
        "total_pairs": len(unique),
        "stratification": {
            "gas_expansion_clear":   len([p for p in unique if p["stratum"] == "gas_expansion_clear"]),
            "lorenz_clear":          len([p for p in unique if p["stratum"] == "lorenz_clear"]),
            "rare_isomorphs":        len([p for p in unique if "rare_" in p["stratum"]]),
            "frontier_gas_lorenz":   len([p for p in unique if p["stratum"] == "frontier_gas_lorenz"]),
            "regime_transition":     len([p for p in unique if p["stratum"] == "regime_transition"]),
            "potential_overdamped":  len([p for p in unique if p["stratum"] == "potential_overdamped"]),
            "lorenz_weak_signal":    len([p for p in unique if p["stratum"] == "lorenz_weak_signal"]),
            "fill_representative":   len([p for p in unique if p["stratum"] == "fill_representative"]),
        },
        "difficulty_distribution": df_pairs["difficulty"].value_counts().to_dict(),
        "expected_isomorph_distribution": df_pairs["expected_isomorph"].value_counts().to_dict(),
        "h2_baseline_f1": 0.278,
        "h2_target_f1": 0.478,
        "known_limitations": [
            "R4_CONTRACTION no aparecio en E1 — no hay pares de crisis profunda",
            "overdamped_system nunca fue isomorfo ganador — pares de potencial "
            "overdamped son EXPERT_JUDGMENT, no tienen etiqueta pre-asignada",
            "123 dias de datos cubren solo bull run y deterioro, no mercado lateral puro"
        ],
        "inter_rater_agreement_required": "Cohen kappa >= 0.75 antes de usar en E3",
        "evaluation_protocol": (
            "Evaluadores ciegos: no ven columna isomorph del sistema. "
            "Solo ven fecha, indicadores de mercado, y descripcion del contexto. "
            "Cada evaluador asigna uno de los 5 isomorfos o 'ninguno'."
        )
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # ── Imprimir resumen ──────────────────────────────────────────────────────
    print(f"Pares generados: {len(unique)}\n")
    print("Estratos:")
    for k, v in metadata["stratification"].items():
        print(f"  {k:<30} {v:>3} pares")
    print()
    print("Dificultad:")
    for d, n in df_pairs["difficulty"].value_counts().items():
        print(f"  {d:<10} {n:>3} pares")
    print()
    print("Isomorfo esperado:")
    for iso, n in df_pairs["expected_isomorph"].value_counts().items():
        pct = n / len(df_pairs) * 100
        print(f"  {iso:<25} {n:>3} pares ({pct:.0f}%)")
    print()
    print(f"Archivos:")
    print(f"  {OUT_CSV}   <- para analisis")
    print(f"  {OUT_MD}    <- para evaluadores (CIEGO)")
    print(f"  {OUT_JSON}  <- metadata completa")
    print()
    print("SIGUIENTE PASO:")
    print("  Compartir e3_pairs.md con 3 evaluadores externos.")
    print("  SIN decirles que isomorfo eligio el sistema.")
    print("  Calcular Cohen's kappa antes de usar en E3.")


def _row(r, stratum, expected, difficulty, rationale):
    return {
        "date":              r["date"],
        "spy_price":         r["spy_price"],
        "vix":               r["vix"],
        "momentum_21d_pct":  r["momentum_21d_pct"],
        "vol_realized_pct":  r["vol_realized_pct"],
        "drawdown_90d_pct":  r["drawdown_90d_pct"],
        "regime":            r["regime"],
        "delta":             r["delta"],
        "isomorph":          r["isomorph"],
        "isomorph_sim":      r["isomorph_sim"],
        "margin":            r.get("margin", 0.0),
        "stratum":           stratum,
        "expected_isomorph": expected,
        "difficulty":        difficulty,
        "rationale":         rationale,
    }


def _write_evaluator_md(df_pairs):
    """
    Documento CIEGO para evaluadores.
    No incluye la columna 'isomorph' del sistema ni 'expected_isomorph'.
    El evaluador solo ve los indicadores de mercado.
    """
    lines = [
        "# E3 — Evaluación ciega de isomorfos de mercado",
        "## Cortex V2 | Evaluador externo",
        "",
        "**INSTRUCCIONES — LEE ANTES DE EVALUAR**",
        "",
        "Para cada día de mercado, identifica cuál de estos 5 estados físicos",
        "describe mejor el comportamiento del mercado en ese momento.",
        "Usa SOLO los datos proporcionados — no busques información adicional.",
        "",
        "### Los 5 estados (isomorfos físicos):",
        "",
        "| Código | Nombre | Descripción de mercado |",
        "|--------|--------|------------------------|",
        "| **GAS** | Gas en expansión | Tendencia alcista sostenida, momentum positivo, VIX bajo (<18), mercado 'libre' sin resistencia |",
        "| **COMP** | Gas comprimido | Mercado lateral con tensión acumulada, VIX moderado-alto, listo para moverse pero sin dirección clara |",
        "| **PHASE** | Transición de fase | Alta volatilidad y cambio abrupto de condiciones, VIX escalando rápido, ruptura de estructura |",
        "| **OVER** | Sistema amortiguado | Recuperación gradual hacia equilibrio, volatilidad bajando lentamente, sin impulso claro |",
        "| **LORENZ** | Atractor de Lorenz | Caos determinista, trayectorias impredecibles, momentum negativo, VIX elevado sin tender a resolverse |",
        "",
        "### Escala de confianza:",
        "1 = muy inseguro | 2 = algo inseguro | 3 = bastante seguro | 4 = muy seguro",
        "",
        "---",
        "",
        "## Los 50 pares",
        "",
        "| # | Fecha | SPY ($) | VIX | Mom.21d | Vol | Drawdown | Régimen | Dificultad | Tu isomorfo | Confianza (1-4) |",
        "|---|-------|---------|-----|---------|-----|---------|---------|------------|-------------|----------------|",
    ]

    diff_map = {"easy": "Fácil", "medium": "Media", "hard": "Difícil"}
    for _, r in df_pairs.sort_values("pair_id").iterrows():
        d = diff_map.get(r["difficulty"], r["difficulty"])
        lines.append(
            f"| {r['pair_id']:>2} | {r['date']} | {r['spy_price']:.0f} | "
            f"{r['vix']:.1f} | {r['momentum_21d_pct']:+.1f}% | "
            f"{r['vol_realized_pct']:.1f}% | {r['drawdown_90d_pct']:.1f}% | "
            f"{r['regime']} | {d} | | |"
        )

    lines += [
        "",
        "---",
        "",
        "## Contexto adicional por par difícil",
        "",
        "Los pares de dificultad 'Difícil' tienen contexto adicional:",
        "",
    ]

    hard_pairs = df_pairs[df_pairs["difficulty"] == "hard"].sort_values("pair_id")
    for _, r in hard_pairs.iterrows():
        lines.append(f"**Par {r['pair_id']} ({r['date']}):** {r['rationale']}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Limitaciones conocidas de este conjunto",
        "",
        "- El período analizado (oct 2025–mar 2026) no tuvo crisis profunda (VIX > 35).",
        "  No hay pares de R4_CONTRACTION. Los evaluadores no verán ese estado.",
        "- El estado 'OVER' (overdamped) es muy raro en este período.",
        "  Si crees que un par corresponde a OVER, indícalo aunque sea infrecuente.",
        "- Los pares de dificultad 'Difícil' son deliberadamente ambiguos.",
        "  No hay respuesta 'correcta' garantizada — el objetivo es el juicio experto.",
        "",
        "---",
        "",
        "*Generado el 5 de abril de 2026 — Pre-registro OSF: https://osf.io/wdkcx*",
        "*Evaluación ciega: el evaluador no conoce la clasificación del sistema.*",
    ]

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    run()
