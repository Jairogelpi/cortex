@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
call venv\Scripts\activate.bat
echo.
echo Generando 50 pares para E3...
echo.
python -m experiments.e3_generate_pairs
pause
