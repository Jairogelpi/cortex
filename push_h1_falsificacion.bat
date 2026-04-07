@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

git add -A
git commit -m "docs: H1 falsificada con datos reales + analisis E2 actualizado

H1 resultado definitivo (7 abril 2026, dia 1 E2):
  Tokens A (real): 2284 — Phi=460 Kappa=172 Omega=722 Lambda=930
  Tokens B (real): 396
  Ratio: 5.77x (objetivo <=0.45x) -> FALSIFICADA

Nuevos documentos:
  experiments/h1_falsificacion.md — analisis completo sin sesgos
  experiments/e2_analisis_dia1.md — estado actualizado con datos reales

Per pre-registro OSF (osf.io/wdkcx):
  'Si alguna hipotesis se falsifica, se publica completo, no se oculta.'

Lo que esto NO invalida:
  - La arquitectura tecnica es correcta
  - H4, H5, H7 siguen siendo testeables
  - La ablacion ya muestra evidencia real (D BACKTRACK incorrecto)"

git push

echo.
echo ===================================================
echo  H1 documentada como falsificada.
echo  Ver experiments/h1_falsificacion.md
echo ===================================================
pause
