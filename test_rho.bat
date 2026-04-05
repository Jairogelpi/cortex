@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
call venv\Scripts\activate.bat
python -m cortex.layers.rho_test
pause
