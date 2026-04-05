@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

git add -A
git commit -m "analysis: diagnostico overdamped_system + datos E1 completos

overdamped_system: diagnostico honesto
- Sim max = 0.7810, supero threshold 0.65 en 10 dias
- Supero a gas_expansion en 45 dias
- NUNCA GANO porque lorenz_attractor tuvo sim mayor en esos dias
- Patron geometrico correcto pero el mercado E1 no estuvo en
  estado de reversion lateral pura — lorenz dominaba por Z4/Z8

Conclusiones para el paper:
1. overdamped no es un error de diseno, es un isomorfo para un
   mercado que no existio en sept2025-mar2026
2. E3 debe incluir pares de mercado lateral para calibrarlo
3. E2 puede activarlo si el mercado entra en rango tras el
   deterioro actual (VIX bajando de 25 a 18)

Archivos nuevos:
- experiments/e1_overdamped_analysis.json
- experiments/e1_overdamped_diagnostico.md
- experiments/e1_analisis_sin_sesgos.md (actualizado)"

git push

echo.
echo ===================================================
echo  Analisis completo subido
echo  https://github.com/Jairogelpi/cortex
echo ===================================================
pause
