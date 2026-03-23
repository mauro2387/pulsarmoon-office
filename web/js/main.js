// Punto de entrada — inicializa canvas, WebSocket y game loop

// --- Canvas ---
const canvas = document.getElementById('office');
const ctx    = canvas.getContext('2d');

ctx.imageSmoothingEnabled = false;

function resizeCanvas() {
  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;
  ctx.imageSmoothingEnabled = false;  // se resetea al cambiar size
}

window.addEventListener('resize', () => { resizeCanvas(); clampCamera(); });
resizeCanvas();

// --- WebSocket ---
let ws = null;

function connectWS() {
  console.log('[WS] Conectando a', CONFIG.WS_URL);
  ws = new WebSocket(CONFIG.WS_URL);

  ws.addEventListener('open', () => {
    console.log('[WS] Conectado');
    state.wsConnected = true;
    updateWSStatus(true);
    // Solicitar estado completo al conectar
    ws.send(JSON.stringify({ type: 'request_state' }));
  });

  ws.addEventListener('message', (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch (e) {
      console.error('[WS] JSON invalido:', e);
      return;
    }
    handleMessage(msg);
  });

  ws.addEventListener('close', () => {
    console.warn('[WS] Desconectado. Reintentando en', CONFIG.WS_RECONNECT_DELAY, 'ms');
    state.wsConnected = false;
    updateWSStatus(false);
    setTimeout(connectWS, CONFIG.WS_RECONNECT_DELAY);
  });

  ws.addEventListener('error', (err) => {
    console.error('[WS] Error:', err);
    // 'close' se dispara despues, maneja la reconexion
  });
}

function handleMessage(msg) {
  switch (msg.type) {
    case 'initial_state':
      state.agents.clear();
      for (const agent of msg.agents) {
        state.agents.set(agent.agent_id, agent);
      }
      console.log('[WS] Estado inicial recibido —', state.agents.size, 'agentes');
      syncCharacters(state.agents);
      break;

    case 'agent_update':
      state.agents.set(msg.agent.agent_id, msg.agent);
      console.log('[WS] Update:', msg.agent.agent_id, '—', msg.agent.status);
      syncCharacters(state.agents);
      break;

    case 'agent_removed':
      state.agents.delete(msg.agent_id);
      if (state.selectedAgent === msg.agent_id) state.selectedAgent = null;
      console.log('[WS] Agente eliminado:', msg.agent_id);
      syncCharacters(state.agents);
      break;

    case 'ping':
      ws.send(JSON.stringify({ type: 'pong' }));
      break;

    default:
      console.warn('[WS] Tipo desconocido:', msg.type);
  }
}

// --- Estado WS (el HUD status bar lo muestra) ---
function updateWSStatus(connected) {
  state.wsConnected = connected;
}

// --- Game loop ---
function loop(timestamp) {
  render(timestamp);
  requestAnimationFrame(loop);
}

// --- Click detection (diferenciar click de drag) ---
let _clickStart = null;
canvas.addEventListener('mousedown', e => {
  if (e.button === 0) _clickStart = { x: e.clientX, y: e.clientY };
});
canvas.addEventListener('mouseup', e => {
  if (!_clickStart || e.button !== 0) return;
  const dx = Math.abs(e.clientX - _clickStart.x);
  const dy = Math.abs(e.clientY - _clickStart.y);
  _clickStart = null;
  if (dx < 4 && dy < 4) _onCanvasClick(e.clientX, e.clientY);
});

// Touch tap
let _tapStart = null;
canvas.addEventListener('touchstart', e => {
  if (e.touches.length === 1) {
    _tapStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
  }
}, { passive: true });
canvas.addEventListener('touchend', e => {
  if (!_tapStart) return;
  const t = e.changedTouches[0];
  const dx = Math.abs(t.clientX - _tapStart.x);
  const dy = Math.abs(t.clientY - _tapStart.y);
  _tapStart = null;
  if (dx < 8 && dy < 8) _onCanvasClick(t.clientX, t.clientY);
});

function _onCanvasClick(sx, sy) {
  if (handleMinimapClick(sx, sy)) return;
  handleAgentClick(sx, sy);
}

// --- Init ---
renderFurnitureToBackground();
registerLivingAnimations();
initHUD();
initSocial();

initCamera(canvas);
centerCamera();
connectWS();
requestAnimationFrame(loop);
