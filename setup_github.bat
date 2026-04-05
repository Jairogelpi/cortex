@echo off
echo ===================================================
echo  CORTEX V2 - Subir a GitHub
echo  github.com/jairogelpi/cortex
echo ===================================================
echo.

cd /d C:\Users\jairo\Desktop\cortex_v2

echo [1/6] Verificando Git instalado...
git --version
if errorlevel 1 (
    echo ERROR: Git no encontrado.
    echo Instala Git desde https://git-scm.com/download/win
    pause
    exit /b 1
)

echo.
echo [2/6] Inicializando repositorio local...
git init
git branch -M main

echo.
echo [3/6] Configurando identidad Git...
git config user.name "jairogelpi"
git config user.email "jairogelpi@users.noreply.github.com"

echo.
echo [4/6] Añadiendo archivos...
git add .
git status

echo.
echo [5/6] Primer commit...
git commit -m "feat: Cortex V2 completo - pipeline 10 capas validado con datos reales

- Phi: factorizador 8 dimensiones ortogonales (var=0.2594)
- Kappa: critic externo delta=0.5966 HOLD_CASH
- Omega: lorenz_attractor Sim=0.9645 con Claude Opus
- Lambda: validacion anti-sesgo Sim_adj=0.8445
- Mu: memoria selectiva sleep replay (umbral 0.70)
- Sigma: orquestador adaptativo HOLD
- Rho: checkpoint + stop-loss 15pct
- Tau: governance HITL paper trading
- Omicron: telemetria JSONL + Markdown diario
- DELTA_CONSOLIDATE ajustado 0.75->0.70 pre-OSF
- Validado con datos reales 5 abril 2026"

echo.
echo [6/6] Conectando con GitHub...
echo.
echo IMPORTANTE: Necesitas crear el repositorio en GitHub primero.
echo Ve a: https://github.com/new
echo Nombre: cortex
echo Visibilidad: Public
echo NO inicialices con README (ya tenemos uno)
echo.
echo Cuando lo hayas creado, ejecuta este comando:
echo.
echo   git remote add origin https://github.com/jairogelpi/cortex.git
echo   git push -u origin main
echo.
echo O copia y pega directamente:
echo git remote add origin https://github.com/jairogelpi/cortex.git ^&^& git push -u origin main
echo.
pause
