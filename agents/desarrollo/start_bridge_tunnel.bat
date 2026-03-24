@echo off
echo === PulsarMoon Bridge + Relay ===
echo.
echo Iniciando relay server...
start "Relay Server" cmd /k "cd /d C:\Users\mauro\OneDrive\Desktop\pulsarmoon-office && .venv\Scripts\python agents\desarrollo\relay_server.py"
echo.
echo Iniciando Cloudflare Tunnel para bridge...
cloudflared tunnel --config C:\Users\mauro\.cloudflared\bridge-config.yml run pulsarmoon-bridge
pause
