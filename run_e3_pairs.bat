@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
call venv\Scripts\activate.bat
echo.
python -m experiments.e3_generate_pairs
if errorlevel 1 (
    echo.
    echo ERROR en la generacion de pares
    pause
    exit /b 1
)
echo.
git add -A
git commit -m "data: E3 pares generados (50, semilla=42, estratificados)"
git push
echo.
echo ===================================================
echo  LISTO
echo  Comparte experiments/e3_pairs.md con evaluadores
echo ===================================================
pause
