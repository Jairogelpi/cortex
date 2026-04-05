@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
call venv\Scripts\activate.bat
echo.
echo Generando 50 pares E3 (muestreo estratificado, semilla=42)...
echo.
python -m experiments.e3_generate_pairs

echo.
echo Subiendo a GitHub...
git add -A
git commit -m "feat: E3 pares + fix workflow GitHub Actions 403

Fix workflow:
- permissions: contents: write a nivel global
- Elimina persist-credentials: false (causaba 403)
- Usa GITHUB_TOKEN por defecto (mas simple y fiable)
- Commit message incluye delta/regime del dia

E3 pares (50, estratificados, semilla=42):
- Estratos: clear gas(8) + clear lorenz(8) + rare(5) +
  frontier(10) + transitions(6) + overdamped(5) + weak(4) + fill(4)
- 40 porciento easy (ancla Cohen kappa), 60 porciento hard/medium
- Documento ciego para evaluadores: e3_pairs.md
- Limitaciones documentadas: sin R4, sin overdamped confirmado

OSF: https://osf.io/wdkcx"
git push

echo.
echo ===================================================
echo  LISTO
echo.
echo  1. Ve a GitHub Actions y lanza Run workflow
echo     El fix 403 esta aplicado
echo.
echo  2. Comparte experiments/e3_pairs.md con 3
echo     evaluadores externos (sin decirles que
echo     isomorfo eligio el sistema)
echo ===================================================
pause
