"""
E2 ANALISIS — Metricas comparativas de las 4 condiciones
Uso: python -m cortex.e2_analysis [--days N]
"""
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

from cortex.config import config

LOG_DIR = Path("logs")


def load_logs(days=None):
    records = []
    files   = sorted(LOG_DIR.glob("e2_ablation_*.jsonl"))
    if days:
        cutoff = datetime.now() - timedelta(days=days)
        files  = [f for f in files
                  if datetime.strptime(f.stem.split("_")[-1], "%Y%m%d") >= cutoff]
    for f in files:
        for line in f.read_text().splitlines():
            if line.strip():
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def analyze(days=None):
    records = load_logs(days)
    if not records:
        print("\nSin datos E2 todavia.")
        print("Primer log: logs/e2_ablation_YYYYMMDD.jsonl")
        return

    by_cond    = defaultdict(list)
    by_cond_err= defaultdict(int)
    for r in records:
        if "error" in r:
            by_cond_err[r.get("condition","?")] += 1
        else:
            by_cond[r.get("condition","?")].append(r)

    total_days = len(set(r.get("date","") for r in records))
    stats      = {}

    print("\n" + "="*70)
    print(f"  E2 ANALISIS — {total_days} dias | OSF: {config.OSF_PREREGISTRATION}")
    print("="*70)

    print(f"\n  {'Cond':<6} {'Dias':>5} {'LONG%':>7} {'CASH%':>7} "
          f"{'delta_med':>10} {'tokens_med':>11} {'errores':>8}")
    print("  " + "-"*60)

    for cond in ["A", "B", "C", "D"]:
        recs = by_cond.get(cond, [])
        errs = by_cond_err.get(cond, 0)
        if not recs:
            print(f"  {cond:<6} {'---':>5} {'sin datos':>30}  errores={errs}")
            continue

        decisions  = [r.get("decision","?") for r in recs]
        deltas     = [float(r.get("confidence", r.get("delta",0))) for r in recs]
        tokens     = [int(r.get("tokens_total",0)) for r in recs]
        n          = len(recs)
        n_long     = sum(1 for d in decisions if "LONG" in d)
        n_cash     = sum(1 for d in decisions if "CASH" in d or "HOLD" in d)
        d_mean     = np.mean(deltas)
        t_mean     = np.mean(tokens)

        stats[cond] = {"n":n,"deltas":deltas,"tokens":tokens,
                       "d_mean":d_mean,"t_mean":t_mean,"errors":errs}

        print(f"  {cond:<6} {n:>5} {n_long/n*100:>6.0f}% {n_cash/n*100:>6.0f}% "
              f"{d_mean:>9.4f}  {t_mean:>10.0f}  {errs:>8}")

    # H1
    print("\n  H1 Token efficiency (objetivo A <= 0.45*B):")
    if "A" in stats and "B" in stats:
        ta, tb = stats["A"]["t_mean"], stats["B"]["t_mean"]
        if tb > 0:
            ratio  = ta / tb
            status = "PASS" if ratio <= 0.45 else ("MARGINAL" if ratio<=0.65 else "FAIL")
            print(f"  A={ta:.0f} | B={tb:.0f} | ratio={ratio:.3f} | {status}")
        else:
            print("  Tokens B=0 aun")
    else:
        print("  Faltan datos")

    # H5
    print("\n  H5 Delta inicial Mu (A con Mu vs C sin Mu):")
    if "A" in stats and "C" in stats:
        da, dc = stats["A"]["d_mean"], stats["C"]["d_mean"]
        diff   = da - dc
        status = "PASS" if da>=0.71 and diff>0.04 else ("MARGINAL" if da>=0.65 else "FAIL")
        print(f"  delta_A={da:.4f} | delta_C={dc:.4f} | diff={diff:+.4f} | {status}")
    else:
        print("  Faltan datos")

    # H7
    print("\n  H7 Uptime (objetivo >= 0.95):")
    n_total = sum(s["n"]+s.get("errors",0)
                  for s in {**stats, **{c:{"n":0,"errors":e}
                             for c,e in by_cond_err.items()}}.values())
    n_ok    = sum(s["n"] for s in stats.values())
    if n_total > 0:
        rate   = n_ok / n_total
        status = "PASS" if rate >= 0.95 else "FAIL"
        print(f"  {n_ok}/{n_total} = {rate:.3f} | {status}")

    print(f"\n  ESTADO: {total_days}/30 dias | "
          f"Faltan: {max(0,30-total_days)} dias laborables")
    print("="*70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=None)
    args = parser.parse_args()
    analyze(args.days)
