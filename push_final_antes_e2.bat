@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

echo Subiendo archivos pendientes antes del primer run de GitHub Actions...

git add -A
git status

git commit -m "chore: archivos pendientes antes de E2

- experiments/e1_overdamped_analysis.json
- experiments/e1_overdamped_diagnostico.md
- experiments/e1_overdamped_analysis.py (fix formato)
- push_overdamped.bat
- verificar_e2.bat

Todo listo para el primer heartbeat automatico de GitHub Actions."

git push

echo.
echo Listo. Ahora lanza el workflow manualmente en GitHub:
echo https://github.com/Jairogelpi/cortex/actions
echo Boton: Run workflow (arriba derecha)
pause
