@echo off
REM PulsarMoon — Auto-start relay + tunnel al prender la PC
REM Se copia en: shell:startup

start "PulsarMoon Relay" cmd /k "cd /d C:\Users\mauro\OneDrive\Desktop\pulsarmoon-office && .venv\Scripts\python agents\desarrollo\relay_server.py"
timeout /t 3 /nobreak >nul
start "PulsarMoon Tunnel" cmd /k "cloudflared tunnel --config C:\Users\mauro\.cloudflared\bridge-config.yml run pulsarmoon-bridge"
