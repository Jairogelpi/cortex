@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
call venv\Scripts\activate.bat
echo.
echo ===================================================
echo  CORTEX V2 — Experimento E1 (backtesting rapido)
echo  Periodo: sept 2025 - mar 2026
echo  Sin llamadas LLM — puro deterministico
echo  Duracion estimada: 2-3 minutos
echo ===================================================
echo.
python -m experiments.e1_fast
pause
