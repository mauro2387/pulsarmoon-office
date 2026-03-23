// Layout del mapa: salas, grid walkable, offscreen canvas del fondo
// Rediseño completo — pasillos 3 tiles, paredes 3D, conectividad total

const ROOMS = [
  // --- Columna izquierda (x:0-19) ---
  { id:'direccion',     name:'Dirección',     color:'#7F77DD', x:0,  y:0,  w:20, h:13, desks:3 },
  { id:'ux_ui',         name:'UX / UI',       color:'#1D9E75', x:0,  y:16, w:20, h:13, desks:4 },
  { id:'marketing',     name:'Marketing',     color:'#D85A30', x:0,  y:32, w:20, h:13, desks:5 },
  { id:'oportunidades', name:'Oportunidades', color:'#D4537E', x:0,  y:48, w:20, h:13, desks:4 },

  // --- Columna derecha (x:23-42) ---
  { id:'desarrollo',    name:'Desarrollo',    color:'#378ADD', x:23, y:0,  w:20, h:13, desks:5 },
  { id:'qa',            name:'QA',            color:'#639922', x:23, y:16, w:20, h:13, desks:4 },
  { id:'atencion',      name:'Atención',      color:'#BA7517', x:23, y:32, w:20, h:13, desks:4 },
  { id:'administrativo',name:'Admin',         color:'#888780', x:23, y:48, w:20, h:13, desks:4 },

  // --- Columna derecha ancha (x:46-67) ---
  { id:'servidores',    name:'Servidores',    color:'#2C2C2A', x:46, y:0,  w:22, h:15, desks:0 },
  { id:'living',        name:'Living',        color:'#E8A838', x:46, y:16, w:22, h:30, desks:0 },
];

const FLOOR_COLORS = {
  direccion:     'rgba(127,119,221,0.18)',
  desarrollo:    'rgba(55,138,221,0.18)',
  ux_ui:         'rgba(29,158,117,0.18)',
  qa:            'rgba(99,153,34,0.18)',
  marketing:     'rgba(216,90,48,0.18)',
  atencion:      'rgba(186,117,23,0.18)',
  oportunidades: 'rgba(212,83,126,0.18)',
  administrativo:'rgba(136,135,128,0.18)',
  living:        'rgba(232,168,56,0.12)',
  servidores:    'rgba(44,44,42,0.55)',
};

const T  = CONFIG.TILE_SIZE;
const MW = CONFIG.MAP_W;
const MH = CONFIG.MAP_H;

// Colores de pared 3D
const WALL_SHADOW   = '#06060f';
const WALL_BODY     = '#10102a';
const WALL_HILIGHT  = '#222244';
const WALL_INNER    = '#191932';

// Colores de pasillo (cálidos, visibles)
const CORRIDOR_BG   = '#1a1520';
const CORRIDOR_TILE  = '#221a2d';
const CORRIDOR_LINE  = '#302848';

// Offscreen canvas del fondo
const bgCanvas = document.createElement('canvas');
bgCanvas.width  = MW * T;
bgCanvas.height = MH * T;
const bgCtx = bgCanvas.getContext('2d');
bgCtx.imageSmoothingEnabled = false;

// Grid walkable
let walkableGrid = [];

function _setWalkable(y, x, val) {
  if (y >= 0 && y < MH && x >= 0 && x < MW && walkableGrid[y]) {
    walkableGrid[y][x] = val;
  }
}

// --- Definicion de pasillos ---
// Verticales (3 tiles ancho)
const V_CORRIDORS = [
  { x: 20, w: 3, yStart: 0, yEnd: MH },   // entre col izq y der
  { x: 43, w: 3, yStart: 0, yEnd: MH },   // entre col der y living/serv
];

// Horizontales (3 tiles alto)
const H_CORRIDORS = [
  { y: 13, h: 3, xStart: 0, xEnd: 46 },   // entre fila 0 y fila 1
  { y: 29, h: 3, xStart: 0, xEnd: 46 },   // entre fila 1 y fila 2
  { y: 45, h: 3, xStart: 0, xEnd: 46 },   // entre fila 2 y fila 3
];

function buildWalkableGrid() {
  if (!MH || !MW || MH <= 0 || MW <= 0) {
    console.error('[map] MH o MW invalido:', MH, MW);
    return;
  }

  walkableGrid = [];
  for (let y = 0; y < MH; y++) {
    walkableGrid[y] = new Array(MW).fill(false);
  }

  // Interior de cada sala
  for (const r of ROOMS) {
    const yS = Math.max(0, r.y + 1);
    const yE = Math.min(MH - 1, r.y + r.h - 2);
    const xS = Math.max(0, r.x + 1);
    const xE = Math.min(MW - 1, r.x + r.w - 2);
    for (let ty = yS; ty <= yE; ty++) {
      for (let tx = xS; tx <= xE; tx++) {
        walkableGrid[ty][tx] = true;
      }
    }
  }

  // Pasillos verticales
  for (const vc of V_CORRIDORS) {
    for (let ty = vc.yStart; ty < vc.yEnd; ty++) {
      for (let dx = 0; dx < vc.w; dx++) {
        _setWalkable(ty, vc.x + dx, true);
      }
    }
  }

  // Pasillos horizontales
  for (const hc of H_CORRIDORS) {
    for (let dy = 0; dy < hc.h; dy++) {
      for (let tx = hc.xStart; tx < hc.xEnd; tx++) {
        _setWalkable(hc.y + dy, tx, true);
      }
    }
  }

  // Area abierta a la derecha (cols 46-67, fuera de salas)
  for (let ty = 38; ty < MH; ty++) {
    for (let tx = 46; tx < 68; tx++) {
      _setWalkable(ty, tx, true);
    }
  }
  // Corridor connection to living/servidores from left
  for (let ty = 0; ty < 38; ty++) {
    for (let tx = 43; tx < 46; tx++) {
      _setWalkable(ty, tx, true);
    }
  }

  console.log('[map] walkableGrid construido:', MH, 'x', MW);
}

// --- Dibujar pared 3D de un tile (16x16 px) con profundidad ---
function _drawWall3D(c, px, py, roomColor, isBottom, isRight) {
  const sz = T;
  const sh = 5; // shadow thickness
  const hl = 2; // highlight thickness

  // 1. Shadow base (fills the whole tile as shadow)
  c.fillStyle = WALL_SHADOW;
  c.fillRect(px, py, sz, sz);

  // 2. Wall body (inset from shadow)
  c.fillStyle = WALL_BODY;
  c.fillRect(px + hl, py + hl, sz - sh, sz - sh);

  // 3. Top highlight
  c.fillStyle = WALL_HILIGHT;
  c.fillRect(px, py, sz, hl);

  // 4. Left highlight
  c.fillStyle = WALL_HILIGHT;
  c.fillRect(px, py, hl, sz);

  // 5. Bottom shadow (darker for south walls)
  if (isBottom) {
    c.fillStyle = '#040408';
    c.fillRect(px, py + sz - sh, sz, sh);
  }

  // 6. Right shadow
  if (isRight) {
    c.fillStyle = '#040408';
    c.fillRect(px + sz - 3, py, 3, sz);
  }

  // 7. Room color accent line (subtle inner glow)
  c.fillStyle = roomColor;
  c.globalAlpha = 0.2;
  c.fillRect(px + hl + 1, py + hl + 1, sz - sh - 2, 1);
  c.fillRect(px + hl + 1, py + hl + 1, 1, sz - sh - 2);
  c.globalAlpha = 1;
}

// --- Dibujar piso de pasillo con baldosas ---
function _drawCorridorFloor(c, px, py) {
  c.fillStyle = CORRIDOR_BG;
  c.fillRect(px, py, T, T);

  // Baldosa interior
  c.fillStyle = CORRIDOR_TILE;
  c.fillRect(px + 1, py + 1, T - 2, T - 2);

  // Lineas de grout visibles
  c.fillStyle = CORRIDOR_LINE;
  c.globalAlpha = 0.55;
  c.fillRect(px, py, T, 1);
  c.fillRect(px, py, 1, T);
  c.globalAlpha = 0.3;
  c.fillRect(px + T - 1, py, 1, T);
  c.fillRect(px, py + T - 1, T, 1);
  c.globalAlpha = 1;
}

// --- Lampara de pared en pasillo con halo grande ---
function _drawWallLamp(c, px, py) {
  // Halo de luz calida (radio 20px)
  c.fillStyle = '#FFEE88';
  c.globalAlpha = 0.08;
  c.beginPath();
  c.arc(px + 8, py + 8, 20, 0, Math.PI * 2);
  c.fill();
  c.globalAlpha = 0.15;
  c.beginPath();
  c.arc(px + 8, py + 8, 12, 0, Math.PI * 2);
  c.fill();
  c.globalAlpha = 1;

  // Base metalica
  c.fillStyle = '#4A4A5A';
  c.fillRect(px + 5, py + 2, 6, 4);
  // Foco
  c.fillStyle = '#FFEE88';
  c.fillRect(px + 5, py + 6, 6, 3);
  c.fillStyle = '#FFDD44';
  c.fillRect(px + 6, py + 6, 4, 2);
}

// --- Puerta con marco decorativo ---
function _drawDoor(c, tx, ty, tileW, tileH, roomColor) {
  const px = tx * T;
  const py = ty * T;
  const pw = tileW * T;
  const ph = tileH * T;

  // Piso del pasillo en la puerta
  for (let dx = 0; dx < tileW; dx++) {
    for (let dy = 0; dy < tileH; dy++) {
      _drawCorridorFloor(c, (tx + dx) * T, (ty + dy) * T);
    }
  }

  // Marco izquierdo
  c.fillStyle = roomColor;
  c.globalAlpha = 0.7;
  c.fillRect(px - 1, py, 2, ph);

  // Marco derecho
  c.fillRect(px + pw - 1, py, 2, ph);
  c.globalAlpha = 1;

  // Luz verde indicando puerta abierta (arriba del marco)
  c.fillStyle = '#44FF44';
  c.globalAlpha = 0.8;
  const lightX = px + Math.floor(pw / 2) - 2;
  c.fillRect(lightX, py - 3, 4, 2);
  c.globalAlpha = 0.3;
  c.fillRect(lightX - 2, py - 4, 8, 4);
  c.globalAlpha = 1;
}

// --- buildMap ---
function buildMap() {
  const c = bgCtx;

  // 1. Fondo base muy oscuro
  c.fillStyle = '#080812';
  c.fillRect(0, 0, MW * T, MH * T);

  // 2. Pintar todos los pasillos con piso de baldosa
  // Verticales
  for (const vc of V_CORRIDORS) {
    for (let ty = vc.yStart; ty < vc.yEnd; ty++) {
      for (let dx = 0; dx < vc.w; dx++) {
        _drawCorridorFloor(c, (vc.x + dx) * T, ty * T);
      }
    }
  }
  // Horizontales
  for (const hc of H_CORRIDORS) {
    for (let dy = 0; dy < hc.h; dy++) {
      for (let tx = hc.xStart; tx < hc.xEnd; tx++) {
        _drawCorridorFloor(c, tx * T, (hc.y + dy) * T);
      }
    }
  }
  // Area abierta derecha (fuera de salas)
  for (let ty = 38; ty < MH; ty++) {
    for (let tx = 46; tx < 68; tx++) {
      _drawCorridorFloor(c, tx * T, ty * T);
    }
  }
  for (let ty = 15; ty < 16; ty++) {
    for (let tx = 43; tx < 46; tx++) {
      _drawCorridorFloor(c, tx * T, ty * T);
    }
  }

  // Lamparas en pasillos cada 8 tiles
  for (const vc of V_CORRIDORS) {
    for (let ty = vc.yStart + 2; ty < vc.yEnd; ty += 8) {
      _drawWallLamp(c, vc.x * T, ty * T);
      _drawWallLamp(c, (vc.x + vc.w - 1) * T, ty * T);
    }
  }
  for (const hc of H_CORRIDORS) {
    for (let tx = hc.xStart + 2; tx < hc.xEnd; tx += 8) {
      _drawWallLamp(c, tx * T, hc.y * T);
    }
  }

  // 3. Salas con paredes 3D
  for (const room of ROOMS) {
    const rx = room.x, ry = room.y, rw = room.w, rh = room.h;

    // --- Paredes 3D tile por tile ---
    // Pared superior
    for (let tx = rx; tx < rx + rw; tx++) {
      _drawWall3D(c, tx * T, ry * T, room.color, false, false);
    }
    // Pared inferior
    for (let tx = rx; tx < rx + rw; tx++) {
      _drawWall3D(c, tx * T, (ry + rh - 1) * T, room.color, true, false);
    }
    // Pared izquierda
    for (let ty = ry + 1; ty < ry + rh - 1; ty++) {
      _drawWall3D(c, rx * T, ty * T, room.color, false, false);
    }
    // Pared derecha
    for (let ty = ry + 1; ty < ry + rh - 1; ty++) {
      _drawWall3D(c, (rx + rw - 1) * T, ty * T, room.color, false, true);
    }

    // --- Piso interior ---
    const ix = (rx + 1) * T;
    const iy = (ry + 1) * T;
    const iw = (rw - 2) * T;
    const ih = (rh - 2) * T;

    c.fillStyle = room.id === 'living' ? '#141824' : '#13132a';
    c.fillRect(ix, iy, iw, ih);

    c.fillStyle = FLOOR_COLORS[room.id] || 'rgba(255,255,255,0.1)';
    c.fillRect(ix, iy, iw, ih);

    // Carpet in living room
    if (room.id === 'living') {
      const cpx = ix + 3 * T, cpy = iy + 4 * T;
      const cpw = (rw - 8) * T, cph = (rh - 12) * T;
      // Border
      c.fillStyle = '#4A2520';
      c.globalAlpha = 0.5;
      c.fillRect(cpx - 2, cpy - 2, cpw + 4, cph + 4);
      // Carpet body
      c.fillStyle = '#6B3A2A';
      c.globalAlpha = 0.35;
      c.fillRect(cpx, cpy, cpw, cph);
      // Inner pattern
      c.strokeStyle = '#8B5A3A';
      c.globalAlpha = 0.2;
      c.lineWidth = 1;
      c.strokeRect(cpx + 4, cpy + 4, cpw - 8, cph - 8);
      c.globalAlpha = 1;
    }

    // Grilla sutil del piso
    c.strokeStyle = room.color;
    c.globalAlpha = 0.04;
    c.lineWidth = 1;
    for (let gx = ix; gx <= ix + iw; gx += 2 * T) {
      c.beginPath(); c.moveTo(gx, iy); c.lineTo(gx, iy + ih); c.stroke();
    }
    for (let gy = iy; gy <= iy + ih; gy += 2 * T) {
      c.beginPath(); c.moveTo(ix, gy); c.lineTo(ix + iw, gy); c.stroke();
    }
    c.globalAlpha = 1;

    // Sombra interior (profundidad)
    c.fillStyle = '#000000';
    c.globalAlpha = 0.25;
    c.fillRect(ix, iy, iw, 3);
    c.fillRect(ix, iy, 3, ih);
    c.globalAlpha = 0.1;
    c.fillRect(ix, iy + ih - 2, iw, 2);
    c.fillRect(ix + iw - 2, iy, 2, ih);
    c.globalAlpha = 1;

    // --- Puertas ---
    const doorCenterX = rx + Math.floor(rw / 2) - 1;
    const doorCenterY = ry + Math.floor(rh / 2) - 1;

    // Puerta inferior (conecta a pasillo horizontal debajo)
    if (room.id !== 'servidores' && ry + rh <= 61) {
      _drawDoor(c, doorCenterX, ry + rh - 1, 3, 1, room.color);
    }

    // Puerta superior (conecta a pasillo horizontal arriba)
    if (ry > 0 && ry >= 16 && room.id !== 'servidores') {
      _drawDoor(c, doorCenterX, ry, 3, 1, room.color);
    }

    // Puerta derecha (salas col izq → pasillo vertical)
    if (rx + rw === 20) {
      _drawDoor(c, rx + rw - 1, doorCenterY, 1, 3, room.color);
    }

    // Puerta izquierda (salas col der → pasillo vertical)
    if (rx === 23) {
      _drawDoor(c, rx, doorCenterY, 1, 3, room.color);
    }

    // Puerta derecha de col derecha → pasillo hacia living/serv
    if (rx === 23 && rx + rw === 43) {
      _drawDoor(c, rx + rw - 1, doorCenterY, 1, 3, room.color);
    }

    // Puerta izquierda de living/servidores
    if (rx === 46) {
      _drawDoor(c, rx, doorCenterY, 1, 3, room.color);
    }

    // --- Nombre del departamento ---
    const fontSize = room.id === 'servidores' ? 9 : (room.id === 'living' ? 12 : 10);
    c.font = `bold ${fontSize}px monospace`;
    c.textAlign = 'center';
    c.textBaseline = 'middle';

    const cx = rx * T + rw * T / 2;
    const cy = ry * T + rh * T / 2;

    c.fillStyle = '#000000';
    c.globalAlpha = 0.5;
    c.fillText(room.name, cx + 1, cy + 1);

    c.fillStyle = room.color;
    c.globalAlpha = 0.85;
    c.fillText(room.name, cx, cy);
    c.globalAlpha = 1;
  }

  // 4. Plants at corridor intersections
  const intersections = [
    { x: 20, y: 13 }, { x: 20, y: 29 }, { x: 20, y: 45 },
    { x: 43, y: 13 }, { x: 43, y: 29 }, { x: 43, y: 45 },
  ];
  for (const int of intersections) {
    // Small decorative plant in corner of intersection
    if (typeof drawFurnitureSprite === 'function') {
      drawFurnitureSprite(c, 'plant', int.x * T, int.y * T, 1);
    }
  }

  // 5. Water coolers at main intersections
  const wcPositions = [{ x: 22, y: 14 }, { x: 22, y: 30 }];
  for (const wc of wcPositions) {
    if (typeof drawFurnitureSprite === 'function') {
      drawFurnitureSprite(c, 'water_cooler', wc.x * T, wc.y * T, 1);
    }
  }

  // 6. Borde exterior
  c.strokeStyle = '#1a1a3a';
  c.lineWidth = 2;
  c.strokeRect(1, 1, MW * T - 2, MH * T - 2);

  console.log('[map] buildMap completado');
}

// Lookup rapido
function getRoomById(id) {
  return ROOMS.find(r => r.id === id) || null;
}

function getRoomAtTile(tx, ty) {
  return ROOMS.find(r =>
    tx >= r.x && tx < r.x + r.w &&
    ty >= r.y && ty < r.y + r.h
  ) || null;
}

// Construir al cargar
buildWalkableGrid();
buildMap();
