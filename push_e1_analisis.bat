@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

git add -A
git commit -m "docs: analisis E1 sin sesgos + diagnostico overdamped_system

Nuevos archivos:
- experiments/e1_analisis_sin_sesgos.md
  Analisis honesto de E1: que hizo, que NO hizo, limitaciones reales.
  Tres problemas documentados antes de E2:
  1. overdamped_system = 0 dias, necesita recalibracion
  2. F1 baseline 0.278 usa proxy debil (retorno dia siguiente)
  3. E1 usa Phi/Kappa/Omega deterministicos, no LLMs reales

- experiments/e1_overdamped_analysis.py
  Diagnostico: por que overdamped_system nunca aparecio.
  Calcula similitud de cada dia de E1 con el vector Z de referencia.
  Ejecutar: run_e1_overdamped.bat

Lo que E1 si demuestra (solido):
- Umbrales 0.65/0.70 validados empiricamente
- Sistema en HOLD durante deterioro de mar2026 (correcto)
- gas_expansion domino oct2025-ene2026
- lorenz_attractor domino feb-mar2026"

git push

echo.
echo ===================================================
echo  Documentacion E1 completa subida a GitHub
echo.
echo  SIGUIENTE: ejecuta run_e1_overdamped.bat
echo  para diagnosticar overdamped_system
echo ===================================================
pause
