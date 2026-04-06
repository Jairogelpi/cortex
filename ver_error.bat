@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
call venv\Scripts\activate.bat

echo Ejecutando diagnostico... > error_log.txt 2>&1

echo === TEST D === >> error_log.txt 2>&1
python test_d.py >> error_log.txt 2>&1
echo Codigo D: %ERRORLEVEL% >> error_log.txt 2>&1

echo === TEST ABLACION === >> error_log.txt 2>&1
python run_ablacion.py >> error_log.txt 2>&1
echo Codigo ablacion: %ERRORLEVEL% >> error_log.txt 2>&1

echo. >> error_log.txt 2>&1
echo FIN >> error_log.txt 2>&1

type error_log.txt

pause
