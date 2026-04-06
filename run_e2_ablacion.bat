@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
call venv\Scripts\activate.bat

echo.
echo === TEST 1: Condicion D (deterministico, sin LLM) ===
python test_d.py
if errorlevel 1 goto error

echo.
echo === TEST 2: Ablacion completa A+B+C+D ===
echo (tarda 3-5 minutos por las llamadas LLM)
echo.
python run_ablacion.py
if errorlevel 1 goto error

echo.
echo === TEST 3: Analisis de resultados ===
python analisis_e2.py

echo.
git add -A
git commit -m "data: E2 ablacion primer test local A,B,C,D"
git push

echo.
echo ===================================================
echo  E2 ABLACION OK
echo  Ver logs/e2_ablation_*.jsonl
echo ===================================================
pause
exit /b 0

:error
echo.
echo ERROR — ver mensaje arriba
pause
exit /b 1
