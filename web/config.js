// Configuracion global — WS_URL y API_URL NUNCA hardcodeadas en otro lado
// En produccion (Vercel), se setean via window.OFFICE_WS_URL / window.OFFICE_API_URL
// En desarrollo local, apuntan a localhost:8765 (WS + API en mismo puerto)
const CONFIG = {
  WS_URL:   window.OFFICE_WS_URL || 'wss://ws.vydre.me',
  API_URL:  window.OFFICE_API_URL || 'https://api.vydre.me',

  TILE_SIZE: 16,
  MAP_W:     80,
  MAP_H:     60,

  MIN_ZOOM:  1,
  MAX_ZOOM:  4,

  // Intervalo de reconexion WebSocket en ms
  WS_RECONNECT_DELAY: 3000,
};
