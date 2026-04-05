@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
call venv\Scripts\activate.bat
echo.
echo ===================================================
echo  CORTEX V2 - Test de Integracion Completo
echo  Verifica las 10 capas + invariantes del paper
echo ===================================================
echo.
python -m tests.test_integration
if errorlevel 1 (
    echo.
    echo RESULTADO: ALGUNOS TESTS FALLARON
    echo Revisa los mensajes de error arriba.
) else (
    echo.
    echo RESULTADO: TODOS LOS TESTS PASARON
)
pause
