"""Script de test rapido para diagnostico."""
from cortex.pipeline_d import run_pipeline_d
r = run_pipeline_d()
print(f"D OK: decision={r['decision']} delta={r['delta']:.4f}")
