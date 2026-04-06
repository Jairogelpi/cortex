@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
set PYTHONIOENCODING=utf-8
call venv\Scripts\activate.bat

echo.
echo ===================================================
echo  TEST E2 ABLACION completa (A+B+C+D)
echo  (~3-5 min por llamadas LLM)
echo ===================================================
echo.

python run_ablacion.py
if errorlevel 1 (
    echo ERROR - ver output arriba
    pause
    exit /b 1
)

echo.
python analisis_e2.py

echo.
git add -A
git commit -m "data: E2 ablacion %date%"
git push

echo.
echo ===================================================
echo  OK - logs/e2_ablation_*.jsonl actualizado
echo ===================================================
pause
