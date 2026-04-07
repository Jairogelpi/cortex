@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
set PYTHONIOENCODING=utf-8
call venv\Scripts\activate.bat

echo.
echo ===================================================
echo  TEST ARQUITECTURA UNIFICADA
echo  Objetivo: 1 sola llamada LLM en todo el pipeline
echo  Estimacion: ~260 tokens (ratio ~0.65x vs B~400)
echo ===================================================
echo.

python run_ablacion.py
if errorlevel 1 goto error

echo.
python analisis_e2.py

echo.
git add -A
git commit -m "feat: arquitectura unificada — 1 llamada LLM vs 4 anteriores

unified_layer.py: Phi+Omega+Lambda en 1 sola llamada LLM
  - Phi deterministico calcula Z_base (0 tokens)
  - Similitudes coseno deterministicas (0 tokens)
  - Penalizaciones Lambda deterministicas (0 tokens)
  - 1 llamada LLM unificada: ajusta Z + confirma isomorfo + detects extra
  - Kappa deterministico (0 tokens)

Reduccion estimada: 2284 -> ~260 tokens (88%% reduccion)
Ratio A/B esperado: ~0.65x (objetivo original: 0.45x)

Si los tokens reales confirman, H1 puede sostenerse con reformulacion:
  'Cortex V2 con arquitectura unificada usa X% menos tokens que baseline'"
git push

echo.
echo ===================================================
echo  Ver tokens reales de A en el output arriba
echo  Si ratio < 0.45x: H1 se sostiene
echo  Si 0.45x < ratio < 1.0x: H1 sostenida parcialmente
echo ===================================================
pause
exit /b 0

:error
echo ERROR
pause
exit /b 1
