@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
call venv\Scripts\activate.bat
echo.
echo Analizando overdamped_system con datos reales de E1...
echo.
python -m experiments.e1_overdamped_analysis
pause
