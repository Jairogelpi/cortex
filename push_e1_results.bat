@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

git add -A
git commit -m "data: Experimento E1 completado — 123 dias sept2025-mar2026

Resultados reales (sin LLM, sin look-ahead bias):

Regimenes:
  R1_EXPANSION:    68 dias (55.3%) delta_medio=0.7648
  R2_ACCUMULATION: 26 dias (21.1%) delta_medio=0.7092
  INDETERMINATE:   26 dias (21.1%) delta_medio=0.6210
  R3_TRANSITION:    3 dias  (2.4%) delta_medio=0.6218

Isomorfos: gas_expansion 62%, lorenz_attractor 34%, otros 4%
Senales:   LONG 62%, CASH 34%, LONG_PREPARE 2%, DEFENSIVE 2%

Delta global: media=0.7192 std=0.0616 min=0.568 max=0.786

F1 baseline (H2): 0.278
Objetivo E3 H2:   F1 >= 0.478

Hallazgos clave:
1. Umbrales 0.65/0.70 validados empiricamente por los datos reales
2. overdamped_system = 0 dias — necesita recalibracion antes de E3
3. Sistema habria estado en HOLD durante deterioro de marzo 2026

Archivos:
  experiments/e1_results.csv    (123 filas)
  experiments/e1_metrics.json
  experiments/e1_isomorph_f1.json
  experiments/e1_report.md"

git push

echo.
echo ===================================================
echo  E1 subido a GitHub
echo  https://github.com/Jairogelpi/cortex
echo.
echo  Siguiente: E2 (30 dias paper trading en Alpaca)
echo  El sistema ya corre solo con GitHub Actions
echo  a las 09:00 UTC cada dia laborable
echo ===================================================
pause
