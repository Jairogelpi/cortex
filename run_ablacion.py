"""Script principal de ablacion E2."""
from cortex.e2_ablation import run_e2_ablation
results = run_e2_ablation(["A", "B", "C", "D"])
errors = [c for c, r in results.items() if "error" in r]
if errors:
    print(f"\nERROR en condiciones: {errors}")
    raise SystemExit(1)
print("\nTODAS LAS CONDICIONES OK")
