"""
E2 ABLATION RUNNER — Orquestador de las 4 condiciones paralelas
Experimento E2 | OSF: https://osf.io/wdkcx

Condiciones del diseno de ablacion (Seccion 3.1 del paper):
  A: Cortex V2 completo
  B: LLM base sin Cortex
  C: Solo Phi+Omega+Kappa (sin infraestructura)
  D: Solo Kappa+Rho (deterministico, 0 tokens LLM)

Log diario: logs/e2_ablation_YYYYMMDD.jsonl (4 lineas/dia)
"""
import json
import time
from datetime import datetime
from pathlib import Path
from loguru import logger

from cortex.config import config

LOG_DIR       = Path("logs")
INITIAL_VALUE = 100_000.0


def run_e2_ablation(conditions: list = None) -> dict:
    if conditions is None:
        conditions = ["A", "B", "C", "D"]

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    date_str   = datetime.now().strftime("%Y%m%d")
    log_path   = LOG_DIR / f"e2_ablation_{date_str}.jsonl"
    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n" + "="*70)
    print("  CORTEX V2 — E2 Ablacion")
    print(f"  Condiciones: {conditions}")
    print(f"  OSF: {config.OSF_PREREGISTRATION}")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70 + "\n")

    results  = {}
    t_global = time.time()

    # CONDICION A
    if "A" in conditions:
        try:
            from cortex.pipeline import run_pipeline
            res_a = run_pipeline(session_id=f"a_{session_ts}")
            results["A"] = {
                "condition":      "A",
                "session_id":     res_a["session_id"],
                "date":           datetime.now().strftime("%Y-%m-%d"),
                "regime":         res_a["regime"],
                "decision":       res_a["sigma_decision"],
                "confidence":     res_a["delta"],
                "delta":          res_a["delta"],
                "isomorph":       res_a.get("isomorph", ""),
                "lambda_verdict": res_a.get("lambda_verdict", ""),
                "stop_loss":      res_a["stop_loss"],
                "portfolio_value":res_a["portfolio_value"],
                "tokens_total":   0,
            }
        except Exception as e:
            logger.error(f"Condicion A fallo: {e}")
            results["A"] = {"condition":"A","error":str(e),
                            "date":datetime.now().strftime("%Y-%m-%d")}

    # CONDICION B
    if "B" in conditions:
        try:
            from cortex.pipeline_b import run_pipeline_b
            results["B"] = run_pipeline_b(
                session_id=f"b_{session_ts}", initial_value=INITIAL_VALUE)
        except Exception as e:
            logger.error(f"Condicion B fallo: {e}")
            results["B"] = {"condition":"B","error":str(e),
                            "date":datetime.now().strftime("%Y-%m-%d")}

    # CONDICION C
    if "C" in conditions:
        try:
            from cortex.pipeline_c import run_pipeline_c
            results["C"] = run_pipeline_c(
                session_id=f"c_{session_ts}", initial_value=INITIAL_VALUE)
        except Exception as e:
            logger.error(f"Condicion C fallo: {e}")
            results["C"] = {"condition":"C","error":str(e),
                            "date":datetime.now().strftime("%Y-%m-%d")}

    # CONDICION D
    if "D" in conditions:
        try:
            from cortex.pipeline_d import run_pipeline_d
            results["D"] = run_pipeline_d(
                session_id=f"d_{session_ts}", initial_value=INITIAL_VALUE)
        except Exception as e:
            logger.error(f"Condicion D fallo: {e}")
            results["D"] = {"condition":"D","error":str(e),
                            "date":datetime.now().strftime("%Y-%m-%d")}

    total_ms = round((time.time() - t_global) * 1000)

    # Guardar log
    with open(log_path, "a", encoding="utf-8") as f:
        for cond, res in results.items():
            res["total_ms"] = total_ms
            f.write(json.dumps(res, default=str) + "\n")

    # Resumen consola
    print("\n" + "="*70)
    print("  RESUMEN COMPARATIVO E2")
    print("="*70)
    print(f"  {'Cond':<6} {'Decision':<14} {'Confidence':>12} "
          f"{'Tokens':>8} {'Ms':>8}  Extra")
    print("  " + "-"*65)

    for cond in ["A", "B", "C", "D"]:
        if cond not in results:
            continue
        r = results[cond]
        if "error" in r:
            print(f"  {cond:<6} ERROR: {r['error'][:50]}")
            continue
        conf  = r.get("confidence", r.get("delta", 0))
        tok   = r.get("tokens_total", 0)
        lat   = r.get("latency_ms", 0) or r.get("total_ms", 0)
        dec   = r.get("decision", "?")
        extra = {
            "A": f"Lambda={r.get('lambda_verdict','?')} iso={r.get('isomorph','?')}",
            "B": r.get("reasoning","")[:40],
            "C": f"iso={r.get('isomorph','?')} Lambda=OFF",
            "D": "deterministico (0 tokens)",
        }.get(cond, "")
        print(f"  {cond:<6} {dec:<14} {conf:>12.4f} {tok:>8} {lat:>8}ms  {extra}")

    # H1 preview
    if "A" in results and "B" in results:
        tok_a = results["A"].get("tokens_total", 0) or 1
        tok_b = results["B"].get("tokens_total", 1)
        if tok_b > 0:
            ratio  = tok_a / tok_b
            status = "PASS" if ratio <= 0.45 else "pendiente"
            print(f"\n  H1 tokens A/B = {tok_a}/{tok_b} = {ratio:.3f} (umbral <=0.45): {status}")

    print(f"\n  Log: {log_path} | Tiempo total: {total_ms}ms")
    print("="*70 + "\n")

    return results


if __name__ == "__main__":
    run_e2_ablation()
