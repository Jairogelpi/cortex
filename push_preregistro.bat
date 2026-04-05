@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

echo Subiendo documentacion completa + pre-registro OSF a GitHub...

git add -A
git status

git commit -m "docs: documentacion completa + PRE_REGISTRO_OSF.md

Estado final del sistema validado con datos reales:
- 53/53 checks de integracion pasados
- FRED conectado (T10Y2Y=0.51)
- Lambda CONTRADICTED real verificado
- Phi temperature=0.0 reproducible (max_diff=0.0000)
- 4 HEARTBEATS reales en logs/cortex_20260405.jsonl

Documentos nuevos:
- docs/PRE_REGISTRO_OSF.md: parametros, hipotesis, experimentos
- docs/FASE_6_CAPA_SIGMA.md a FASE_9_CAPA_OMICRON.md
- docs/CHANGELOG_UMBRALES.md + PROPUESTA_AJUSTE_UMBRALES.md

Para pre-registrar: https://osf.io -> New Registration
Ver docs/PRE_REGISTRO_OSF.md seccion 8 para instrucciones exactas."

git push

echo.
echo ===================================================
echo  Documentacion subida a GitHub
echo.
echo  SIGUIENTE PASO: pre-registro OSF
echo  1. Ve a https://osf.io
echo  2. Crea proyecto: Cortex V2
echo  3. New Registration - OSF Preregistration
echo  4. Usa docs/PRE_REGISTRO_OSF.md como guia
echo ===================================================
pause
