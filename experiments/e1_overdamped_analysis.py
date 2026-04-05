"""
Analisis de overdamped_system — por que nunca aparecio en E1
Cortex V2 | Problema documentado en e1_analisis_sin_sesgos.md

Este script busca en e1_results.csv los dias que deberian activar
overdamped_system segun el paper (mercado lateral, VIX 18-22,
momentum ~0, drawdown moderado) y calcula la similitud real de
esos dias con el vector Z de referencia de overdamped_system.

Si la similitud es alta pero gas_expansion gano de todas formas,
el problema es de calibracion del vector Z.
Si la similitud es baja, el mercado simplemente no tuvo ese patron.
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

    # Calcular similitud de cada dia con overdamped_system
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

    # Dias donde overdamped estuvo mas cerca que gas_expansion
    df_near = df[df["overdamped_would_win"]].copy()

    # Dias donde overdamped > 0.65 (habria activado el threshold)
    df_above = df[df["sim_overdamped"] >= config.SIM_THRESHOLD].copy()

    # Mercado lateral: condiciones que deberian activar overdamped
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

    print(f"Dias donde overdamped supero a gas_expansion:")
    print(f"  Total:    {len(df_near)} dias")
    if not df_near.empty:
        print(f"\n  {'Fecha':<12} {'Regimen':<16} {'VIX':>6} {'Mom':>+7} "
              f"{'Sim_over':>9} {'Sim_gas':>8} {'isomorfo_real'}")
        print("  " + "-"*85)
        for _, row in df_near.iterrows():
            print(f"  {row['date']:<12} {row['regime']:<16} {row['vix']:>6.1f} "
                  f"{row['momentum_21d_pct']:>+7.2f} "
                  f"{row['sim_overdamped']:>9.4f} {row['sim_gas']:>8.4f} "
                  f"{row['isomorph']}")
    print()

    print(f"Dias de mercado lateral (VIX 17-24, mom abs<2%, dd>-10%):")
    print(f"  Total: {len(df_lateral)} dias")
    if not df_lateral.empty:
        print(f"  Sim_overdamped media en lateral: "
              f"{df_lateral['sim_overdamped'].mean():.4f}")
        print(f"  Sim_gas media en lateral:        "
              f"{df_lateral['sim_gas'].mean():.4f}")

        print(f"\n  {'Fecha':<12} {'Regimen':<16} {'VIX':>6} {'Mom':>+7} "
              f"{'Sim_over':>9} {'Sim_gas':>8} {'isomorfo_real'}")
        print("  " + "-"*85)
        for _, row in df_lateral.head(15).iterrows():
            print(f"  {row['date']:<12} {row['regime']:<16} {row['vix']:>6.1f} "
                  f"{row['momentum_21d_pct']:>+7.2f} "
                  f"{row['sim_overdamped']:>9.4f} {row['sim_gas']:>8.4f} "
                  f"{row['isomorph']}")
        if len(df_lateral) > 15:
            print(f"  ... ({len(df_lateral)-15} dias mas)")

    # Conclusion
    print("\n" + "="*65)
    print("  DIAGNOSTICO")
    print("="*65)

    max_sim_over = df["sim_overdamped"].max()
    dias_above   = len(df_above)
    dias_lateral = len(df_lateral)

    if max_sim_over < 0.65:
        print(f"\n  CAUSA: El vector Z de referencia de overdamped_system")
        print(f"  nunca supero el threshold 0.65 en ningun dia del periodo.")
        print(f"  Similitud maxima: {max_sim_over:.4f}")
        print(f"\n  El mercado de sept2025-mar2026 no tuvo el patron geometrico")
        print(f"  que caracteriza a overdamped_system (Z6=+0.80).")
        print(f"\n  OPCIONES:")
        print(f"  A) El mercado simplemente no tuvo ese patron en este periodo.")
        print(f"     Puede aparecer en E2 si el mercado entra en rango lateral.")
        print(f"  B) El vector Z de referencia es demasiado especifico.")
        print(f"     Considerar recalibrar Z6 de +0.80 a +0.50 para activar")
        print(f"     en mas condiciones de mercado lateral.")
    elif dias_above > 0 and len(df_near) == 0:
        print(f"\n  CAUSA: overdamped supero 0.65 en {dias_above} dias,")
        print(f"  pero gas_expansion tuvo similitud mayor todos esos dias.")
        print(f"  gas_expansion 'gana siempre' porque su vector Z coincide")
        print(f"  con el mercado expansivo que domino el periodo.")
    else:
        print(f"\n  overdamped_system activo en {len(df_near)} dias.")

    # Guardar resultado
    result = {
        "sim_overdamped_mean": round(float(df["sim_overdamped"].mean()), 4),
        "sim_overdamped_max":  round(float(df["sim_overdamped"].max()), 4),
        "dias_above_threshold": int(dias_above),
        "dias_where_overdamped_wins": int(len(df_near)),
        "dias_mercado_lateral": int(dias_lateral),
        "sim_overdamped_en_lateral": round(
            float(df_lateral["sim_overdamped"].mean()), 4) if not df_lateral.empty else None,
        "diagnostico": (
            "El vector Z de referencia de overdamped_system no coincide "
            "con ningun patron del mercado real en sept2025-mar2026. "
            "La similitud maxima fue "
            f"{round(float(df['sim_overdamped'].max()), 4)}, "
            "por debajo del threshold 0.65. "
            "Requiere recalibracion antes de E3."
        ) if max_sim_over < 0.65 else (
            f"overdamped activo en {dias_above} dias pero gas_expansion "
            "tuvo similitud mayor. El periodo fue dominado por expansion."
        )
    }
    with open(OUTPUT, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n  Resultado guardado en {OUTPUT}")
    print("="*65 + "\n")


if __name__ == "__main__":
    run()
