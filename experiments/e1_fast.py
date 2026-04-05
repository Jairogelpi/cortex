"""
E1 FAST — Backtesting rapido sin llamadas LLM
Cortex V2 | OSF: https://osf.io/wdkcx
"""
import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from loguru import logger

from cortex.config import config
from cortex.layers.omega import PHYSICAL_ISOMORPHS

OUTPUT_DIR = Path("experiments")
E1_START   = "2025-09-01"
E1_END     = "2026-03-31"


def download_data(start: str, end: str) -> pd.DataFrame:
    import yfinance as yf
    logger.info(f"Descargando SPY, VIX para {start} - {end}...")

    spy_raw = yf.Ticker("SPY").history(start=start, end=end)
    vix_raw = yf.Ticker("^VIX").history(start=start, end=end)

    if spy_raw.empty:
        raise ValueError("No hay datos de SPY")
    if vix_raw.empty:
        raise ValueError("No hay datos de VIX")

    spy_raw.index = spy_raw.index.tz_convert(None)
    vix_raw.index = vix_raw.index.tz_convert(None)
    spy_raw.index = spy_raw.index.normalize()
    vix_raw.index = vix_raw.index.normalize()

    df = pd.DataFrame({
        "spy_close": spy_raw["Close"],
        "vix":       vix_raw["Close"]
    }).dropna().sort_index()

    logger.info(f"Datos: {len(df)} dias ({df.index[0].date()} - {df.index[-1].date()})")
    return df


def classify_regime(vix, momentum, vol, drawdown) -> str:
    if vix > 35 and momentum < -5 and drawdown < -15:
        return "R4_CONTRACTION"
    elif vix > 28:
        return "R3_TRANSITION"
    elif 20 <= vix <= 28 and abs(momentum) <= 2:
        return "R2_ACCUMULATION"
    elif vix < 20 and momentum > 0 and vol < 15:
        return "R1_EXPANSION"
    return "INDETERMINATE"


def calc_phi(vix, momentum, vol, drawdown, regime) -> np.ndarray:
    z1 = float(np.clip(momentum / 8.0, -1, 1))
    z2 = float(np.clip((vix - 20.0) / 22.0, -1, 1))
    z3 = float(np.clip((vol - 12.0) / 18.0, -1, 1))
    sign_mom = np.sign(momentum) if abs(momentum) > 0.5 else 0
    z4 = float(np.clip(sign_mom * (vol / 25.0), -1, 1))
    z5 = float(np.clip(drawdown / -35.0, -1, 1))
    if vix > 35:   z6 = 0.85
    elif vix > 28: z6 = 0.45
    elif vix > 22: z6 = 0.10
    elif vix < 14: z6 = -0.65
    else:          z6 = -0.20
    z7 = float(np.clip(
        0.45*(momentum/8.0) + 0.30*(drawdown/-35.0) + 0.25*(-(vix-20.0)/22.0), -1, 1))
    z8 = {"R1_EXPANSION":-0.70,"R2_ACCUMULATION":-0.25,"R4_CONTRACTION":+0.40,
          "R3_TRANSITION":+0.72,"INDETERMINATE":+0.92}.get(regime, 0.92)
    return np.array([z1, z2, z3, z4, z5, z6, z7, z8])


def calc_delta(z, drawdown, regime) -> float:
    retorno_norm  = 0.5
    drawdown_norm = max(0.0, min(1.0, abs(drawdown) / 30.0))
    base = {"R1_EXPANSION":0.85,"R2_ACCUMULATION":0.75,"R3_TRANSITION":0.70,
            "R4_CONTRACTION":0.75,"INDETERMINATE":0.45}.get(regime, 0.45)
    z4, z8    = float(z[3]), float(z[7])
    penalty   = ((z8 + 1.0) / 2.0) * 0.15
    coherence = -0.10 if z4 < -0.6 else (0.10 if z4 > 0.5 else 0.0)
    consist   = max(0.05, min(1.0, base - penalty + coherence))
    return round(max(0.0, min(1.0,
        0.4 * retorno_norm + 0.4 * (1 - drawdown_norm) + 0.2 * consist)), 4)


def calc_omega(z) -> dict:
    sims = {}
    for name, iso in PHYSICAL_ISOMORPHS.items():
        z_ref = iso["Z"]
        na, nb = np.linalg.norm(z), np.linalg.norm(z_ref)
        cosine = float(np.dot(z, z_ref) / (na * nb)) if na > 0 and nb > 0 else 0.0
        sims[name] = round(max(0.0, min(1.0, (cosine + 1.0) / 2.0)), 4)
    best     = max(sims, key=sims.get)
    best_sim = sims[best]
    met      = best_sim >= config.SIM_THRESHOLD
    return {
        "best_isomorph":    best,
        "similarity":       best_sim,
        "threshold_met":    met,
        "trading_signal":   PHYSICAL_ISOMORPHS[best]["trading_signal"] if met else "CASH",
        "all_similarities": sims,
    }


def run_e1_fast():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*65)
    print("  CORTEX V2 - E1 Fast (deterministico, sin LLM)")
    print(f"  Periodo: {E1_START} - {E1_END}")
    print(f"  OSF: {config.OSF_PREREGISTRATION}")
    print("="*65 + "\n")

    df = download_data(E1_START, E1_END)
    n  = len(df)
    print(f"Dias: {n} ({df.index[0].date()} - {df.index[-1].date()})\n")

    results          = []
    regimes_count    = {}
    isomorphs_count  = {}
    signals_count    = {}
    delta_by_regime  = {}

    # Cabecera sin caracteres especiales
    print(f"{'Fecha':<12} {'Regimen':<16} {'VIX':>6} {'Mom':>7} "
          f"{'delta':>7} {'Isomorfo':<22} {'Sim':>6}  Senal")
    print("-"*90)

    for idx in range(n):
        if idx < 22:
            continue

        closes  = df["spy_close"].iloc[:idx+1]
        current = float(closes.iloc[-1])
        prev_21 = float(closes.iloc[-22])
        mom_21d = round((current - prev_21) / prev_21 * 100, 2)
        rets    = closes.pct_change().dropna()
        vol_21d = round(float(rets.tail(21).std() * (252**0.5) * 100), 2)
        max_90d = float(closes.tail(90).max()) if len(closes) >= 90 else float(closes.max())
        dd_90d  = round((current - max_90d) / max_90d * 100, 2)
        vix_val = float(df["vix"].iloc[idx])
        regime  = classify_regime(vix_val, mom_21d, vol_21d, dd_90d)

        next_ret = None
        if idx < n - 1:
            next_ret = round(
                (float(df["spy_close"].iloc[idx+1]) - current) / current * 100, 4)

        z     = calc_phi(vix_val, mom_21d, vol_21d, dd_90d, regime)
        delta = calc_delta(z, dd_90d, regime)
        omega = calc_omega(z)
        iso   = omega["best_isomorph"]
        sig   = omega["trading_signal"]
        day   = str(df.index[idx].date())

        results.append({
            "date":                day,
            "spy_price":           round(current, 2),
            "vix":                 round(vix_val, 2),
            "momentum_21d_pct":    mom_21d,
            "vol_realized_pct":    vol_21d,
            "drawdown_90d_pct":    dd_90d,
            "regime":              regime,
            "spy_return_next_pct": next_ret,
            "z1": round(float(z[0]),3), "z2": round(float(z[1]),3),
            "z3": round(float(z[2]),3), "z4": round(float(z[3]),3),
            "z5": round(float(z[4]),3), "z6": round(float(z[5]),3),
            "z7": round(float(z[6]),3), "z8": round(float(z[7]),3),
            "phi_var":        round(float(np.var(z)), 4),
            "delta":          delta,
            "isomorph":       iso,
            "isomorph_sim":   omega["similarity"],
            "trading_signal": sig,
            "threshold_met":  omega["threshold_met"],
        })

        regimes_count[regime]   = regimes_count.get(regime, 0) + 1
        isomorphs_count[iso]    = isomorphs_count.get(iso, 0) + 1
        signals_count[sig]      = signals_count.get(sig, 0) + 1
        delta_by_regime.setdefault(regime, []).append(delta)

        print(f"{day:<12} {regime:<16} {vix_val:>6.1f} {mom_21d:>+7.2f} "
              f"{delta:>7.4f} {iso:<22} {omega['similarity']:>6.4f}  {sig}")

    # ── CSV ───────────────────────────────────────────────────────────────────
    df_res   = pd.DataFrame(results)
    csv_path = OUTPUT_DIR / "e1_results.csv"
    df_res.to_csv(csv_path, index=False)

    # ── Metricas ──────────────────────────────────────────────────────────────
    metrics = {
        "experiment":    "E1_fast",
        "period":        f"{E1_START} to {E1_END}",
        "real_period":   f"{results[0]['date']} to {results[-1]['date']}",
        "osf":           config.OSF_PREREGISTRATION,
        "total_days":    len(results),
        "generated_at":  datetime.now().isoformat(),
        "delta_mean":    round(float(df_res["delta"].mean()), 4),
        "delta_std":     round(float(df_res["delta"].std()), 4),
        "delta_min":     round(float(df_res["delta"].min()), 4),
        "delta_max":     round(float(df_res["delta"].max()), 4),
        "delta_median":  round(float(df_res["delta"].median()), 4),
        "phi_var_mean":  round(float(df_res["phi_var"].mean()), 4),
        "omega_threshold_pct": round(
            float(df_res["threshold_met"].sum()) / len(df_res) * 100, 1),
        "regime_distribution": {
            r: {"count": c, "pct": round(c/len(results)*100, 1)}
            for r, c in regimes_count.items()},
        "isomorph_distribution": {
            i: {"count": c, "pct": round(c/len(results)*100, 1)}
            for i, c in isomorphs_count.items()},
        "signal_distribution": {
            s: {"count": c, "pct": round(c/len(results)*100, 1)}
            for s, c in signals_count.items()},
        "delta_by_regime": {
            r: {"mean": round(float(np.mean(d)),4),
                "std":  round(float(np.std(d)),4),
                "count":len(d)}
            for r, d in delta_by_regime.items()},
    }
    with open(OUTPUT_DIR / "e1_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # ── F1 baseline para H2 ───────────────────────────────────────────────────
    df_v = df_res.dropna(subset=["spy_return_next_pct"])

    def iso_dir(i):
        if i in ("gas_expansion", "compressed_gas"):      return "bullish"
        elif i in ("phase_transition", "lorenz_attractor"): return "bearish"
        return "neutral"

    def ret_dir(r):
        if r > 0.3:    return "bullish"
        elif r < -0.3: return "bearish"
        return "neutral"

    pred   = df_v["isomorph"].apply(iso_dir)
    actual = df_v["spy_return_next_pct"].apply(ret_dir)

    f1_by_class = {}
    for cls in ("bullish", "bearish", "neutral"):
        tp = int(((pred == cls) & (actual == cls)).sum())
        fp = int(((pred == cls) & (actual != cls)).sum())
        fn = int(((pred != cls) & (actual == cls)).sum())
        p  = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r_ = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r_ / (p + r_) if (p + r_) > 0 else 0.0
        f1_by_class[cls] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(p, 4), "recall": round(r_, 4), "f1": round(f1, 4)}

    macro_f1 = round(float(np.mean([v["f1"] for v in f1_by_class.values()])), 4)
    accuracy = round(float((pred == actual).sum()) / len(df_v), 4)

    f1_data = {
        "experiment":            "E1_fast",
        "baseline_accuracy":     accuracy,
        "macro_f1_baseline":     macro_f1,
        "h2_target":             round(macro_f1 + 0.20, 4),
        "total_days_evaluated":  len(df_v),
        "correct_predictions":   int((pred == actual).sum()),
        "by_class":              f1_by_class,
        "note": f"H2 requiere F1_Cortex >= {round(macro_f1+0.20, 4)} en E3"
    }
    with open(OUTPUT_DIR / "e1_isomorph_f1.json", "w") as f:
        json.dump(f1_data, f, indent=2)

    # ── Informe MD ────────────────────────────────────────────────────────────
    lines = [
        "# Experimento E1 - Backtesting Cortex V2",
        "",
        f"**Periodo pre-registrado:** {metrics['period']}",
        f"**Periodo real:** {metrics['real_period']}",
        f"**Dias procesados:** {metrics['total_days']}",
        f"**OSF:** {metrics['osf']}",
        f"**Generado:** {metrics['generated_at'][:19]}",
        "",
        "---",
        "",
        "## Delta por regimen",
        "",
        "| Regimen | Dias | % | delta medio | delta std |",
        "|---------|------|---|-------------|-----------|",
    ]
    for r, d in sorted(metrics["delta_by_regime"].items(),
                        key=lambda x: -x[1]["count"]):
        rd = metrics["regime_distribution"].get(r, {})
        lines.append(
            f"| {r} | {rd.get('count','?')} | {rd.get('pct','?')}% "
            f"| {d['mean']:.4f} | {d['std']:.4f} |")

    lines += [
        "",
        f"**Global:** media={metrics['delta_mean']:.4f}  "
        f"std={metrics['delta_std']:.4f}  "
        f"min={metrics['delta_min']:.4f}  "
        f"max={metrics['delta_max']:.4f}",
        "",
        "---",
        "",
        "## Distribucion de isomorfos",
        "",
        "| Isomorfo | Dias | % |",
        "|----------|------|---|",
    ]
    for iso, d in sorted(metrics["isomorph_distribution"].items(),
                          key=lambda x: -x[1]["count"]):
        lines.append(f"| {iso} | {d['count']} | {d['pct']}% |")

    lines += [
        "",
        "## Senales generadas",
        "",
        "| Senal | Dias | % |",
        "|-------|------|---|",
    ]
    for s, d in sorted(metrics["signal_distribution"].items(),
                        key=lambda x: -x[1]["count"]):
        lines.append(f"| {s} | {d['count']} | {d['pct']}% |")

    lines += [
        "",
        "---",
        "",
        "## F1-score baseline para H2",
        "",
        f"**Accuracy baseline:** {f1_data['baseline_accuracy']}",
        f"**Macro F1 baseline:** {f1_data['macro_f1_baseline']}",
        f"**Objetivo H2 en E3:** F1 >= {f1_data['h2_target']}",
        "",
        "| Clase | Precision | Recall | F1 |",
        "|-------|-----------|--------|----|",
    ]
    for cls, d in f1_data["by_class"].items():
        lines.append(
            f"| {cls} | {d['precision']:.4f} | {d['recall']:.4f} | {d['f1']:.4f} |")

    lines += [
        "",
        "---",
        "",
        "## Calidad de Phi",
        f"**Varianza Z media:** {metrics['phi_var_mean']:.4f}",
        f"**Omega threshold_met:** {metrics['omega_threshold_pct']}% de los dias",
        "",
        "---",
        "",
        "*Datos reales. Sin LLM. Sin look-ahead bias.*",
    ]
    report_path = OUTPUT_DIR / "e1_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    # ── Resumen consola ───────────────────────────────────────────────────────
    print("\n" + "="*65)
    print("  E1 COMPLETADO")
    print("="*65)
    print(f"  Dias: {len(results)}  ({results[0]['date']} - {results[-1]['date']})")
    print()
    print("  Regimenes:")
    for r, c in sorted(regimes_count.items(), key=lambda x: -x[1]):
        dm = np.mean(delta_by_regime.get(r, [0]))
        print(f"    {r:<22} {c:>4} dias  delta_medio={dm:.4f}")
    print()
    print("  Isomorfos:")
    for iso, c in sorted(isomorphs_count.items(), key=lambda x: -x[1]):
        print(f"    {iso:<22} {c:>4} dias ({c/len(results)*100:.1f}%)")
    print()
    print("  Senales:")
    for s, c in sorted(signals_count.items(), key=lambda x: -x[1]):
        print(f"    {s:<16} {c:>4} dias ({c/len(results)*100:.1f}%)")
    print()
    print(f"  delta global:  media={metrics['delta_mean']:.4f}  "
          f"std={metrics['delta_std']:.4f}")
    print(f"  Phi var media: {metrics['phi_var_mean']:.4f}")
    print(f"  Threshold:     {metrics['omega_threshold_pct']}% de dias")
    print()
    print(f"  F1 baseline (H2): {macro_f1}")
    print(f"  Objetivo E3 H2:   F1 >= {f1_data['h2_target']}")
    print()
    print(f"  Archivos generados:")
    print(f"    {csv_path}")
    print(f"    {OUTPUT_DIR}/e1_metrics.json")
    print(f"    {OUTPUT_DIR}/e1_isomorph_f1.json")
    print(f"    {report_path}")
    print("="*65 + "\n")

    return metrics, f1_data


if __name__ == "__main__":
    run_e1_fast()
