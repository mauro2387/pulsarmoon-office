// Camara: pan drag, zoom entero 1-4 hacia cursor, clamp, conversiones de coordenadas

let _isDragging = false;
let _dragStart  = { x: 0, y: 0 };
let _camStart   = { x: 0, y: 0 };

function initCamera(canvas) {
  canvas.addEventListener('mousedown',  _onMouseDown);
  canvas.addEventListener('mousemove',  _onMouseMove);
  canvas.addEventListener('mouseup',    _onMouseUp);
  canvas.addEventListener('mouseleave', _onMouseUp);
  canvas.addEventListener('wheel',      _onWheel, { passive: false });
  window.addEventListener('keydown',    _onKeyDown);

  // Soporte touch para mobile
  canvas.addEventListener('touchstart', _onTouchStart, { passive: false });
  canvas.addEventListener('touchmove',  _onTouchMove,  { passive: false });
  canvas.addEventListener('touchend',   _onTouchEnd);
}

function _onMouseDown(e) {
  if (e.button !== 0) return;
  _isDragging = true;
  _dragStart  = { x: e.clientX, y: e.clientY };
  _camStart   = { x: state.camera.x, y: state.camera.y };
}

function _onMouseMove(e) {
  if (!_isDragging) return;
  state.camera.x = _camStart.x - (e.clientX - _dragStart.x);
  state.camera.y = _camStart.y - (e.clientY - _dragStart.y);
  clampCamera();
}

function _onMouseUp() {
  _isDragging = false;
}

function _onWheel(e) {
  e.preventDefault();
  const oldZoom = state.camera.zoom;
  const delta   = e.deltaY < 0 ? 1 : -1;
  const newZoom = Math.min(CONFIG.MAX_ZOOM, Math.max(CONFIG.MIN_ZOOM, oldZoom + delta));
  if (newZoom === oldZoom) return;

  // Zoom hacia el punto del mundo bajo el cursor
  const rect = e.target.getBoundingClientRect();
  const sx   = e.clientX - rect.left;
  const sy   = e.clientY - rect.top;

  // Coordenada mundo (px 1x) bajo el cursor antes del zoom
  const wx = (sx + state.camera.x) / oldZoom;
  const wy = (sy + state.camera.y) / oldZoom;

  state.camera.zoom = newZoom;
  state.camera.x    = wx * newZoom - sx;
  state.camera.y    = wy * newZoom - sy;
  clampCamera();
}

function _onKeyDown(e) {
  if (e.key === 'Escape') {
    state.selectedAgent = null;
  }
  if (e.key === ' ') {
    e.preventDefault();
    centerCamera();
  }
}

// --- Touch ---
let _touchDragStart = { x: 0, y: 0 };
let _touchCamStart  = { x: 0, y: 0 };

function _onTouchStart(e) {
  if (e.touches.length !== 1) return;
  e.preventDefault();
  _isDragging      = true;
  _touchDragStart  = { x: e.touches[0].clientX, y: e.touches[0].clientY };
  _touchCamStart   = { x: state.camera.x, y: state.camera.y };
}

function _onTouchMove(e) {
  if (!_isDragging || e.touches.length !== 1) return;
  e.preventDefault();
  state.camera.x = _touchCamStart.x - (e.touches[0].clientX - _touchDragStart.x);
  state.camera.y = _touchCamStart.y - (e.touches[0].clientY - _touchDragStart.y);
  clampCamera();
}

function _onTouchEnd() {
  _isDragging = false;
}

// --- Utilidades publicas ---

// Clampea la camara a los limites del mundo
function clampCamera() {
  const { zoom } = state.camera;
  const maxX = CONFIG.MAP_W * CONFIG.TILE_SIZE * zoom - window.innerWidth;
  const maxY = CONFIG.MAP_H * CONFIG.TILE_SIZE * zoom - window.innerHeight;
  state.camera.x = Math.max(0, Math.min(state.camera.x, Math.max(0, maxX)));
  state.camera.y = Math.max(0, Math.min(state.camera.y, Math.max(0, maxY)));
}

// Centra la camara en el mapa (usado en init y tecla Espacio)
function centerCamera() {
  const { zoom } = state.camera;
  state.camera.x = Math.max(0, (CONFIG.MAP_W * CONFIG.TILE_SIZE * zoom - window.innerWidth)  / 2);
  state.camera.y = Math.max(0, (CONFIG.MAP_H * CONFIG.TILE_SIZE * zoom - window.innerHeight) / 2);
  clampCamera();
}

// wx, wy en pixels mundo (1x) → coordenadas de pantalla
function worldToScreen(wx, wy) {
  const { x, y, zoom } = state.camera;
  return {
    x: Math.floor(wx * zoom - x),
    y: Math.floor(wy * zoom - y),
  };
}

// sx, sy en pixels de pantalla → coordenadas mundo (1x)
function screenToWorld(sx, sy) {
  const { x, y, zoom } = state.camera;
  return {
    x: (sx + x) / zoom,
    y: (sy + y) / zoom,
  };
}
