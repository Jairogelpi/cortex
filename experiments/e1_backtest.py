"""
EXPERIMENTO E1 — Backtesting sin look-ahead bias
Cortex V2 | Pre-registro OSF: https://osf.io/wdkcx

Especificacion del paper (Seccion 5, E1):
    Datos: septiembre 2025 - marzo 2026 (post-cutoff de todos los modelos)
    Objetivo: calibrar Phi y Omega con datos historicos reales
    Condicion: datos estrictamente post-cutoff para evitar look-ahead bias
    Output: parametros de calibracion + F1-score baseline para H2

Por que post-cutoff:
    Los modelos usados (Sonnet 4.6, Opus 4.6, Haiku 4.5) tienen cutoff
    de entrenamiento anterior a sept 2025. Los datos de sept 2025-mar 2026
    son genuinamente nuevos para los modelos — no pueden haber memorizado
    los patrones del mercado en ese periodo.

Metodologia:
    1. Descargar datos diarios SPY, VIX, IEF para sept 2025 - mar 2026
    2. Para cada dia de mercado: calcular indicadores de regimen
    3. Ejecutar Phi + Kappa + Omega (sin Alpaca, sin ordenes reales)
    4. Registrar: regimen, delta, isomorfo, similitud, senal
    5. Calcular metricas de calibracion:
       - Drift de Phi (variacion del vector Z en el tiempo)
       - Frecuencia de cada isomorfo
       - Correlacion isomorfo con retorno SPY del dia siguiente (H2 baseline)
       - Distribucion de delta en cada regimen

Output para el paper:
    - experiments/e1_results.csv: una fila por dia de mercado
    - experiments/e1_metrics.json: metricas de calibracion
    - experiments/e1_isomorph_f1.json: F1-score baseline para H2
    - experiments/e1_report.md: informe completo

NO usa Tau ni ejecuta ordenes. Es solo observacion y calibracion.
"""
import json
import time
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger

from cortex.config import config
from cortex.layers.phi import PhiLayer
from cortex.layers.kappa import KappaLayer
from cortex.layers.omega import OmegaLayer, PHYSICAL_ISOMORPHS

# ─── Parametros de E1 ─────────────────────────────────────────────────────────

E1_START = "2025-09-01"   # post-cutoff de todos los modelos
E1_END   = "2026-03-31"   # fin del periodo de calibracion
OUTPUT_DIR = Path("experiments")

# ─── Funciones de datos ───────────────────────────────────────────────────────

def download_historical_data(start: str, end: str) -> pd.DataFrame:
    """
    Descarga datos historicos reales de Yahoo Finance.
    SPY (precio, retornos), VIX (estres), IEF (flight-to-safety).
    """
    logger.info(f"Descargando datos historicos {start} → {end}...")

    spy_hist  = yf.Ticker("SPY").history(start=start, end=end)
    vix_hist  = yf.Ticker("^VIX").history(start=start, end=end)
    ief_hist  = yf.Ticker("IEF").history(start=start, end=end)

    if spy_hist.empty:
        raise ValueError("No se obtuvieron datos de SPY")

    # Alinear todos los indices
    spy_closes = spy_hist["Close"].rename("spy_close")
    vix_closes = vix_hist["Close"].rename("vix")
    ief_closes = ief_hist["Close"].rename("ief_close")

    df = pd.concat([spy_closes, vix_closes, ief_closes], axis=1)
    df = df.dropna(subset=["spy_close", "vix"])
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.sort_index()

    logger.info(f"Datos descargados: {len(df)} dias de mercado")
    return df


def calc_indicators_for_day(df: pd.DataFrame, idx: int) -> dict:
    """
    Calcula indicadores de regimen para un dia especifico del backtest.
    Usa solo datos ANTERIORES a ese dia (no look-ahead).
    """
    if idx < 22:
        return None  # necesitamos al menos 22 dias de historia

    window = df.iloc[:idx+1]  # datos hasta hoy incluido, nada del futuro
    closes = window["spy_close"]

    current_price  = float(closes.iloc[-1])
    price_21d_ago  = float(closes.iloc[-22])
    momentum_21d   = round((current_price - price_21d_ago) / price_21d_ago * 100, 2)

    returns = closes.pct_change().dropna()
    vol_21d = round(float(returns.tail(21).std() * (252**0.5) * 100), 2)

    max_90d  = float(closes.tail(90).max()) if len(closes) >= 90 else float(closes.max())
    drawdown = round((current_price - max_90d) / max_90d * 100, 2)

    vix = float(window["vix"].iloc[-1])

    # Clasificacion de regimen (igual que en produccion)
    if vix > 35 and momentum_21d < -5 and drawdown < -15:
        regime = "R4_CONTRACTION"
    elif vix > 28:
        regime = "R3_TRANSITION"
    elif 20 <= vix <= 28 and abs(momentum_21d) <= 2:
        regime = "R2_ACCUMULATION"
    elif vix < 20 and momentum_21d > 0 and vol_21d < 15:
        regime = "R1_EXPANSION"
    else:
        regime = "INDETERMINATE"

    # Retorno del dia siguiente (para calibracion — solo se usa DESPUES del backt.)
    next_return = None
    if idx < len(df) - 1:
        next_close  = float(df["spy_close"].iloc[idx + 1])
        next_return = round((next_close - current_price) / current_price * 100, 4)

    return {
        "date":              str(df.index[idx].date()),
        "spy_price":         round(current_price, 2),
        "vix":               vix,
        "momentum_21d_pct":  momentum_21d,
        "vol_realized_pct":  vol_21d,
        "drawdown_90d_pct":  drawdown,
        "regime":            regime,
        "spy_return_next_pct": next_return,
    }


# ─── Pipeline de backtesting ──────────────────────────────────────────────────

def run_e1():
    """
    Ejecuta el experimento E1 completo.
    Para cada dia de mercado sept 2025 - mar 2026:
      1. Calcula indicadores (sin look-ahead)
      2. Ejecuta Phi → Kappa → Omega
      3. Registra resultado
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*65)
    print("  CORTEX V2 — Experimento E1: Backtesting")
    print(f"  Periodo: {E1_START} → {E1_END}")
    print(f"  Pre-registro OSF: {config.OSF_PREREGISTRATION}")
    print("="*65 + "\n")

    # Descargar datos historicos
    df = download_historical_data(E1_START, E1_END)
    print(f"Datos disponibles: {len(df)} dias de mercado\n")

    # Inicializar capas (sin LLM para backtesting rapido)
    # Phi usa temperatura 0 para reproducibilidad
    phi   = PhiLayer(temperature=0.0)
    kappa = KappaLayer()
    omega = OmegaLayer()

    results = []
    regimes_count  = {}
    isomorphs_count = {}
    delta_by_regime = {}

    print(f"{'Fecha':<12} {'Reg':<16} {'VIX':>6} {'Mom%':>7} {'δ':>7} {'Isomorfo':<20} {'Sim':>6} {'Señal':<12}")
    print("-"*90)

    for idx in range(len(df)):
        ind = calc_indicators_for_day(df, idx)
        if ind is None:
            continue

        day_date = ind["date"]

        try:
            # Phi: factorizar estado
            phi_state = phi.factorize(ind)

            # Kappa: calcular delta
            kappa_eval = kappa.evaluate(
                phi_state,
                portfolio_value=100_000.0,
                initial_value=100_000.0,
                spy_benchmark_return=0.0,
                open_positions=[]
            )

            # Omega: detectar isomorfo
            omega_hyp = omega.generate_hypothesis(phi_state)

            # Registrar resultado
            row = {
                **ind,
                "z_vector":       phi_state.to_vector().tolist(),
                "phi_confidence": phi_state.confidence,
                "phi_var":        round(float(np.var(phi_state.to_vector())), 4),
                "delta":          kappa_eval.delta,
                "kappa_decision": kappa_eval.decision,
                "isomorph":       omega_hyp.best_isomorph,
                "isomorph_sim":   omega_hyp.similarity,
                "trading_signal": omega_hyp.trading_signal,
                "threshold_met":  omega_hyp.threshold_met,
                "all_similarities": omega_hyp.all_similarities,
            }
            results.append(row)

            # Estadisticas acumuladas
            r = ind["regime"]
            regimes_count[r]  = regimes_count.get(r, 0) + 1
            iso = omega_hyp.best_isomorph
            isomorphs_count[iso] = isomorphs_count.get(iso, 0) + 1
            if r not in delta_by_regime:
                delta_by_regime[r] = []
            delta_by_regime[r].append(kappa_eval.delta)

            # Print progreso
            print(
                f"{day_date:<12} {r:<16} {ind['vix']:>6.1f} "
                f"{ind['momentum_21d_pct']:>+7.2f} {kappa_eval.delta:>7.4f} "
                f"{iso:<20} {omega_hyp.similarity:>6.4f} {omega_hyp.trading_signal:<12}"
            )

            # Pausa breve para no saturar la API de LLM
            # Omega usa Opus — limitamos a max 1 llamada cada 2s
            time.sleep(2)

        except Exception as e:
            logger.error(f"E1 error en {day_date}: {e}")
            continue

    # ─── Guardar resultados CSV ───────────────────────────────────────────────
    df_results = pd.DataFrame(results)
    csv_path   = OUTPUT_DIR / "e1_results.csv"
    df_results.to_csv(csv_path, index=False)
    logger.info(f"Resultados guardados: {csv_path}")

    # ─── Calcular metricas de calibracion ─────────────────────────────────────
    metrics = _calc_metrics(df_results, regimes_count, isomorphs_count, delta_by_regime)

    metrics_path = OUTPUT_DIR / "e1_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    # ─── Calcular F1-score baseline para H2 ───────────────────────────────────
    f1_data = _calc_isomorph_f1_baseline(df_results)

    f1_path = OUTPUT_DIR / "e1_isomorph_f1.json"
    with open(f1_path, "w") as f:
        json.dump(f1_data, f, indent=2, default=str)

    # ─── Generar informe ──────────────────────────────────────────────────────
    report = _generate_report(metrics, f1_data, len(results))
    report_path = OUTPUT_DIR / "e1_report.md"
    report_path.write_text(report, encoding="utf-8")

    # ─── Imprimir resumen ─────────────────────────────────────────────────────
    print("\n" + "="*65)
    print("  E1 COMPLETADO")
    print("="*65)
    print(f"  Dias procesados:     {len(results)}")
    print(f"  Periodo real:        {results[0]['date']} → {results[-1]['date']}")
    print()
    print("  Distribucion de regimenes:")
    for r, n in sorted(regimes_count.items(), key=lambda x: -x[1]):
        pct = n / len(results) * 100
        delta_mean = np.mean(delta_by_regime.get(r, [0]))
        print(f"    {r:<20} {n:>4} dias ({pct:.1f}%) | δ_medio={delta_mean:.4f}")
    print()
    print("  Distribucion de isomorfos:")
    for iso, n in sorted(isomorphs_count.items(), key=lambda x: -x[1]):
        pct = n / len(results) * 100
        print(f"    {iso:<22} {n:>4} dias ({pct:.1f}%)")
    print()
    print(f"  Delta medio global:  {df_results['delta'].mean():.4f}")
    print(f"  Delta std global:    {df_results['delta'].std():.4f}")
    print(f"  Delta minimo:        {df_results['delta'].min():.4f}")
    print(f"  Delta maximo:        {df_results['delta'].max():.4f}")
    print()
    print(f"  Archivos generados:")
    print(f"    {csv_path}")
    print(f"    {metrics_path}")
    print(f"    {f1_path}")
    print(f"    {report_path}")
    print("="*65 + "\n")

    return metrics


def _calc_metrics(df: pd.DataFrame, regimes_count: dict,
                  isomorphs_count: dict, delta_by_regime: dict) -> dict:
    """Calcula metricas de calibracion del backtesting."""
    metrics = {
        "experiment":         "E1",
        "period":             f"{E1_START} to {E1_END}",
        "osf_preregistration": config.OSF_PREREGISTRATION,
        "total_days":         len(df),
        "generated_at":       datetime.now().isoformat(),

        # Delta global
        "delta_mean":   round(float(df["delta"].mean()), 4),
        "delta_std":    round(float(df["delta"].std()), 4),
        "delta_min":    round(float(df["delta"].min()), 4),
        "delta_max":    round(float(df["delta"].max()), 4),
        "delta_median": round(float(df["delta"].median()), 4),

        # Delta por regimen
        "delta_by_regime": {
            r: {
                "mean":   round(float(np.mean(deltas)), 4),
                "std":    round(float(np.std(deltas)), 4),
                "count":  len(deltas)
            }
            for r, deltas in delta_by_regime.items()
        },

        # Distribucion de regimenes
        "regime_distribution": {
            r: {"count": n, "pct": round(n/len(df)*100, 1)}
            for r, n in regimes_count.items()
        },

        # Distribucion de isomorfos
        "isomorph_distribution": {
            iso: {"count": n, "pct": round(n/len(df)*100, 1)}
            for iso, n in isomorphs_count.items()
        },

        # Phi: varianza Z media (indicador de calidad de factorizacion)
        "phi_z_variance_mean": round(float(df["phi_var"].mean()), 4),
        "phi_z_variance_std":  round(float(df["phi_var"].std()), 4),

        # Dias con threshold_met (Omega activo)
        "omega_threshold_met_pct": round(
            float(df["threshold_met"].sum()) / len(df) * 100, 1
        ),
    }
    return metrics


def _calc_isomorph_f1_baseline(df: pd.DataFrame) -> dict:
    """
    Calcula el F1-score baseline para H2.

    Logica: el isomorfo 'correcto' para un dia se define como el que mejor
    predice el retorno del dia siguiente:
    - gas_expansion / compressed_gas → retorno positivo (> +0.3%)
    - phase_transition / lorenz_attractor → retorno negativo (< -0.3%)
    - overdamped_system → retorno neutro (-0.3% a +0.3%)

    Este baseline mide cuantas veces Omega eligio el isomorfo que mejor
    coincide con el retorno real del dia siguiente.
    """
    if "spy_return_next_pct" not in df.columns:
        return {"error": "sin datos de retorno siguiente"}

    df_valid = df.dropna(subset=["spy_return_next_pct"])
    if df_valid.empty:
        return {"error": "sin filas validas"}

    def isomorph_direction(iso):
        if iso in ("gas_expansion", "compressed_gas"):
            return "bullish"
        elif iso in ("phase_transition", "lorenz_attractor"):
            return "bearish"
        else:
            return "neutral"

    def return_direction(ret):
        if ret > 0.3:
            return "bullish"
        elif ret < -0.3:
            return "bearish"
        else:
            return "neutral"

    predicted  = df_valid["isomorph"].apply(isomorph_direction)
    actual     = df_valid["spy_return_next_pct"].apply(return_direction)
    correct    = (predicted == actual).sum()
    total      = len(df_valid)
    accuracy   = round(correct / total, 4)

    # F1 por clase
    from collections import Counter
    results_by_class = {}
    for cls in ("bullish", "bearish", "neutral"):
        tp = ((predicted == cls) & (actual == cls)).sum()
        fp = ((predicted == cls) & (actual != cls)).sum()
        fn = ((predicted != cls) & (actual == cls)).sum()
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        results_by_class[cls] = {
            "tp": int(tp), "fp": int(fp), "fn": int(fn),
            "precision": round(float(precision), 4),
            "recall":    round(float(recall), 4),
            "f1":        round(float(f1), 4)
        }

    macro_f1 = round(
        float(np.mean([v["f1"] for v in results_by_class.values()])), 4
    )

    return {
        "experiment":          "E1",
        "baseline_accuracy":   accuracy,
        "macro_f1_baseline":   macro_f1,
        "total_days_evaluated":total,
        "correct_predictions": int(correct),
        "by_class":            results_by_class,
        "note": (
            "Este es el F1-score baseline para H2. "
            "H2 requiere F1_Cortex >= F1_baseline + 0.20 en E3."
        )
    }


def _generate_report(metrics: dict, f1_data: dict, n_days: int) -> str:
    """Genera el informe Markdown de E1."""
    lines = [
        "# Experimento E1 — Backtesting Cortex V2",
        "",
        f"**Periodo:** {E1_START} → {E1_END}",
        f"**Dias procesados:** {n_days}",
        f"**Pre-registro OSF:** {config.OSF_PREREGISTRATION}",
        f"**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## 1. Delta score por régimen",
        "",
        "| Régimen | Dias | % | δ medio | δ std |",
        "|---------|------|---|---------|-------|",
    ]

    for r, data in metrics.get("delta_by_regime", {}).items():
        reg_dist = metrics.get("regime_distribution", {}).get(r, {})
        lines.append(
            f"| {r} | {reg_dist.get('count','?')} | "
            f"{reg_dist.get('pct','?')}% | "
            f"{data['mean']:.4f} | {data['std']:.4f} |"
        )

    lines += [
        "",
        f"**Delta global:** media={metrics['delta_mean']:.4f} "
        f"std={metrics['delta_std']:.4f} "
        f"min={metrics['delta_min']:.4f} "
        f"max={metrics['delta_max']:.4f}",
        "",
        "---",
        "",
        "## 2. Distribución de isomorfos",
        "",
        "| Isomorfo | Dias | % |",
        "|----------|------|---|",
    ]

    for iso, data in metrics.get("isomorph_distribution", {}).items():
        lines.append(f"| {iso} | {data['count']} | {data['pct']}% |")

    lines += [
        "",
        f"**Omega threshold_met:** {metrics.get('omega_threshold_met_pct', '?')}% de los días",
        "",
        "---",
        "",
        "## 3. F1-score baseline para H2",
        "",
        f"**Accuracy baseline:** {f1_data.get('baseline_accuracy', '?')}",
        f"**Macro F1 baseline:** {f1_data.get('macro_f1_baseline', '?')}",
        "",
        "| Clase | Precisión | Recall | F1 |",
        "|-------|-----------|--------|----|",
    ]

    for cls, data in f1_data.get("by_class", {}).items():
        lines.append(
            f"| {cls} | {data['precision']:.4f} | "
            f"{data['recall']:.4f} | {data['f1']:.4f} |"
        )

    lines += [
        "",
        f"> **H2 requiere:** F1_Cortex ≥ F1_baseline + 0.20 en E3",
        f"> **F1 baseline E1:** {f1_data.get('macro_f1_baseline', '?')}",
        f"> **Objetivo E3:** F1 ≥ {round((f1_data.get('macro_f1_baseline') or 0) + 0.20, 4)}",
        "",
        "---",
        "",
        "## 4. Calidad de Phi",
        "",
        f"**Varianza Z media:** {metrics.get('phi_z_variance_mean', '?')}",
        f"**Varianza Z std:** {metrics.get('phi_z_variance_std', '?')}",
        "",
        "> Una varianza Z alta indica buena separacion de dimensiones.",
        "> Objetivo: var > 0.15 en todos los dias (verificado en test de integracion).",
        "",
        "---",
        "",
        "## 5. Implicaciones para E2",
        "",
        "- Los δ medios por régimen establecen las expectativas para E2",
        "- La distribución de isomorfos indica qué señales predominarán en E2",
        "- El F1 baseline es el umbral que H2 debe superar en E3",
        "",
        "---",
        "",
        f"*Generado automáticamente por experiments/e1_backtest.py*",
        f"*Todos los datos son reales. Sin simulación. Sin look-ahead bias.*",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    run_e1()
