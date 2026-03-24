# Setup del tunnel de Cloudflare para el relay bridge
# Ejecutar UNA VEZ desde PowerShell con permisos de admin

Write-Host "=== PulsarMoon Bridge Tunnel Setup ===" -ForegroundColor Cyan

# Crear tunnel
Write-Host "Creando tunnel..." -ForegroundColor Yellow
$output = cloudflared tunnel create pulsarmoon-bridge 2>&1
Write-Host $output

# Extraer tunnel ID del output o de los archivos
$tunnelId = (cloudflared tunnel list --name pulsarmoon-bridge --output json | ConvertFrom-Json).id
if (-not $tunnelId) {
    Write-Host "Error: no se pudo obtener el tunnel ID" -ForegroundColor Red
    exit 1
}
Write-Host "Tunnel ID: $tunnelId" -ForegroundColor Green

# Crear config
$configContent = @"
tunnel: $tunnelId
credentials-file: C:\Users\mauro\.cloudflared\$tunnelId.json

ingress:
  - hostname: bridge.vydre.me
    service: http://localhost:7820
  - hostname: forms.vydre.me
    service: http://localhost:7820
  - service: http_status:404
"@

$configPath = "C:\Users\mauro\.cloudflared\bridge-config.yml"
$configContent | Out-File -FilePath $configPath -Encoding UTF8
Write-Host "Config guardada en: $configPath" -ForegroundColor Green

# Agregar DNS
Write-Host "Configurando DNS..." -ForegroundColor Yellow
cloudflared tunnel route dns pulsarmoon-bridge bridge.vydre.me
cloudflared tunnel route dns pulsarmoon-bridge forms.vydre.me

Write-Host ""
Write-Host "=== Setup completado ===" -ForegroundColor Green
Write-Host ""
Write-Host "Para iniciar el tunnel:" -ForegroundColor Cyan
Write-Host "cloudflared tunnel --config $configPath run pulsarmoon-bridge"
