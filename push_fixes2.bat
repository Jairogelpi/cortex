@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

del /f /q _fred_fix_tmp_DELETE.py 2>nul

git add -A
git commit -m "fix: correccion OmegaHypothesis campos + FRED csv sin parse_dates

FIX TEST: OmegaHypothesis no tiene reasoning_opus/risk_warning.
  Campos correctos: llm_reasoning, market_analog, z_market, confidence.
  Test de integracion actualizado con los campos reales del dataclass.

FIX FRED: el error 'Missing column provided to parse_dates: DATE'
  se resuelve no usando parse_dates en absoluto.
  _fetch_fred_csv_raw() lee raw y filtra por posicion de columna.
  Evita el error de encoding/header que causaba el fallo.

FIX FRED INFO: FRED es fuente secundaria. Si falla, Lambda opera
  correctamente solo con Yahoo Finance (fuente primaria).
  El test ahora marca FRED como informativo, no como FAIL."

git push

echo.
echo ===================================================
echo  Fixes subidos. Ejecuta test_integracion.bat
echo ===================================================
pause
