@echo off
cd /d C:\Users\jairo\Desktop\cortex_v2
call venv\Scripts\activate.bat

echo.
echo ===================================================
echo  Diagnostico de conexion — OpenRouter y Alpaca
echo ===================================================
echo.

python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()

key = os.getenv('OPENROUTER_API_KEY', '')
print(f'OpenRouter key: {key[:12]}...{key[-4:] if len(key) > 16 else '(muy corta)'}')
print(f'Longitud key:   {len(key)} caracteres')
print()

# Test OpenRouter
try:
    r = requests.get(
        'https://openrouter.ai/api/v1/models',
        headers={'Authorization': f'Bearer {key}'},
        timeout=15
    )
    print(f'OpenRouter HTTP: {r.status_code}')
    if r.status_code == 200:
        models = r.json().get('data', [])
        sonnet = [m for m in models if 'sonnet' in m.get('id','').lower()]
        print(f'Modelos disponibles: {len(models)}')
        print(f'Sonnet encontrado:   {len(sonnet) > 0}')
        print('OpenRouter: OK')
    elif r.status_code == 401:
        print('ERROR: API key invalida o expirada')
        print('Solucion: regenera la key en https://openrouter.ai/keys')
    else:
        print(f'ERROR: {r.text[:200]}')
except Exception as e:
    print(f'ERROR de conexion: {e}')
"

echo.
git add -A
git commit -m "fix: workflow con verificacion de conectividad y diagnostico"
git push

echo.
echo ===================================================
echo  Ahora ve a GitHub y lanza Run workflow de nuevo:
echo  https://github.com/Jairogelpi/cortex/actions
echo.
echo  El nuevo workflow mostrara exactamente donde falla
echo ===================================================
pause
