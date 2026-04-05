@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

echo Limpiando archivos basura y subiendo estado final...

del /f /q "-0.30" 2>nul
del /f /q "New" 2>nul
del /f /q "_fred_fix_tmp_DELETE.py" 2>nul
del /f /q "push_docs.bat" 2>nul
del /f /q "push_fixes.bat" 2>nul
del /f /q "push_fixes2.bat" 2>nul
del /f /q "push_preregistro.bat" 2>nul
del /f /q "cleanup_and_push.bat" 2>nul
del /f /q "setup_github.bat" 2>nul
del /f /q "setup_actions.bat" 2>nul

git add -A
git status

git commit -m "chore: limpieza final + estado pre-registro OSF completo

Pre-registro OSF: https://osf.io/wdkcx (5 abril 2026)
Test integracion: 53/53 PASS
Pipeline: 10 capas validadas con datos reales

Estado del proyecto:
- Parametros inmutables en cortex/config.py
- Documentacion completa en docs/ (12 archivos)
- GitHub Actions configurado (heartbeat diario 09:00 UTC)
- Logs reales en logs/cortex_20260405.jsonl

Siguiente paso: Experimento E1 (backtesting sept 2025 - mar 2026)"

git push

echo.
echo ===================================================
echo  CORTEX V2 — Estado final
echo.
echo  GitHub: https://github.com/Jairogelpi/cortex
echo  OSF:    https://osf.io/wdkcx
echo  Test:   53/53 PASS
echo.
echo  Siguiente: Experimento E1
echo ===================================================
pause
