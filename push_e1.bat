@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

git add -A
git commit -m "feat: Experimento E1 — backtesting sept 2025 - mar 2026

experiments/e1_fast.py:
  - Phi deterministico (sin LLM, temperatura 0)
  - Kappa deterministico (sin LLM)
  - Omega deterministico (similitud coseno pura, sin Opus)
  - ~150 dias de mercado en <3 minutos
  - Sin look-ahead bias: cada dia solo ve datos anteriores
  - Output: e1_results.csv, e1_metrics.json, e1_isomorph_f1.json, e1_report.md

experiments/e1_backtest.py:
  - Version completa con Opus para razonamiento real
  - Usar sobre muestra representativa, no todos los dias

run_e1.bat: ejecuta e1_fast directamente

Pre-registro OSF: https://osf.io/wdkcx"

git push

echo.
echo ===================================================
echo  E1 subido a GitHub
echo  Ejecuta run_e1.bat para lanzar el backtesting
echo ===================================================
pause
