@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
call venv\Scripts\activate.bat

echo.
echo === TEST 1: Python funciona? ===
python --version
echo.

echo === TEST 2: Imports basicos ===
python -c "from cortex.config import config; print('config OK')"
echo.

echo === TEST 3: Import pipeline_d (deterministico) ===
python -c "from cortex.pipeline_d import run_pipeline_d; print('pipeline_d OK')"
echo.

echo === TEST 4: Correr solo Condicion D (sin LLM) ===
python -c "
from cortex.pipeline_d import run_pipeline_d
r = run_pipeline_d()
print('D OK:', r['decision'], r['delta'])
"
echo.

echo === TEST 5: Import e2_ablation ===
python -c "from cortex.e2_ablation import run_e2_ablation; print('e2_ablation OK')"
echo.

echo === TEST 6: Ablacion solo D (mas rapido) ===
python -c "
from cortex.e2_ablation import run_e2_ablation
r = run_e2_ablation(['D'])
print('Ablacion D OK')
"
echo.

echo === FIN DIAGNOSTICO ===
pause
