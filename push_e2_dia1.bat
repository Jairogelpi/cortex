@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

git add -A
git commit -m "docs+fix: E2 analisis dia1 sin sesgos + fix log acumulacion

Fix e2_ablation.py:
  - Log ahora guarda exactamente 1 linea por condicion por dia
  - Sobreescribe entradas anteriores del mismo dia (para tests locales)
  - Evita contaminar el analisis con multiples runs del mismo dia

Documento nuevo:
  experiments/e2_analisis_dia1.md — analisis honesto sin sesgos

Hallazgos dia 1 (7 abril 2026):
  + D comete error que A no comete (BACKTRACK en cash) — evidencia
    real de que la arquitectura completa anade valor
  + H7 uptime 12/12 = 100%%
  - H1 FALLA: A=2800 tokens vs B=400 tokens (ratio=7.0, umbral<=0.45)
    Requiere medicion real de tokens via OpenRouter API
  - H5 incalculable: mercado INDETERMINATE, Mu nunca consolida
    Necesita dias de R1_EXPANSION para ser testeable"

git push

echo.
echo ===================================================
echo  Estado documentado y subido
echo ===================================================
pause
