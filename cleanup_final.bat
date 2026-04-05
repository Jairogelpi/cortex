@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2

echo Limpiando archivos accidentales...
del /f /q "0.478" 2>nul
del /f /q "New" 2>nul
del /f /q "Cortex_V2_FINAL_v2.docx" 2>nul

echo Subiendo estado final del dia...
git add -A
git rm --cached "Cortex_V2_FINAL_v2.docx" 2>nul
git rm --cached "0.478" 2>nul

git commit -m "fix: limpieza archivos accidentales + requirements.txt completo

Archivos eliminados:
- 0.478 (0 bytes, accidental)
- Cortex_V2_FINAL_v2.docx (placeholder 11 bytes, no el paper real)

Fix requirements.txt:
- Anadido sseclient-py>=1.7.2 (faltaba, instalado por GitHub Actions)

Estado del proyecto al cierre del dia 5 abril 2026:
- 53/53 tests de integracion pasados
- E1 completado: 123 dias, delta_mean=0.7192
- E3: 50 pares generados (semilla=42)
- OSF: https://osf.io/wdkcx
- E2: arranca manana 09:00 UTC automaticamente
- PENDIENTE: verificar que GitHub Actions usa LLMs reales (no fallback)"

git push

echo.
echo ===================================================
echo  Estado final del proyecto:
echo.
echo  SOLIDO:
echo    53/53 tests pasados
echo    E1 completo con datos reales
echo    E3 50 pares listos para evaluadores
echo    OSF pre-registro sellado
echo    GitHub Actions configurado
echo.
echo  PENDIENTE MANANA:
echo    Verificar que el run de 09:00 UTC usa LLMs
echo    (no fallback deterministico)
echo    URL: https://github.com/Jairogelpi/cortex/actions
echo.
echo  ESTA SEMANA:
echo    Compartir e3_pairs.md con 3 evaluadores externos
echo    Actualizar el paper con resultados de E1
echo ===================================================
pause
