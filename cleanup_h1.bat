@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

echo Limpiando archivos temporales de trabajo...

del /f /q "cortex\_config_unified_patch.py" 2>nul
del /f /q "cortex\_method_new.py" 2>nul
del /f /q "cortex\_unified_review_method.py" 2>nul
del /f /q "cortex\_unified_review_patch.py" 2>nul
del /f /q "0.03)" 2>nul
del /f /q "1.7.2" 2>nul

git add -A
git commit -m "chore: limpieza archivos temporales de optimizacion H1

Eliminados:
  cortex/_config_unified_patch.py  (parche aplicado)
  cortex/_method_new.py            (parche aplicado)
  cortex/_unified_review_method.py (parche aplicado)
  cortex/_unified_review_patch.py  (parche aplicado)
  0.03)                            (archivo accidental del bat)
  1.7.2                            (archivo accidental)

H1 resultado final:
  A=121 tokens / B=401 tokens = 0.302x
  Objetivo pre-registrado: <=0.45x
  Estado: PASS"

git push

echo.
echo Hecho.
pause
