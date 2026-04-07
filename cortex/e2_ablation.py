"""
E2 ABLATION RUNNER — Orquestador de las 4 condiciones paralelas
Experimento E2 | OSF: https://osf.io/wdkcx

Condicion A: tokens_total son REALES via token_tracker (phi+kappa+omega+lambda)
Condicion B: tokens_total son REALES via usage de OpenAI response
Condicion C: tokens_total son ESTIMADOS (phi+kappa+omega sin medicion exacta)
Condicion D: tokens_total = 0 (deterministico, sin LLM)

Log: logs/e2_ablation_YYYYMMDD.jsonl — EXACTAMENTE 1 linea por condicion por dia.
"""
import json
import time
from datetime import datetime
from pathlib import Path
from loguru import logger

from cortex.config import config

LOG_DIR       = Path("logs")
INITIAL_VALUE = 100_000.0


def _save_results(log_path: Path, results: dict, total_ms: int):
    """1 linea por condicion por dia — sobreescribe si ya existe."""
    existing = {}
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    r = json.loads(line)
                    if "condition" in r and "error" not in r:
                        existing[r["condition"]] = r
                except Exception:
                    pass
    for cond, res in results.items():
        if "error" not in res:
            res["total_ms"] = total_ms
            existing[cond] = res
    with open(log_path, "w", encoding="utf-8") as f:
        for cond in ["A", "B", "C", "D"]:
            if cond in existing:
                f.write(json.dumps(existing[cond], default=str, ensure_ascii=False) + "\n")


def run_e2_ablation(conditions: list = None) -> dict:
    if conditions is None:
        conditions = ["A", "B", "C", "D"]

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    date_str   = datetime.now().strftime("%Y%m%d")
    log_path   = LOG_DIR / f"e2_ablation_{date_str}.jsonl"
    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n" + "="*70)
    print("  CORTEX V2 - E2 Ablacion")
    print(f"  Condiciones: {conditions}")
    print(f"  OSF: {config.OSF_PREREGISTRATION}")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70 + "\n")

    results  = {}
    t_global = time.time()

    # CONDICION A — Cortex V2 completo con tokens REALES
    if "A" in conditions:
        try:
            from cortex.pipeline import run_pipeline
            res_a = run_pipeline(session_id=f"a_{session_ts}")
            results["A"] = {
                "condition":       "A",
                "session_id":      res_a["session_id"],
                "date":            datetime.now().strftime("%Y-%m-%d"),
                "regime":          res_a["regime"],
                "decision":        res_a["sigma_decision"],
                "confidence":      res_a["delta"],
                "delta":           res_a["delta"],
                "isomorph":        res_a.get("isomorph", ""),
                "lambda_verdict":  res_a.get("lambda_verdict", ""),
                "stop_loss":       res_a["stop_loss"],
                "portfolio_value": res_a["portfolio_value"],
                "tokens_total":    res_a["tokens_total"],    # REAL via token_tracker
                "tokens_by_layer": res_a.get("tokens_by_layer", {}),
            }
        except Exception as e:
            logger.error(f"Condicion A fallo: {e}")
            results["A"] = {"condition":"A","error":str(e),"date":datetime.now().strftime("%Y-%m-%d")}

    # CONDICION B — LLM base (tokens REALES via usage de la API)
    if "B" in conditions:
        try:
            from cortex.pipeline_b import run_pipeline_b
            results["B"] = run_pipeline_b(session_id=f"b_{session_ts}", initial_value=INITIAL_VALUE)
        except Exception as e:
            logger.error(f"Condicion B fallo: {e}")
            results["B"] = {"condition":"B","error":str(e),"date":datetime.now().strftime("%Y-%m-%d")}

    # CONDICION C — Phi+Omega+Kappa (tokens estimados — sin tracker en C por ahora)
    if "C" in conditions:
        try:
            from cortex.pipeline_c import run_pipeline_c
            results["C"] = run_pipeline_c(session_id=f"c_{session_ts}", initial_value=INITIAL_VALUE)
        except Exception as e:
            logger.error(f"Condicion C fallo: {e}")
            results["C"] = {"condition":"C","error":str(e),"date":datetime.now().strftime("%Y-%m-%d")}

    # CONDICION D — Solo Kappa+Rho (0 tokens LLM — deterministico)
    if "D" in conditions:
        try:
            from cortex.pipeline_d import run_pipeline_d
            results["D"] = run_pipeline_d(session_id=f"d_{session_ts}", initial_value=INITIAL_VALUE)
        except Exception as e:
            logger.error(f"Condicion D fallo: {e}")
            results["D"] = {"condition":"D","error":str(e),"date":datetime.now().strftime("%Y-%m-%d")}

    total_ms = round((time.time() - t_global) * 1000)
    _save_results(log_path, results, total_ms)

    # Resumen
    print("\n" + "="*70)
    print("  RESUMEN E2 - " + datetime.now().strftime("%Y-%m-%d"))
    print("="*70)
    print(f"  {'Cond':<6} {'Decision':<14} {'delta':>8} {'Tokens':>8} {'Ms':>8}  Info")
    print("  " + "-"*65)

    for cond in ["A","B","C","D"]:
        if cond not in results:
            continue
        r = results[cond]
        if "error" in r:
            print(f"  {cond:<6} ERROR: {str(r['error'])[:55]}")
            continue
        conf = r.get("confidence", r.get("delta", 0))
        tok  = r.get("tokens_total", 0)
        lat  = r.get("latency_ms", 0) or total_ms
        dec  = r.get("decision","?")
        info = {
            "A": f"Lambda={r.get('lambda_verdict','?')} iso={r.get('isomorph','?')} tokens=REAL",
            "B": r.get("reasoning","")[:40] + " [tokens=REAL]",
            "C": f"iso={r.get('isomorph','?')} Lambda=OFF [tokens=estimado]",
            "D": "deterministico 0 tokens LLM",
        }.get(cond,"")
        print(f"  {cond:<6} {dec:<14} {conf:>8.4f} {tok:>8} {lat:>8}ms  {info}")

    tok_a = results.get("A",{}).get("tokens_total",0)
    tok_b = results.get("B",{}).get("tokens_total",0)
    if tok_a and tok_b:
        ratio  = tok_a / tok_b
        status = "PASS" if ratio <= 0.45 else ("MARGINAL" if ratio <= 1.0 else "FAIL")
        print(f"\n  H1 (tokens reales) A={tok_a} / B={tok_b} = {ratio:.3f} (umbral <=0.45): {status}")
        if status == "FAIL":
            print(f"  A usa {ratio:.1f}x mas tokens que B.")
            print(f"  Para PASS: A necesita <= {int(tok_b*0.45)} tokens.")
            # Detalle por capa de A
            by_layer = results.get("A",{}).get("tokens_by_layer",{})
            if by_layer:
                print(f"  Desglose A: {by_layer}")

    errors = [c for c,r in results.items() if "error" in r]
    if errors:
        print(f"\n  ERRORES: {errors}")

    print(f"\n  Log: {log_path} (1 linea/condicion/dia)")
    print(f"  Tiempo total: {total_ms}ms")
    print("="*70 + "\n")

    return results


if __name__ == "__main__":
    run_e2_ablation()
