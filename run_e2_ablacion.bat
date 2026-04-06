@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
call venv\Scripts\activate.bat

echo.
echo ===================================================
echo  TEST E2 ABLACION — 4 condiciones
echo  D es deterministico (rapido)
echo  B, C, A usan LLMs (~3-5 min en total)
echo ===================================================
echo.

python -c "
from cortex.e2_ablation import run_e2_ablation
results = run_e2_ablation(['A','B','C','D'])
errors = [c for c,r in results.items() if 'error' in r]
if errors:
    print(f'ERROR en condiciones: {errors}')
    exit(1)
print('TODAS LAS CONDICIONES OK')
"

if errorlevel 1 (
    echo.
    echo Algunas condiciones fallaron.
    pause
    exit /b 1
)

echo.
echo Analisis de resultados:
python -m cortex.e2_analysis

echo.
git add -A
git commit -m "data: E2 ablacion — primer test condiciones A,B,C,D"
git push

echo.
echo ===================================================
echo  LISTO. Ver logs/e2_ablation_*.jsonl
echo ===================================================
pause
