@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

echo Subiendo fixes reales a GitHub...

git add -A
git status

git commit -m "fix: tres correcciones reales en Lambda, Phi y test integracion

FIX 1 - FRED multiples estrategias:
  Lambda._get_fred_data() ahora intenta:
  1. CSV publico fredgraph.csv (requests directo, sin auth)
  2. FRED JSON API con endpoint alternativo
  Antes fallaba siempre. Ahora obtiene T10Y2Y y VIXCLS reales.

FIX 2 - Penalizaciones Lambda calibradas para CONTRADICTED real:
  Antes: penalizacion maxima -0.12 (nunca alcanzaba CONTRADICTED)
  Ahora: penalizacion hasta -0.55 segun magnitud real de la contradiccion
  VIX bajando >8pts -> -0.30 | momentum 5d >4% -> -0.20
  Test verifica: mercado bajista vs gas_expansion -> CONTRADICTED/UNCERTAIN

FIX 3 - Phi acepta temperature parameter:
  PhiLayer(temperature=0.0) para Lambda interna (reproducible)
  PhiLayer(temperature=0.1) para Phi principal (razonamiento rico)
  Test verifica: dos ejecuciones con temp=0.0 difieren <0.05 en Z

Test integracion actualizado:
  - Verifica FRED conectado (datos reales)
  - Verifica CONTRADICTED con escenario bajista forzado
  - Verifica reproducibilidad Phi temperature=0.0"

git push

echo.
echo ===================================================
echo  Fixes subidos a GitHub
echo  https://github.com/Jairogelpi/cortex
echo ===================================================
pause
