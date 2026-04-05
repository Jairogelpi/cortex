"""
E3 — Generación de 50 pares para evaluación ciega de isomorfos
Cortex V2 | Pre-registro OSF: https://osf.io/wdkcx
Semilla: 42 (reproducible, pre-registrable)
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
RANDOM_SEED = 42


def cosine_sim(z_a, z_b):
    na, nb = np.linalg.norm(z_a), np.linalg.norm(z_b)
    if na == 0 or nb == 0:
        return 0.0
    return float(max(0.0, min(1.0, (np.dot(z_a, z_b) / (na * nb) + 1.0) / 2.0)))


def enrich(df):
    """Añade columnas derivadas necesarias para la selección."""
    z_cols = ["z1","z2","z3","z4","z5","z6","z7","z8"]
    margins, sim_over, sim_gas, sim_lorenz = [], [], [], []
    for _, row in df.iterrows():
        z = np.array([row[c] for c in z_cols])
        sims = {n: cosine_sim(z, iso["Z"]) for n, iso in PHYSICAL_ISOMORPHS.items()}
        sv   = sorted(sims.values(), reverse=True)
        margins.append(round(sv[0] - sv[1], 4))
        sim_over.append(sims["overdamped_system"])
        sim_gas.append(sims["gas_expansion"])
        sim_lorenz.append(sims["lorenz_attractor"])
    df = df.copy()
    df["margin"]       = margins
    df["sim_overdamped"] = sim_over
    df["sim_gas"]       = sim_gas
    df["sim_lorenz"]    = sim_lorenz
    return df


def safe_sample(df_sub, n, seed):
    """Sample n rows sin romper si hay menos de n."""
    n = min(n, len(df_sub))
    if n == 0:
        return pd.DataFrame()
    return df_sub.sample(n, random_state=seed, replace=False)


def row_to_pair(r, stratum, expected, difficulty, rationale):
    return {
        "date":             r["date"],
        "spy_price":        r["spy_price"],
        "vix":              r["vix"],
        "momentum_21d_pct": r["momentum_21d_pct"],
        "vol_realized_pct": r["vol_realized_pct"],
        "drawdown_90d_pct": r["drawdown_90d_pct"],
        "regime":           r["regime"],
        "delta":            r["delta"],
        "isomorph":         r["isomorph"],     # isomorfo del sistema (NO mostrar al evaluador)
        "isomorph_sim":     r["isomorph_sim"],
        "margin":           r.get("margin", 0.0),
        "stratum":          stratum,
        "expected_isomorph":expected,          # etiqueta científica
        "difficulty":       difficulty,
        "rationale":        rationale,
    }


def run():
    df_raw = pd.read_csv(CSV_PATH)
    df     = enrich(df_raw)

    print(f"Generando 50 pares E3 de {len(df)} dias | semilla={RANDOM_SEED}\n")
    print("Distribución de margenes:")
    print(f"  media={df['margin'].mean():.3f}  min={df['margin'].min():.3f}  "
          f"max={df['margin'].max():.3f}\n")

    pairs = []

    # ── E1: Gas_expansion inequívoco (8 pares, easy) ──────────────────────────
    # Días de bull run real. Umbral de margin reducido a 0.05 (datos deterministas)
    e1 = df[(df["isomorph"]=="gas_expansion") &
            (df["regime"]=="R1_EXPANSION") &
            (df["momentum_21d_pct"]>3.0)]
    print(f"Estrato 1 (gas claro):   {len(e1)} candidatos")
    for _, r in safe_sample(e1, 8, RANDOM_SEED).iterrows():
        pairs.append(row_to_pair(r, "gas_clear", "gas_expansion", "easy",
            "Bull run inequivoco: R1_EXPANSION, momentum>3%, VIX bajo"))

    # ── E2: Lorenz_attractor inequívoco (8 pares, easy) ───────────────────────
    e2 = df[(df["isomorph"]=="lorenz_attractor") &
            (df["momentum_21d_pct"]<-3.0) &
            (df["isomorph_sim"]>=0.85)]
    print(f"Estrato 2 (lorenz claro): {len(e2)} candidatos")
    for _, r in safe_sample(e2, 8, RANDOM_SEED).iterrows():
        pairs.append(row_to_pair(r, "lorenz_clear", "lorenz_attractor", "easy",
            "Caos inequivoco: momentum<-3%, VIX elevado, sim_lorenz>0.85"))

    # ── E3: Isomorfos raros — todos los disponibles (5 pares, medium) ─────────
    e3 = df[df["isomorph"].isin(["compressed_gas","phase_transition"])]
    print(f"Estrato 3 (raros):        {len(e3)} candidatos")
    for _, r in e3.iterrows():
        pairs.append(row_to_pair(r, f"rare_{r['isomorph']}", r["isomorph"],
            "medium", f"Isomorfo infrecuente ({r['isomorph']}) — todos incluidos"))

    # ── E4: Frontera ambigua gas/lorenz (10 pares, hard) ──────────────────────
    seen = {p["date"] for p in pairs}
    e4 = df[(df["isomorph"].isin(["gas_expansion","lorenz_attractor"])) &
            (df["momentum_21d_pct"].between(-2.5, 2.0)) &
            (~df["date"].isin(seen))].sort_values("margin")
    print(f"Estrato 4 (frontera):     {len(e4)} candidatos")
    for _, r in safe_sample(e4.head(20), 10, RANDOM_SEED).iterrows():
        pairs.append(row_to_pair(r, "frontier_ambiguous", "EXPERT_JUDGMENT", "hard",
            f"Frontera gas/lorenz: mom={r['momentum_21d_pct']:+.1f}%, "
            f"margen={r['margin']:.3f}. Sistema: {r['isomorph']}"))

    # ── E5: Transiciones de régimen (6 pares, hard) ───────────────────────────
    seen = {p["date"] for p in pairs}
    ds = df.sort_values("date").reset_index(drop=True)
    t_idx = set()
    for i in range(1, len(ds)):
        if ds.loc[i,"isomorph"] != ds.loc[i-1,"isomorph"]:
            t_idx.update([i-1, i])
    t_days = ds.loc[list(t_idx)].copy()
    t_days = t_days[~t_days["date"].isin(seen)]
    print(f"Estrato 5 (transiciones): {len(t_days)} candidatos")
    for _, r in safe_sample(t_days, 6, RANDOM_SEED).iterrows():
        pairs.append(row_to_pair(r, "regime_transition", "EXPERT_JUDGMENT", "hard",
            f"Dia de transicion de regimen. Sistema: {r['isomorph']}"))

    # ── E6: Potencial overdamped (5 pares, hard) ──────────────────────────────
    seen = {p["date"] for p in pairs}
    e6 = df[(df["sim_overdamped"]>=0.55) &
            (df["isomorph"]!="overdamped_system") &
            (~df["date"].isin(seen))].sort_values("sim_overdamped", ascending=False)
    print(f"Estrato 6 (overdamped?):  {len(e6)} candidatos")
    for _, r in safe_sample(e6, 5, RANDOM_SEED).iterrows():
        pairs.append(row_to_pair(r, "potential_overdamped", "EXPERT_JUDGMENT", "hard",
            f"overdamped_system tiene sim={r['sim_overdamped']:.3f}. "
            f"Sistema elige {r['isomorph']}. ¿Cual es el correcto?"))

    # ── E7: Lorenz con señal débil (4 pares, medium) ──────────────────────────
    seen = {p["date"] for p in pairs}
    e7 = df[(df["isomorph"]=="lorenz_attractor") &
            (df["isomorph_sim"].between(0.65, 0.75)) &
            (~df["date"].isin(seen))]
    print(f"Estrato 7 (lorenz débil): {len(e7)} candidatos")
    for _, r in safe_sample(e7, 4, RANDOM_SEED).iterrows():
        pairs.append(row_to_pair(r, "lorenz_weak", "lorenz_attractor", "medium",
            f"Lorenz con señal débil: sim={r['isomorph_sim']:.3f} (cerca del umbral 0.65)"))

    # ── Completar hasta 50 si es necesario ────────────────────────────────────
    seen = {p["date"] for p in pairs}
    if len(pairs) < 50:
        rest = df[~df["date"].isin(seen)]
        n_extra = 50 - len(pairs)
        for _, r in safe_sample(rest, n_extra, RANDOM_SEED).iterrows():
            pairs.append(row_to_pair(r, "fill", r["isomorph"], "medium",
                "Muestra representativa adicional"))

    # Eliminar duplicados y ordenar por fecha
    seen2, unique = set(), []
    for p in pairs:
        if p["date"] not in seen2:
            seen2.add(p["date"])
            unique.append(p)
    unique = unique[:50]
    unique.sort(key=lambda x: x["date"])
    for i, p in enumerate(unique, 1):
        p["pair_id"] = i

    # ── Guardar CSV completo ───────────────────────────────────────────────────
    df_pairs = pd.DataFrame(unique)
    cols = ["pair_id","date","spy_price","vix","momentum_21d_pct",
            "vol_realized_pct","drawdown_90d_pct","regime",
            "delta","isomorph","isomorph_sim","margin",
            "stratum","expected_isomorph","difficulty","rationale"]
    df_pairs[cols].to_csv(OUT_CSV, index=False)

    # ── Generar MD ciego para evaluadores ─────────────────────────────────────
    _write_evaluator_md(df_pairs)

    # ── Metadata ───────────────────────────────────────────────────────────────
    strata_counts = df_pairs["stratum"].value_counts().to_dict()
    diff_counts   = df_pairs["difficulty"].value_counts().to_dict()
    exp_counts    = df_pairs["expected_isomorph"].value_counts().to_dict()

    metadata = {
        "experiment":       "E3",
        "osf":              config.OSF_PREREGISTRATION,
        "generated_from":   "experiments/e1_results.csv",
        "generated_at":     datetime.now().isoformat(),
        "random_seed":      RANDOM_SEED,
        "total_pairs":      len(unique),
        "stratification":   strata_counts,
        "difficulty":       diff_counts,
        "expected_isomorph":exp_counts,
        "date_range":       f"{df_pairs['date'].min()} to {df_pairs['date'].max()}",
        "h2_baseline_f1":   0.278,
        "h2_target_f1":     0.478,
        "known_limitations": [
            "R4_CONTRACTION no aparecio en E1 — sin pares de crisis profunda (VIX>35)",
            "overdamped_system nunca fue isomorfo ganador — pares son EXPERT_JUDGMENT",
            "Phi deterministico produce Z comprimidos — margenes menores que en produccion"
        ],
        "inter_rater_agreement_required": "Cohen kappa >= 0.75",
        "protocol": (
            "Evaluadores ciegos: no ven columna isomorph del sistema. "
            "Asignan uno de los 5 isomorfos o 'ninguno'. "
            "Escala de confianza 1-4 por par."
        )
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # ── Resumen ────────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  E3 COMPLETADO: {len(unique)} pares")
    print(f"{'='*60}")
    print(f"\nEstratos:")
    for k, v in strata_counts.items():
        print(f"  {k:<30} {v:>3}")
    print(f"\nDificultad:")
    for d, n in diff_counts.items():
        print(f"  {d:<12} {n:>3} ({n/len(unique)*100:.0f}%)")
    print(f"\nIsomorfo esperado:")
    for iso, n in sorted(exp_counts.items(), key=lambda x: -x[1]):
        print(f"  {iso:<25} {n:>3}")
    print(f"\nArchivos:")
    print(f"  {OUT_CSV}")
    print(f"  {OUT_MD}   <- ESTE es el que compartes con evaluadores")
    print(f"  {OUT_JSON}")
    print(f"\nLIMITACIONES DOCUMENTADAS:")
    for lim in metadata["known_limitations"]:
        print(f"  - {lim}")
    print()


def _write_evaluator_md(df_pairs):
    lines = [
        "# E3 — Evaluación ciega de isomorfos de mercado",
        "## Cortex V2 | Evaluador externo",
        "### Pre-registro OSF: https://osf.io/wdkcx",
        "",
        "---",
        "",
        "## INSTRUCCIONES",
        "",
        "Para cada día de mercado, identifica cuál de los 5 estados físicos",
        "describe mejor el comportamiento del mercado en ese momento.",
        "**Usa solo los datos de la tabla** — no busques información adicional.",
        "**No uses el retorno futuro** — evalúa el estado presente del mercado.",
        "",
        "### Los 5 isomorfos físicos:",
        "",
        "| Código | Estado del mercado |",
        "|--------|--------------------|",
        "| **GAS_EXP** | Bull run sostenido: tendencia alcista clara, VIX < 18, momentum positivo fuerte, mercado 'libre' |",
        "| **COMP_GAS** | Acumulación pre-rally: mercado lateral-alcista, VIX moderado-alto, tensión acumulada esperando ruptura |",
        "| **PHASE** | Transición de régimen: alta volatilidad, VIX escalando, cambio estructural en curso, ruptura de tendencia |",
        "| **OVER_DAMP** | Amortiguamiento lento: recuperación gradual sin impulso, VIX bajando lentamente, regreso al equilibrio |",
        "| **LORENZ** | Caos determinista: trayectorias impredecibles, momentum negativo, VIX elevado sin resolución clara |",
        "",
        "### Escala de confianza:",
        "- **1** = muy inseguro (podría ser otro isomorfo)",
        "- **2** = algo inseguro",
        "- **3** = bastante seguro",
        "- **4** = muy seguro (señal inequívoca)",
        "",
        "---",
        "",
        "## Los 50 pares de evaluación",
        "",
        "| # | Fecha | SPY ($) | VIX | Mom.21d | Vol.real | Drawdown | Régimen detectado | Dificultad | Tu isomorfo | Confianza |",
        "|---|-------|---------|-----|---------|----------|---------|-------------------|------------|-------------|-----------|",
    ]

    diff_es = {"easy": "Fácil", "medium": "Media", "hard": "Difícil"}
    for _, r in df_pairs.sort_values("pair_id").iterrows():
        d = diff_es.get(r["difficulty"], r["difficulty"])
        lines.append(
            f"| {int(r['pair_id']):>2} | {r['date']} | "
            f"{r['spy_price']:.0f} | {r['vix']:.1f} | "
            f"{r['momentum_21d_pct']:+.1f}% | {r['vol_realized_pct']:.1f}% | "
            f"{r['drawdown_90d_pct']:.1f}% | {r['regime']} | {d} | | |"
        )

    lines += [
        "",
        "---",
        "",
        "## Contexto adicional — pares difíciles",
        "",
        "Para los pares de dificultad 'Difícil', información contextual adicional:",
        "",
    ]
    for _, r in df_pairs[df_pairs["difficulty"]=="hard"].sort_values("pair_id").iterrows():
        lines.append(f"**Par {int(r['pair_id'])} ({r['date']}):** {r['rationale']}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Limitaciones de este conjunto de datos",
        "",
        "- El período analizado (oct 2025 – mar 2026) no incluyó crisis profunda (VIX > 35).",
        "  No hay pares del estado R4_CONTRACTION.",
        "- El estado OVER_DAMP (sistema amortiguado) es muy infrecuente en este período.",
        "  Si crees que algún par corresponde a ese estado, indícalo aunque sea raro.",
        "- Los pares 'Difícil' son deliberadamente ambiguos — no hay respuesta única garantizada.",
        "",
        "---",
        "",
        "*Generado el 5 de abril de 2026 con semilla aleatoria 42 (reproducible).*",
        "*Evaluación ciega: el evaluador no conoce la clasificación del sistema.*",
    ]

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    run()
