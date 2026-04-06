@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

echo Subiendo ablacion E2 a GitHub...
git add -A
git commit -m "feat: ablacion E2 — condiciones B, C, D implementadas

Nuevos archivos en cortex/:
  pipeline_b.py  — LLM base sin Cortex (controla capacidad del modelo)
  pipeline_c.py  — Phi+Omega+Kappa sin Lambda/Mu/Sigma (aisla abstraccion)
  pipeline_d.py  — Solo Kappa+Rho deterministico (controla solo backtrack)
  e2_ablation.py — orquestador 4 condiciones, log e2_ablation_YYYYMMDD.jsonl
  e2_analysis.py — analisis H1, H5, H7 con datos reales

GitHub Actions actualizado: corre A,B,C,D cada dia 09:00 UTC
Log: logs/e2_ablation_YYYYMMDD.jsonl (4 lineas/dia)

OSF: https://osf.io/wdkcx"
git push

echo.
echo ===================================================
echo  Ablacion subida a GitHub
echo.
echo  SIGUIENTE: ejecuta run_e2_ablacion.bat
echo  para el primer test con datos reales
echo ===================================================
pause
