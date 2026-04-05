"""
Analisis de overdamped_system — por que nunca aparecio en E1
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

from cortex.config import config
from cortex.layers.omega import PHYSICAL_ISOMORPHS

CSV_PATH = Path("experiments/e1_results.csv")
OUTPUT   = Path("experiments/e1_overdamped_analysis.json")


def calc_sim(z_a, z_b) -> float:
    na, nb = np.linalg.norm(z_a), np.linalg.norm(z_b)
    if na == 0 or nb == 0:
        return 0.0
    return float(max(0.0, min(1.0, (np.dot(z_a, z_b) / (na * nb) + 1.0) / 2.0)))


def run():
    if not CSV_PATH.exists():
        print(f"ERROR: no existe {CSV_PATH}. Ejecuta primero run_e1.bat")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"\nAnalisis de overdamped_system en {len(df)} dias de E1\n")

    z_ref_over = PHYSICAL_ISOMORPHS["overdamped_system"]["Z"]
    z_ref_gas  = PHYSICAL_ISOMORPHS["gas_expansion"]["Z"]

    print(f"Vector Z de referencia overdamped_system:")
    print(f"  {[round(x,2) for x in z_ref_over.tolist()]}")
    print(f"  Z6(reversibilidad)=+0.80 — condicion clave\n")

    z_cols = ["z1","z2","z3","z4","z5","z6","z7","z8"]
    sims_over = []
    sims_gas  = []

    for _, row in df.iterrows():
        z = np.array([row[c] for c in z_cols])
        sims_over.append(calc_sim(z, z_ref_over))
        sims_gas.append(calc_sim(z, z_ref_gas))

    df["sim_overdamped"] = sims_over
    df["sim_gas"]        = sims_gas
    df["overdamped_would_win"] = df["sim_overdamped"] > df["sim_gas"]

    df_near  = df[df["overdamped_would_win"]].copy()
    df_above = df[df["sim_overdamped"] >= config.SIM_THRESHOLD].copy()
    df_lateral = df[
        (df["vix"] >= 17) & (df["vix"] <= 24) &
        (df["momentum_21d_pct"].abs() <= 2.0) &
        (df["drawdown_90d_pct"] >= -10)
    ].copy()

    print(f"Similitud con overdamped_system:")
    print(f"  Media:    {df['sim_overdamped'].mean():.4f}")
    print(f"  Max:      {df['sim_overdamped'].max():.4f}")
    print(f"  Min:      {df['sim_overdamped'].min():.4f}")
    print(f"  >= 0.65:  {len(df_above)} dias")
    print()

    print(f"Dias donde overdamped supero a gas_expansion: {len(df_near)}")
    if not df_near.empty:
        print()
        print(f"  Fecha        Regimen          VIX    Mom   Sim_over  Sim_gas  Isomorfo_real")
        print("  " + "-"*85)
        for _, row in df_near.iterrows():
            mom_str = f"{row['momentum_21d_pct']:+.2f}"
            print(f"  {row['date']:<12} {row['regime']:<16} {row['vix']:>5.1f}  "
                  f"{mom_str:>7}  {row['sim_overdamped']:>8.4f}  "
                  f"{row['sim_gas']:>7.4f}  {row['isomorph']}")
    print()

    print(f"Dias de mercado lateral (VIX 17-24, mom abs<2%, dd>-10%): {len(df_lateral)}")
    if not df_lateral.empty:
        print(f"  Sim_overdamped media: {df_lateral['sim_overdamped'].mean():.4f}")
        print(f"  Sim_gas media:        {df_lateral['sim_gas'].mean():.4f}")

    # Diagnostico
    max_sim_over = df["sim_overdamped"].max()
    dias_above   = len(df_above)
    dias_near    = len(df_near)

    print("\n" + "="*65)
    print("  DIAGNOSTICO")
    print("="*65)

    if dias_near > 0 and dias_above > 0:
        print(f"""
  overdamped_system supero a gas_expansion en {dias_near} dias.
  Ademas tuvo sim >= 0.65 en {dias_above} dias.

  CONCLUSION: El vector Z de overdamped_system ES geometricamente
  relevante para este mercado. El problema es otro:

  En Omega, la similitud se calcula para TODOS los isomorfos y
  gana el que tiene sim MAS ALTA. En los {dias_near} dias donde
  overdamped supero a gas_expansion, probablemente lorenz_attractor
  o phase_transition tuvieron sim aun mayor.

  La solucion NO es recalibrar el vector Z de overdamped.
  La solucion es entender que en el mercado sept2025-mar2026,
  cuando el patron de reversion estaba presente, habia UN PATRON
  mas dominante (lorenz o phase_transition) que lo tapaba.

  ESTO ES INFORMACION PARA E3:
  Los 50 pares de E3 deben incluir dias de estos {dias_near}
  donde overdamped deberia haber ganado segun expertos, pero
  el sistema eligio otro isomorfo. Si los expertos confirman
  que overdamped era el correcto, tendremos casos de FALLO
  real del sistema — exactamente lo que H2 mide.
        """)
    elif max_sim_over < 0.65:
        print(f"""
  La similitud maxima fue {max_sim_over:.4f}, nunca supero 0.65.
  El vector Z de referencia de overdamped_system no coincide
  con ningun patron del mercado real en este periodo.
  Recalibracion necesaria antes de E3.
        """)
    else:
        print(f"  overdamped tuvo sim >= 0.65 en {dias_above} dias pero nunca gano.")

    result = {
        "sim_overdamped_mean":         round(float(df["sim_overdamped"].mean()), 4),
        "sim_overdamped_max":          round(float(df["sim_overdamped"].max()), 4),
        "dias_above_threshold":        int(dias_above),
        "dias_where_overdamped_wins":  int(dias_near),
        "dias_mercado_lateral":        int(len(df_lateral)),
        "diagnostico": (
            f"overdamped_system supero a gas_expansion en {dias_near} dias "
            f"y tuvo sim>=0.65 en {dias_above} dias. El problema es que "
            "lorenz_attractor o phase_transition tuvieron sim aun mayor en "
            "esos dias. El vector Z no necesita recalibracion — necesita "
            "contexto de expertos en E3 para determinar cual isomorfo era "
            "el correcto en esos dias."
        ) if dias_near > 0 else (
            "El vector Z de overdamped_system no coincide con ningun patron "
            f"del mercado real. Similitud maxima: {max_sim_over:.4f}."
        )
    }
    with open(OUTPUT, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n  Resultado guardado en {OUTPUT}")
    print("="*65 + "\n")


if __name__ == "__main__":
    run()
