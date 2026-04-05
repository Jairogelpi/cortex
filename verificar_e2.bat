@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

echo ===================================================
echo  VERIFICACION E2 — Comprobando que todo funciona
echo  antes del primer heartbeat automatico
echo ===================================================
echo.

call venv\Scripts\activate.bat

echo [1/4] Verificando que el pipeline corre localmente...
python -m cortex.pipeline
if errorlevel 1 (
    echo ERROR: el pipeline fallo localmente
    echo Revisa los mensajes de error antes de continuar
    pause
    exit /b 1
)

echo.
echo [2/4] Subiendo logs de hoy a GitHub...
git add logs/
git add data/checkpoints/
git status

git commit -m "data: logs reales del 5 abril 2026 (dia de validacion y E1)

Primer log real de Cortex V2 — datos de mercado del 5/04/2026:
  VIX=23.87, SPY=655.83, Momentum=-4.02%
  Regimen: INDETERMINATE
  Delta: 0.5961-0.5966
  Isomorfo: lorenz_attractor
  Decision: HOLD 100% cash

Este commit incluye los logs generados durante la validacion
del sistema y el experimento E1. GitHub Actions continuara
publicando logs automaticamente desde manana 09:00 UTC."

git push

echo.
echo [3/4] Verificando que el workflow esta en GitHub...
echo Abre esta URL para confirmarlo:
echo https://github.com/Jairogelpi/cortex/actions
echo.

echo [4/4] Verificar que los secrets estan configurados:
echo https://github.com/Jairogelpi/cortex/settings/secrets/actions
echo.
echo Secrets necesarios:
echo   ALPACA_API_KEY     — tu key de Alpaca
echo   ALPACA_SECRET_KEY  — tu secret de Alpaca
echo   OPENROUTER_API_KEY — tu key de OpenRouter
echo.
echo ===================================================
echo  RESULTADO: si los 3 secrets estan configurados
echo  y el pipeline corrio sin errores arriba,
echo  E2 arrancara automaticamente manana lunes
echo  a las 09:00 UTC (11:00 Madrid)
echo ===================================================
pause
