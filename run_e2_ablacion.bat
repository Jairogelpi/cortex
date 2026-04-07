@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
set PYTHONIOENCODING=utf-8
call venv\Scripts\activate.bat

echo.
echo ===================================================
echo  TEST E2 CON TOKEN TRACKING REAL
echo  Ahora A muestra tokens REALES por capa
echo ===================================================
echo.

python run_ablacion.py
if errorlevel 1 goto error

echo.
python analisis_e2.py

echo.
git add -A
git commit -m "feat: H1 token tracking real — phi+kappa+omega+lambda

- cortex/token_tracker.py: contador global de tokens por capa
- phi.py, kappa.py, omega.py, lambda_.py: instrumentados
- pipeline.py: resetea tracker, devuelve tokens_total REAL
- e2_ablation.py: usa tokens reales de A (no estimacion 2800)
- Al ejecutar: H1 muestra tokens reales con desglose por capa"
git push

echo.
echo ===================================================
echo  OK. H1 ahora usa tokens reales.
echo ===================================================
pause
exit /b 0

:error
echo ERROR - ver output arriba
pause
exit /b 1
