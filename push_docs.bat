@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

echo Subiendo documentacion y tests completos a GitHub...

git add .
git status

git commit -m "docs+tests: documentacion completa 10 capas + test integracion

Documentacion nueva:
- docs/FASE_6_CAPA_SIGMA.md
- docs/FASE_7_CAPA_RHO.md
- docs/FASE_8_CAPA_TAU.md
- docs/FASE_9_CAPA_OMICRON.md

Tests nuevos:
- cortex/layers/sigma_test.py
- cortex/layers/rho_test.py
- cortex/layers/tau_test.py
- cortex/layers/omicron_test.py
- tests/test_integration.py (verifica invariantes del paper)

Todas las 10 capas documentadas individualmente.
Test de integracion verifica coherencia del pipeline completo."

git push

echo.
echo ===================================================
echo  GitHub actualizado
echo  https://github.com/Jairogelpi/cortex
echo ===================================================
pause
