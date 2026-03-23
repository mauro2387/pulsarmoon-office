// HUD: status bar superior, panel de detalle, minimap
// Renderiza sobre el canvas sin transformacion de camara

let _detailPanel = null;
const _MM_W = 180, _MM_H = 135, _MM_PAD = 10;

// --- Status bar (top 28px) ---
function renderStatusBar(c) {
  const w = canvas.width;
  c.fillStyle = 'rgba(8,8,20,0.88)';
  c.fillRect(0, 0, w, 28);
  c.fillStyle = 'rgba(255,255,255,0.08)';
  c.fillRect(0, 27, w, 1);

  const total = state.agents.size;
  const active = [...state.agents.values()].filter(a => a.status === 'working').length;
  const ws = state.wsConnected ? '● online' : '○ offline';
  const wsColor = state.wsConnected ? '#4ade80' : '#f87171';
  const time = new Date().toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });

  c.font = '11px monospace';
  c.textBaseline = 'middle';
  c.textAlign = 'left';
  c.fillStyle = '#d0d0e8';
  c.fillText(`◈ PulsarMoon Office  │  ${total} agentes  │  ${active} activos  │`, 12, 14);

  // WS status con color
  const baseW = c.measureText(`◈ PulsarMoon Office  │  ${total} agentes  │  ${active} activos  │ `).width;
  c.fillStyle = wsColor;
  c.fillText(ws, 12 + baseW, 14);

  const wsW = c.measureText(ws + '  │  ').width;
  c.fillStyle = '#8080a0';
  c.fillText(`│  ${time}`, 12 + baseW + wsW, 14);
}

// --- Minimap (esquina inferior derecha) ---
function renderMinimap(c) {
  const mx = canvas.width - _MM_W - _MM_PAD;
  const my = canvas.height - _MM_H - _MM_PAD;
  const sx = _MM_W / CONFIG.MAP_W;
  const sy = _MM_H / CONFIG.MAP_H;

  // Fondo
  c.fillStyle = 'rgba(8,8,20,0.85)';
  c.fillRect(mx, my, _MM_W, _MM_H);
  c.strokeStyle = 'rgba(255,255,255,0.1)';
  c.lineWidth = 1;
  c.strokeRect(mx, my, _MM_W, _MM_H);

  // Salas como rectangulos coloreados
  for (const room of ROOMS) {
    c.fillStyle = room.color;
    c.globalAlpha = 0.4;
    c.fillRect(
      Math.floor(mx + room.x * sx),
      Math.floor(my + room.y * sy),
      Math.ceil(room.w * sx),
      Math.ceil(room.h * sy)
    );
  }
  c.globalAlpha = 1;

  // Agentes como puntos 3x3 del color de su departamento
  for (const [, ch] of state.characters) {
    const pal = PALETTES[ch.dept];
    c.fillStyle = pal ? pal.primary : '#FFFFFF';
    const ax = Math.floor(mx + (ch.x / T) * sx);
    const ay = Math.floor(my + (ch.y / T) * sy);
    c.fillRect(ax - 1, ay - 1, 3, 3);
  }

  // Rectangulo del area visible
  const { x: camX, y: camY, zoom } = state.camera;
  const vx = Math.floor(mx + (camX / zoom / T) * sx);
  const vy = Math.floor(my + (camY / zoom / T) * sy);
  const vw = Math.floor((canvas.width / zoom / T) * sx);
  const vh = Math.floor((canvas.height / zoom / T) * sy);
  c.strokeStyle = 'rgba(255,255,255,0.5)';
  c.lineWidth = 1;
  c.strokeRect(vx, vy, vw, vh);
}

// --- Panel de detalle (HTML overlay, 280px slide-in) ---
function _createDetailPanel() {
  _detailPanel = document.createElement('div');
  _detailPanel.id = 'detail-panel';
  _detailPanel.className = 'hud-panel';
  document.getElementById('hud').appendChild(_detailPanel);
}

function showDetailPanel(agentId) {
  const agent = state.agents.get(agentId);
  const ch = state.characters.get(agentId);
  if (!agent || !ch || !_detailPanel) return;
  state.selectedAgent = agentId;
  const pal = PALETTES[ch.dept] || PALETTES.administrativo;
  const sc = { working:'#4ade80', idle:'#64748b', waiting:'#fbbf24', error:'#f87171', done:'#60a5fa' };
  const col = sc[agent.status] || '#64748b';
  _detailPanel.innerHTML =
    `<div class="dp-head">` +
      `<span class="dp-av" style="background:${pal.primary}"></span>` +
      `<span class="dp-name">${agent.agent_name || agentId}</span>` +
      `<button class="dp-x" onclick="hideDetailPanel()">×</button>` +
    `</div>` +
    `<div class="dp-status"><span class="dp-dot" style="background:${col}"></span>${agent.status || 'idle'}</div>` +
    `<hr class="dp-hr">` +
    `<div class="dp-row"><span class="dp-lbl">Dept:</span> ${agent.department || 'N/A'}</div>` +
    `<div class="dp-row"><span class="dp-lbl">Modelo:</span> ${agent.model || 'N/A'}</div>` +
    `<hr class="dp-hr">` +
    `<div class="dp-task-lbl">Tarea actual:</div>` +
    `<div class="dp-task">"${(agent.task || 'Sin tarea').replace(/"/g, '&quot;')}"</div>` +
    `<hr class="dp-hr">` +
    `<div class="dp-time">Última actualización: ${_timeAgo(agent.timestamp)}</div>`;
  _detailPanel.classList.add('open');
}

function hideDetailPanel() {
  state.selectedAgent = null;
  if (_detailPanel) _detailPanel.classList.remove('open');
}

function _timeAgo(ts) {
  if (!ts) return 'N/A';
  const d = Math.floor(Date.now() / 1000 - ts);
  if (d < 60) return `${d}s`;
  if (d < 3600) return `${Math.floor(d / 60)}m`;
  return `${Math.floor(d / 3600)}h`;
}

// --- Click en agente ---
function handleAgentClick(sx, sy) {
  const w = screenToWorld(sx, sy);
  let closest = null, best = Infinity;
  for (const [id, ch] of state.characters) {
    const d = Math.abs(ch.x - w.x) + Math.abs(ch.y - w.y);
    if (d < best && d < T * 2) { closest = id; best = d; }
  }
  if (closest) showDetailPanel(closest);
  else hideDetailPanel();
}

// --- Click en minimap → navegar ---
function handleMinimapClick(sx, sy) {
  const mx = canvas.width - _MM_W - _MM_PAD;
  const my = canvas.height - _MM_H - _MM_PAD;
  if (sx < mx || sx > mx + _MM_W || sy < my || sy > my + _MM_H) return false;
  const rx = (sx - mx) / _MM_W;
  const ry = (sy - my) / _MM_H;
  const wx = rx * CONFIG.MAP_W * T;
  const wy = ry * CONFIG.MAP_H * T;
  state.camera.x = wx * state.camera.zoom - canvas.width / 2;
  state.camera.y = wy * state.camera.zoom - canvas.height / 2;
  clampCamera();
  return true;
}

// --- Render principal del HUD ---
let _lastPanelRefresh = 0;
function renderHUD() {
  renderStatusBar(ctx);
  renderMinimap(ctx);
  // Actualizar panel cada 2s si esta abierto (no cada frame)
  const now = performance.now();
  if (state.selectedAgent && now - _lastPanelRefresh > 2000) {
    _lastPanelRefresh = now;
    showDetailPanel(state.selectedAgent);
  }
}

// --- Init ---
function initHUD() {
  _createDetailPanel();
}
