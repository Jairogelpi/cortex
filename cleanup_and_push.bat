@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

echo Limpiando y subiendo estado final...

rem Eliminar archivo accidental
del /f /q 0.70 2>nul

rem Añadir todo
git add -A
git status

echo.
git commit -m "chore: limpieza post-setup + primer log Omicron

- Elimina archivo 0.70 accidental del script
- Actualiza .gitignore
- Incluye primer log real de Omicron (5 abril 2026)
- Repositorio listo para E1"

git push

echo.
echo ===================================================
echo  CORTEX V2 esta en GitHub
echo  https://github.com/Jairogelpi/cortex
echo.
echo  GitHub Actions ejecutara el pipeline cada dia
echo  a las 09:00 UTC (lunes a viernes)
echo.
echo  Siguiente paso: pre-registro en OSF
echo  https://osf.io
echo ===================================================
pause
