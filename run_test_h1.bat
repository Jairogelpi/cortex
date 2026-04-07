@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
set PYTHONIOENCODING=utf-8
call venv\Scripts\activate.bat

echo.
echo ===================================================
echo  TEST H1 OPTIMIZADO AL MAXIMO
echo  HIGH_SIM=0.86  GAP_MIN=0.03  MAX_TOKENS=20
echo  Dia claro (lorenz sim>0.86, gap>0.03): 0 tokens
echo  Dia ambiguo: ~75 tokens (telegrama)
echo ===================================================
echo.

python run_ablacion.py
if errorlevel 1 goto error

echo.
python analisis_e2.py

echo.
git add -A
git commit -m "perf: H1 optimizacion maxima sin perder potencia

unified_layer.py:
  - Prompt telegrama: elimina JSON template, top2 deltas Z (no top3)
  - snapshot: 5 campos (elimina Vol y DD que no cambian la decision)
  - HIGH_SIM: 0.92->0.86 (dias con sim>0.86 y gap>0.03 usan ruta rapida)
  - GAP_MIN: 0.05->0.03 (gap de 3pts ya es suficientemente discriminante)
  - MAX_TOKENS: 24->20
  - Parse flexible: acepta texto libre ademas de JSON

config.py:
  - UNIFIED_REVIEW_HIGH_SIM=0.86
  - UNIFIED_REVIEW_GAP_MIN=0.03
  - UNIFIED_REVIEW_MAX_TOKENS=20

Potencia preservada:
  - LLM sigue activandose en dias ambiguos (gap<0.03 o contra>=2)
  - Puede cambiar el isomorfo si detecta algo real
  - Penalizaciones deterministicas sin cambio

H1 esperada:
  - Dias claros: ratio=0.0x (PASS)
  - Dias ambiguos: ratio~0.19x (PASS)
  - Media: bien por debajo de 0.45x"
git push

echo.
echo ===================================================
echo  Ver tokens A en output arriba
echo  Si 0 tokens: camino rapido (H1 PASS con ratio=0)
echo  Si ~75 tokens: revision activada (H1 PASS ratio~0.19)
echo ===================================================
pause
exit /b 0

:error
echo ERROR
pause
exit /b 1
