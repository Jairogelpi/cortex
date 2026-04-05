@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

git add -A
git commit -m "feat: pre-registro OSF sellado — https://osf.io/wdkcx

Pre-registro publico: https://osf.io/wdkcx
Fecha: 5 de abril de 2026

Cambios en este commit:
- README.md: badge OSF + URL pre-registro + tabla H1-H7
- cortex/config.py: URL OSF en constante OSF_PREREGISTRATION
- docs/PRE_REGISTRO_OSF.md: documento completo de pre-registro

Parametros inmutables desde este momento:
  DELTA_BACKTRACK    = 0.65
  DELTA_CONSOLIDATE  = 0.70
  SIM_THRESHOLD      = 0.65
  STOP_LOSS_PCT      = 0.15

Test de integracion: 53/53 PASS
Pipeline validado con datos reales el 5/04/2026."

git push

echo.
echo ===================================================
echo  PRE-REGISTRO COMPLETO
echo.
echo  OSF:    https://osf.io/wdkcx
echo  GitHub: https://github.com/Jairogelpi/cortex
echo.
echo  Los parametros son inmutables desde este momento.
echo  Siguiente paso: Experimento E1 (backtesting)
echo ===================================================
pause
