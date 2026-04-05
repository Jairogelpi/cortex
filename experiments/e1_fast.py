"""
E1 FAST — Backtesting rapido sin llamadas a Opus
Para calibracion de Phi y baseline F1 de H2.

Diferencia con e1_backtest.py:
    - Omega no llama a Opus — usa solo similitud coseno determinista
    - Phi usa temperatura 0 — sin variacion entre ejecuciones
    - Kappa no llama a Haiku — calcula delta directamente
    Resultado: ~150 dias procesados en <2 minutos sin coste de API

Cuando usar este script vs e1_backtest.py:
    - e1_fast.py: calibracion, metricas, F1 baseline (este script)
    - e1_backtest.py: version completa con Opus para razonamiento real
      (usar solo sobre una muestra representativa, no los 150 dias)
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


def calc_phi_deterministic(ind: dict) -> np.ndarray:
    """Phi determinista pura — sin LLM, para backtesting rapido."""
    vix      = ind.get("vix", 20.0)
    momentum = ind.get("momentum_21d_pct", 0.0)
    vol      = ind.get("vol_realized_pct", 15.0)
    drawdown = ind.get("drawdown_90d_pct", 0.0)
    regime   = ind.get("regime", "INDETERMINATE")

    z1 = float(np.clip(momentum / 8.0, -1, 1))
    z2 = float(np.clip((vix - 20.0) / 22.0, -1, 1))
    z3 = float(np.clip((vol - 12.0) / 18.0, -1, 1))
    sign_mom = np.sign(momentum) if abs(momentum) > 0.5 else 0
    z4 = float(np.clip(sign_mom * (vol / 25.0), -1, 1))
    z5 = float(np.clip(drawdown / -35.0, -1, 1))
    if vix > 35:    z6 = 0.85
    elif vix > 28:  z6 = 0.45
    elif vix > 22:  z6 = 0.10
    elif vix < 14:  z6 = -0.65
    else:           z6 = -0.20
    z7 = float(np.clip(0.45*(momentum/8.0) + 0.30*(drawdown/-35.0) + 0.25*(-(vix-20.0)/22.0), -1, 1))
    z8_map = {"R1_EXPANSION":-0.70,"R2_ACCUMULATION":-0.25,"R4_CONTRACTION":+0.40,"R3_TRANSITION":+0.72,"INDETERMINATE":+0.92}
    z8 = z8_map.get(regime, 0.92)

    return np.array([z1, z2, z3, z4, z5, z6, z7, z8])


def calc_delta_deterministic(z: np.ndarray, ind: dict) -> float:
    """Kappa deterministico — sin LLM."""
    vix      = ind.get("vix", 20.0)
    momentum = ind.get("momentum_21d_pct", 0.0)
    drawdown = ind.get("drawdown_90d_pct", 0.0)
    regime   = ind.get("regime", "INDETERMINATE")

    retorno_norm  = max(0.0, min(1.0, (0.0 + 10.0) / 20.0))  # portfolio neutral = 0.5
    drawdown_norm = max(0.0, min(1.0, abs(drawdown) / 30.0))

    conf_map = {"R1_EXPANSION":0.85,"R2_ACCUMULATION":0.75,"R3_TRANSITION":0.70,"R4_CONTRACTION":0.75,"INDETERMINATE":0.45}
    base = conf_map.get(regime, 0.45)
    z4, z8 = float(z[3]), float(z[7])
    complexity_penalty = ((z8 + 1.0) / 2.0) * 0.15
    coherence_adj = -0.10 if z4 < -0.6 else (0.10 if z4 > 0.5 else 0.0)
    consistencia = max(0.05, min(1.0, base - complexity_penalty + coherence_adj))

    delta = 0.4 * retorno_norm + 0.4 * (1.0 - drawdown_norm) + 0.2 * consistencia
    return round(max(0.0, min(1.0, delta)), 4)


def calc_omega_deterministic(z: np.ndarray) -> dict:
    """Omega deterministico — similitud coseno sin Opus."""
    similarities = {}
    for name, iso in PHYSICAL_ISOMORPHS.items():
        z_ref = iso["Z"]
        na, nb = np.linalg.norm(z), np.linalg.norm(z_ref)
        if na == 0 or nb == 0:
            sim = 0.0
        else:
            cosine = float(np.dot(z, z_ref) / (na * nb))
            sim = max(0.0, min(1.0, (cosine + 1.0) / 2.0))
        similarities[name] = round(sim, 4)

    best     = max(similarities, key=similarities.get)
    best_sim = similarities[best]
    threshold_met = best_sim >= config.SIM_THRESHOLD

    return {
        "best_isomorph":  best,
        "similarity":     best_sim,
        "threshold_met":  threshold_met,
        "trading_signal": PHYSICAL_ISOMORPHS[best]["trading_signal"] if threshold_met else "CASH",
        "all_similarities": similarities,
    }


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


def run_e1_fast():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*65)
    print("  CORTEX V2 — E1 Fast (sin LLM, deterministico)")
    print(f"  Periodo: {E1_START} → {E1_END}")
    print(f"  OSF: {config.OSF_PREREGISTRATION}")
    print("="*65 + "\n")

    # Descargar datos historicos
    import yfinance as yf
    logger.info("Descargando SPY, VIX, IEF...")
    spy_hist = yf.Ticker("SPY").history(start=E1_START, end=E1_END)
    vix_hist = yf.Ticker("^VIX").history(start=E1_START, end=E1_END)
    ief_hist = yf.Ticker("IEF").history(start=E1_START, end=E1_END)

    if spy_hist.empty:
        print("ERROR: no se obtuvieron datos de SPY")
        return

    spy_closes = spy_hist["Close"].rename("spy_close")
    vix_closes = vix_hist["Close"].rename("vix")
    ief_closes = ief_hist["Close"].rename("ief_close")
    df = pd.concat([spy_closes, vix_closes, ief_closes], axis=1).dropna(subset=["spy_close","vix"])
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.sort_index()

    print(f"Datos: {len(df)} dias de mercado ({df.index[0].date()} → {df.index[-1].date()})\n")

    results          = []
    regimes_count    = {}
    isomorphs_count  = {}
    delta_by_regime  = {}
    signals_count    = {}

    print(f"{'Fecha':<12} {'Régimen':<16} {'VIX':>6} {'Mom':>+7} {'δ':>7} {'Isomorfo':<22} {'Sim':>6} {'Señal'}")
    print("-"*95)

    for idx in range(len(df)):
        if idx < 22:
            continue

        closes   = df["spy_close"].iloc[:idx+1]
        current  = float(closes.iloc[-1])
        prev_21  = float(closes.iloc[-22])
        mom_21d  = round((current - prev_21) / prev_21 * 100, 2)
        returns  = closes.pct_change().dropna()
        vol_21d  = round(float(returns.tail(21).std() * (252**0.5) * 100), 2)
        max_90d  = float(closes.tail(90).max()) if len(closes) >= 90 else float(closes.max())
        dd_90d   = round((current - max_90d) / max_90d * 100, 2)
        vix_val  = float(df["vix"].iloc[idx])
        regime   = classify_regime(vix_val, mom_21d, vol_21d, dd_90d)

        next_ret = None
        if idx < len(df) - 1:
            next_ret = round((float(df["spy_close"].iloc[idx+1]) - current) / current * 100, 4)

        ind = {
            "date": str(df.index[idx].date()),
            "spy_price": round(current, 2),
            "vix": vix_val,
            "momentum_21d_pct": mom_21d,
            "vol_realized_pct": vol_21d,
            "drawdown_90d_pct": dd_90d,
            "regime": regime,
            "spy_return_next_pct": next_ret,
        }

        z           = calc_phi_deterministic(ind)
        delta       = calc_delta_deterministic(z, ind)
        omega_result= calc_omega_deterministic(z)

        row = {
            **ind,
            "z_vector":       z.tolist(),
            "phi_var":        round(float(np.var(z)), 4),
            "delta":          delta,
            "isomorph":       omega_result["best_isomorph"],
            "isomorph_sim":   omega_result["similarity"],
            "trading_signal": omega_result["trading_signal"],
            "threshold_met":  omega_result["threshold_met"],
        }
        results.append(row)

        r   = regime
        iso = omega_result["best_isomorph"]
        sig = omega_result["trading_signal"]
        regimes_count[r]    = regimes_count.get(r, 0) + 1
        isomorphs_count[iso]= isomorphs_count.get(iso, 0) + 1
        signals_count[sig]  = signals_count.get(sig, 0) + 1
        if r not in delta_by_regime:
            delta_by_regime[r] = []
        delta_by_regime[r].append(delta)

        print(
            f"{ind['date']:<12} {r:<16} {vix_val:>6.1f} "
            f"{mom_21d:>+7.2f} {delta:>7.4f} "
            f"{iso:<22} {omega_result['similarity']:>6.4f} {sig}"
        )

    # ─── Guardar CSV ──────────────────────────────────────────────────────────
    df_res = pd.DataFrame(results)
    csv_path = OUTPUT_DIR / "e1_results.csv"
    df_res.to_csv(csv_path, index=False)

    # ─── Metricas ─────────────────────────────────────────────────────────────
    metrics = {
        "experiment":          "E1_fast",
        "period":              f"{E1_START} to {E1_END}",
        "real_period":         f"{results[0]['date']} to {results[-1]['date']}",
        "osf":                 config.OSF_PREREGISTRATION,
        "total_days":          len(results),
        "generated_at":        datetime.now().isoformat(),
        "delta_mean":          round(float(df_res["delta"].mean()), 4),
        "delta_std":           round(float(df_res["delta"].std()), 4),
        "delta_min":           round(float(df_res["delta"].min()), 4),
        "delta_max":           round(float(df_res["delta"].max()), 4),
        "delta_median":        round(float(df_res["delta"].median()), 4),
        "phi_var_mean":        round(float(df_res["phi_var"].mean()), 4),
        "omega_threshold_pct": round(float(df_res["threshold_met"].sum())/len(df_res)*100, 1),
        "regime_distribution": {r: {"count":n,"pct":round(n/len(results)*100,1)} for r,n in regimes_count.items()},
        "isomorph_distribution":{iso:{"count":n,"pct":round(n/len(results)*100,1)} for iso,n in isomorphs_count.items()},
        "signal_distribution": {s:{"count":n,"pct":round(n/len(results)*100,1)} for s,n in signals_count.items()},
        "delta_by_regime":     {r:{"mean":round(float(np.mean(d)),4),"std":round(float(np.std(d)),4),"count":len(d)} for r,d in delta_by_regime.items()},
    }

    # ─── F1 baseline para H2 ──────────────────────────────────────────────────
    df_valid = df_res.dropna(subset=["spy_return_next_pct"])

    def iso_dir(iso):
        if iso in ("gas_expansion","compressed_gas"):     return "bullish"
        elif iso in ("phase_transition","lorenz_attractor"): return "bearish"
        else: return "neutral"

    def ret_dir(r):
        if r > 0.3:    return "bullish"
        elif r < -0.3: return "bearish"
        else:          return "neutral"

    pred   = df_valid["isomorph"].apply(iso_dir)
    actual = df_valid["spy_return_next_pct"].apply(ret_dir)

    f1_by_class = {}
    for cls in ("bullish","bearish","neutral"):
        tp = int(((pred==cls)&(actual==cls)).sum())
        fp = int(((pred==cls)&(actual!=cls)).sum())
        fn = int(((pred!=cls)&(actual==cls)).sum())
        p  = tp/(tp+fp) if (tp+fp)>0 else 0.0
        r_ = tp/(tp+fn) if (tp+fn)>0 else 0.0
        f1 = 2*p*r_/(p+r_) if (p+r_)>0 else 0.0
        f1_by_class[cls] = {"tp":tp,"fp":fp,"fn":fn,"precision":round(p,4),"recall":round(r_,4),"f1":round(f1,4)}

    macro_f1 = round(float(np.mean([v["f1"] for v in f1_by_class.values()])),4)
    accuracy = round(float((pred==actual).sum())/len(df_valid),4)

    f1_data = {
        "experiment":           "E1_fast",
        "baseline_accuracy":    accuracy,
        "macro_f1_baseline":    macro_f1,
        "h2_target":            round(macro_f1 + 0.20, 4),
        "total_days_evaluated": len(df_valid),
        "correct_predictions":  int((pred==actual).sum()),
        "by_class":             f1_by_class,
        "note": f"H2 requiere F1_Cortex >= {round(macro_f1+0.20,4)} en E3"
    }

    metrics_path = OUTPUT_DIR / "e1_metrics.json"
    f1_path      = OUTPUT_DIR / "e1_isomorph_f1.json"
    with open(metrics_path,"w") as f: json.dump(metrics, f, indent=2)
    with open(f1_path,"w") as f:      json.dump(f1_data, f, indent=2)

    # ─── Informe Markdown ─────────────────────────────────────────────────────
    report = _report(metrics, f1_data)
    report_path = OUTPUT_DIR / "e1_report.md"
    report_path.write_text(report, encoding="utf-8")

    # ─── Resumen final ────────────────────────────────────────────────────────
    print("\n" + "="*65)
    print("  E1 COMPLETADO")
    print("="*65)
    print(f"  Dias procesados:  {len(results)}")
    print(f"  Periodo real:     {results[0]['date']} → {results[-1]['date']}")
    print()
    print("  Regimenes:")
    for r,n in sorted(regimes_count.items(), key=lambda x:-x[1]):
        dm = np.mean(delta_by_regime.get(r,[0]))
        print(f"    {r:<22} {n:>4} dias | δ_medio={dm:.4f}")
    print()
    print("  Isomorfos:")
    for iso,n in sorted(isomorphs_count.items(), key=lambda x:-x[1]):
        print(f"    {iso:<22} {n:>4} dias ({n/len(results)*100:.1f}%)")
    print()
    print("  Señales:")
    for s,n in sorted(signals_count.items(), key=lambda x:-x[1]):
        print(f"    {s:<16} {n:>4} dias ({n/len(results)*100:.1f}%)")
    print()
    print(f"  Delta global:     media={metrics['delta_mean']:.4f}  std={metrics['delta_std']:.4f}")
    print(f"  Phi var media:    {metrics['phi_var_mean']:.4f}")
    print(f"  Omega threshold:  {metrics['omega_threshold_pct']}% de dias")
    print()
    print(f"  F1 baseline (H2): {macro_f1}")
    print(f"  Objetivo E3 H2:   F1 >= {f1_data['h2_target']}")
    print()
    print(f"  Archivos:")
    print(f"    {csv_path}")
    print(f"    {metrics_path}")
    print(f"    {f1_path}")
    print(f"    {report_path}")
    print("="*65 + "\n")

    return metrics, f1_data


def _report(metrics, f1_data) -> str:
    lines = [
        "# Experimento E1 — Backtesting Cortex V2",
        "",
        f"**Periodo pre-registrado:** {metrics['period']}",
        f"**Periodo real de datos:** {metrics['real_period']}",
        f"**Días procesados:** {metrics['total_days']}",
        f"**OSF:** {metrics['osf']}",
        f"**Generado:** {metrics['generated_at'][:19]}",
        "",
        "---",
        "",
        "## Delta por régimen",
        "",
        "| Régimen | Días | % | δ medio | δ std |",
        "|---------|------|---|---------|-------|",
    ]
    for r, d in metrics["delta_by_regime"].items():
        rd = metrics["regime_distribution"].get(r, {})
        lines.append(f"| {r} | {rd.get('count','?')} | {rd.get('pct','?')}% | {d['mean']:.4f} | {d['std']:.4f} |")

    lines += [
        "",
        f"**Global:** media={metrics['delta_mean']:.4f} std={metrics['delta_std']:.4f} "
        f"min={metrics['delta_min']:.4f} max={metrics['delta_max']:.4f}",
        "",
        "---",
        "",
        "## Distribución de isomorfos",
        "",
        "| Isomorfo | Días | % |",
        "|----------|------|---|",
    ]
    for iso, d in sorted(metrics["isomorph_distribution"].items(), key=lambda x: -x[1]["count"]):
        lines.append(f"| {iso} | {d['count']} | {d['pct']}% |")

    lines += [
        "",
        "## Señales generadas",
        "",
        "| Señal | Días | % |",
        "|-------|------|---|",
    ]
    for s, d in sorted(metrics["signal_distribution"].items(), key=lambda x: -x[1]["count"]):
        lines.append(f"| {s} | {d['count']} | {d['pct']}% |")

    lines += [
        "",
        "---",
        "",
        "## F1-score baseline para H2",
        "",
        f"**Accuracy baseline:** {f1_data['baseline_accuracy']}",
        f"**Macro F1 baseline:** {f1_data['macro_f1_baseline']}",
        f"**Objetivo H2 en E3:** F1 ≥ {f1_data['h2_target']}",
        "",
        "| Clase | Precisión | Recall | F1 |",
        "|-------|-----------|--------|----|",
    ]
    for cls, d in f1_data["by_class"].items():
        lines.append(f"| {cls} | {d['precision']:.4f} | {d['recall']:.4f} | {d['f1']:.4f} |")

    lines += [
        "",
        "---",
        "",
        "## Calidad de Phi",
        "",
        f"**Varianza Z media:** {metrics['phi_var_mean']:.4f}",
        f"**Omega threshold_met:** {metrics['omega_threshold_pct']}% de los días",
        "",
        "---",
        "",
        "*Generado por experiments/e1_fast.py — datos reales, sin LLM, sin look-ahead bias.*",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    run_e1_fast()
