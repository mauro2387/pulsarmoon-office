// Personajes: FSM, sincronizacion con backend, movimiento, renderizado

// --- Constantes ---
const WALK_SPEED     = 1.5;  // tiles por segundo
const FRAME_DURATION = 200;  // ms entre frames de animacion
const SIT_OFFSET_Y   = -8;   // offset Y cuando sentado (px mundo 1x)
const CHAR_W = 16;           // ancho sprite personaje en px
const CHAR_H = 32;           // alto sprite personaje en px

// --- Estados FSM ---
const STATES = {
  SPAWNING: 'spawning',
  WALKING:  'walking',
  SITTING:  'sitting',
  TYPING:   'typing',
  IDLE:     'idle',
  WAITING:  'waiting',
  ERROR:    'error',
};

// Mapeo de status del backend a estado visual
const STATUS_TO_STATE = {
  working: STATES.TYPING,
  idle:    STATES.IDLE,
  waiting: STATES.WAITING,
  error:   STATES.ERROR,
  done:    STATES.IDLE,
};

// --- Posiciones de escritorios por sala ---
// Cada desk tiene {tx, ty} en coordenadas tile (posicion del escritorio)
// y {cx, cy} donde se sienta el personaje (tile frente al escritorio)
function generateDesks(room) {
  const desks = [];
  if (room.desks === 0) return desks;

  // Interior de la sala: (room.x+1) a (room.x+room.w-2)
  const innerX = room.x + 2;
  const innerY = room.y + 2;
  const innerW = room.w - 4;
  const innerH = room.h - 4;

  // Distribuir escritorios en 2 columnas
  const cols = 2;
  const spacing = Math.floor(innerW / cols);

  for (let i = 0; i < room.desks; i++) {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const tx = innerX + col * spacing + 1;
    const ty = innerY + row * 3;

    // Personaje se sienta 1 tile debajo del escritorio
    desks.push({
      tx, ty,
      cx: tx, cy: ty + 1,
    });
  }
  return desks;
}

// Pre-calcular desks de cada sala
const ROOM_DESKS = {};
for (const room of ROOMS) {
  ROOM_DESKS[room.id] = generateDesks(room);
}

// --- Tracking de desks ocupados ---
const occupiedDesks = new Map();  // key: "roomId-deskIndex" -> agentId

// Asignar un desk libre a un agente en su departamento
function assignDesk(agentId, deptId) {
  // Si ya tiene desk asignado, reutilizar
  for (const [key, id] of occupiedDesks) {
    if (id === agentId) {
      const [rid, idx] = key.split('-');
      return ROOM_DESKS[rid]?.[parseInt(idx)] || null;
    }
  }

  const desks = ROOM_DESKS[deptId];
  if (!desks || desks.length === 0) return null;

  for (let i = 0; i < desks.length; i++) {
    const key = `${deptId}-${i}`;
    if (!occupiedDesks.has(key)) {
      occupiedDesks.set(key, agentId);
      return desks[i];
    }
  }
  // Si todos los desks estan ocupados, usar uno aleatorio (overflow)
  const idx = Math.floor(Math.random() * desks.length);
  return desks[idx];
}

// Liberar desk de un agente
function releaseDesk(agentId) {
  for (const [key, id] of occupiedDesks) {
    if (id === agentId) {
      occupiedDesks.delete(key);
      return;
    }
  }
}

// --- Clase Character ---
class Character {
  constructor(agentId, agentData) {
    this.id       = agentId;
    this.name     = agentData.agent_name || agentId;
    this.dept     = agentData.department || 'administrativo';
    this.status   = agentData.status || 'idle';
    this.task     = agentData.task || '';
    this.model    = agentData.model || '';

    // Estado FSM
    this.state = STATES.SPAWNING;

    // Posicion en pixels mundo (1x) — centro del tile
    const desk = assignDesk(agentId, this.dept);
    const room = getRoomById(this.dept);

    // Spawn en la puerta de la sala, luego caminar al desk
    if (room && desk) {
      // Puerta: centro inferior de la sala
      this.x = (room.x + Math.floor(room.w / 2)) * T + T / 2;
      this.y = (room.y + room.h - 1) * T;
      this.targetX = desk.cx * T + T / 2;
      this.targetY = desk.cy * T + T / 2;
      this.desk = desk;
    } else {
      this.x = 40 * T;
      this.y = 30 * T;
      this.targetX = this.x;
      this.targetY = this.y;
      this.desk = null;
    }

    // Pathfinding
    this.path      = null;
    this.pathIndex = 0;

    // Social system lock
    this._inSocialEvent = false;
    this._mailTimer = 0;

    // Animacion
    this.frame     = 0;
    this.frameTime = 0;
    this.direction = 'down';  // down, up, left, right

    // Transicion al estado correcto despues del spawn
    this.targetState = STATUS_TO_STATE[this.status] || STATES.IDLE;

    // Iniciar caminando al desk
    this._startWalkToDesk();
  }

  _startWalkToDesk() {
    if (!this.desk) {
      this.state = this.targetState;
      return;
    }

    const startTile = {
      x: Math.floor(this.x / T),
      y: Math.floor(this.y / T),
    };
    const endTile = { x: this.desk.cx, y: this.desk.cy };

    this.path = findPath(startTile, endTile);
    if (this.path && this.path.length > 1) {
      this.pathIndex = 1;
      this.state = STATES.WALKING;
    } else {
      // Sin ruta, teleportar
      this.x = this.targetX;
      this.y = this.targetY;
      this.state = STATES.SITTING;
      this._enterTargetState();
    }
  }

  _enterTargetState() {
    const ts = this.targetState;
    if (ts === STATES.TYPING || ts === STATES.IDLE ||
        ts === STATES.WAITING || ts === STATES.ERROR) {
      this.state = ts;
    } else {
      this.state = STATES.IDLE;
    }
  }

  update(dt) {
    // Avanzar timer de animacion
    this.frameTime += dt * 1000;
    if (this.frameTime >= FRAME_DURATION) {
      this.frameTime -= FRAME_DURATION;
      this.frame = (this.frame + 1) % 2;
    }

    switch (this.state) {
      case STATES.SPAWNING:
        this._startWalkToDesk();
        break;

      case STATES.WALKING:
        if (!this._inSocialEvent) this._updateWalking(dt);
        break;

      // Sentado, tecleando, idle, waiting, error — no se mueve
      default:
        break;
    }
  }

  _updateWalking(dt) {
    if (!this.path || this.pathIndex >= this.path.length) {
      // Llego al destino
      this.state = STATES.SITTING;
      this._enterTargetState();
      return;
    }

    const target = this.path[this.pathIndex];
    const goalX = target.x * T + T / 2;
    const goalY = target.y * T + T / 2;

    const dx = goalX - this.x;
    const dy = goalY - this.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    // Determinar direccion para el sprite
    if (Math.abs(dx) > Math.abs(dy)) {
      this.direction = dx > 0 ? 'right' : 'left';
    } else {
      this.direction = dy > 0 ? 'down' : 'up';
    }

    const step = WALK_SPEED * T * dt;
    if (dist <= step) {
      this.x = goalX;
      this.y = goalY;
      this.pathIndex++;
    } else {
      this.x += (dx / dist) * step;
      this.y += (dy / dist) * step;
    }
  }

  // Actualizar desde datos del backend
  syncFromAgent(agentData) {
    const prevStatus = this.status;
    this.name   = agentData.agent_name || this.name;
    this.status = agentData.status || this.status;
    this.task   = agentData.task || this.task;
    this.model  = agentData.model || this.model;

    const newDept = agentData.department || this.dept;
    if (newDept !== this.dept) {
      releaseDesk(this.id);
      this.dept = newDept;
      this.desk = assignDesk(this.id, this.dept);
      if (this.desk) {
        this.targetX = this.desk.cx * T + T / 2;
        this.targetY = this.desk.cy * T + T / 2;
        this._startWalkToDesk();
      }
    }

    this.targetState = STATUS_TO_STATE[this.status] || STATES.IDLE;
    if (this.state !== STATES.WALKING && this.state !== STATES.SPAWNING) {
      this._enterTargetState();
    }
  }
}

// --- Sincronizar con datos del backend ---
function syncCharacters(agentsMap) {
  // Actualizar o crear personajes
  for (const [agentId, agentData] of agentsMap) {
    if (state.characters.has(agentId)) {
      state.characters.get(agentId).syncFromAgent(agentData);
    } else {
      state.characters.set(agentId, new Character(agentId, agentData));
    }
  }

  // Eliminar personajes que ya no existen en el backend
  for (const [charId] of state.characters) {
    if (!agentsMap.has(charId)) {
      releaseDesk(charId);
      state.characters.delete(charId);
    }
  }
}

// --- Update loop ---
function updateCharacters(dt) {
  for (const [, char] of state.characters) {
    char.update(dt);
  }
}

// --- Renderizado ---

// Obtiene el nombre del sprite segun estado y frame actual
function _getSpriteName(char) {
  switch (char.state) {
    case STATES.TYPING:
      return `char_type_${char.frame}`;
    case STATES.SITTING:
      return 'char_sit';
    case STATES.WALKING:
    case STATES.SPAWNING:
      if (char.direction === 'up')   return `char_up_${char.frame}`;
      if (char.direction === 'left') return `char_left_${char.frame}`;
      // right usa left espejado (se maneja en el render)
      if (char.direction === 'right') return `char_left_${char.frame}`;
      return `char_down_${char.frame}`;
    case STATES.IDLE:
    case STATES.WAITING:
    case STATES.ERROR:
    default:
      return `char_idle_${char.frame}`;
  }
}

function renderCharacter(ctx, char) {
  const spriteName = _getSpriteName(char);
  const zoom = 1;  // Se dibuja a 1x en el bgCanvas/world space, ctx.scale aplica zoom

  // Posicion de dibujo (centro del sprite en la posicion del personaje)
  let drawX = Math.floor(char.x - (CHAR_W * zoom) / 2);
  let drawY = Math.floor(char.y - (CHAR_H * zoom) / 2);

  // Offset de sentado
  if (char.state === STATES.SITTING || char.state === STATES.TYPING) {
    drawY += SIT_OFFSET_Y;
  }

  // Espejar para direccion derecha
  if (char.direction === 'right' && char.state === STATES.WALKING) {
    ctx.save();
    ctx.translate(Math.floor(char.x), 0);
    ctx.scale(-1, 1);
    drawCharSprite(ctx, spriteName,
      Math.floor(-(CHAR_W * zoom) / 2),
      drawY, zoom, char.dept);
    ctx.restore();
  } else {
    drawCharSprite(ctx, spriteName, drawX, drawY, zoom, char.dept);
  }

  // Indicador de estado ahora renderizado por renderStatusIndicator() en animations.js

  // Nombre debajo del personaje (texto pequeño)
  ctx.font = 'bold 5px monospace';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillStyle = '#000000';
  ctx.globalAlpha = 0.5;
  ctx.fillText(char.name, Math.floor(char.x) + 1, drawY + CHAR_H + 2 + 1);
  ctx.fillStyle = PALETTES[char.dept]?.light || '#CCCCCC';
  ctx.globalAlpha = 0.9;
  ctx.fillText(char.name, Math.floor(char.x), drawY + CHAR_H + 2);
  ctx.globalAlpha = 1;
}

// --- Renderizado de furniture estatico en el bgCanvas ---
function renderFurnitureToBackground() {
  const c = bgCtx;
  const zoom = 1;

  for (const room of ROOMS) {
    const desks = ROOM_DESKS[room.id];

    // --- Escritorios y sillas (salas con desks) ---
    if (desks && desks.length > 0) {
      for (const desk of desks) {
        drawFurnitureSprite(c, 'desk', desk.tx * T, desk.ty * T, zoom);
        drawFurnitureSprite(c, 'chair_down', desk.cx * T, desk.cy * T, zoom);
      }

      // Lampara en el primer desk de cada sala
      if (desks[0]) {
        drawFurnitureSprite(c, 'lamp', (desks[0].tx + 1) * T, (desks[0].ty) * T, zoom);
      }
    }

    // --- Plantas en esquinas superiores (todas las salas) ---
    if (room.id !== 'servidores') {
      drawFurnitureSprite(c, 'plant', (room.x + 1) * T, (room.y + 1) * T, zoom);
      drawFurnitureSprite(c, 'plant', (room.x + room.w - 2) * T, (room.y + 1) * T, zoom);
    }

    // --- Bookshelves en pared trasera (salas de trabajo, no living/servidores) ---
    if (room.desks > 0 && room.id !== 'living' && room.id !== 'servidores') {
      // Estanteria centrada en pared superior
      const bx = room.x + Math.floor(room.w / 2) - 1;
      drawFurnitureSprite(c, 'bookshelf', bx * T, (room.y + 1) * T, zoom);
    }

    // --- Whiteboard en Desarrollo y QA ---
    if (room.id === 'desarrollo' || room.id === 'qa') {
      drawFurnitureSprite(c, 'whiteboard', (room.x + room.w - 3) * T, (room.y + 1) * T, zoom);
    }

    // --- Printer en Admin ---
    if (room.id === 'administrativo') {
      drawFurnitureSprite(c, 'printer', (room.x + room.w - 3) * T, (room.y + room.h - 3) * T, zoom);
    }

    // --- Server racks (sala servidores, ajustado a h:18) ---
    if (room.id === 'servidores') {
      for (let row = 0; row < 2; row++) {
        const rx = room.x + 3;
        const ry = room.y + 2 + row * 7;
        if (ry + 1 < room.y + room.h - 1) {
          drawFurnitureSprite(c, 'server_rack', rx * T, ry * T, zoom);
          drawFurnitureSprite(c, 'server_rack', (rx + 5) * T, ry * T, zoom);
          drawFurnitureSprite(c, 'server_rack', (rx + 10) * T, ry * T, zoom);
        }
      }
      // Plantas en servidores
      drawFurnitureSprite(c, 'plant', (room.x + 1) * T, (room.y + 1) * T, zoom);
      drawFurnitureSprite(c, 'plant', (room.x + room.w - 2) * T, (room.y + 1) * T, zoom);
    }

    // --- LIVING ROOM: sofas, mesa de cafe, TV, ping pong, perros ---
    if (room.id === 'living') {
      const lx = room.x + 1;  // interior left
      const ly = room.y + 1;  // interior top

      // Sofas: 2 horizontales, formando L
      drawFurnitureSprite(c, 'sofa_h', (lx + 2) * T, (ly + 1) * T, zoom);
      drawFurnitureSprite(c, 'sofa_h', (lx + 2) * T, (ly + 3) * T, zoom);

      // Mesa ratona en el centro del area de sofas
      drawFurnitureSprite(c, 'coffee_table', (lx + 4) * T, (ly + 2) * T, zoom);

      // TV contra la pared izquierda
      drawFurnitureSprite(c, 'tv', (lx) * T, (ly + 2) * T, zoom);

      // Sofa vertical al lado derecho
      drawFurnitureSprite(c, 'sofa_v', (lx + 7) * T, (ly + 1) * T, zoom);

      // Mesa de ping pong (2 mitades, centro-derecha)
      drawFurnitureSprite(c, 'ping_pong', (lx + 11) * T, (ly + 2) * T, zoom);
      drawFurnitureSprite(c, 'ping_pong', (lx + 11) * T, (ly + 3) * T, zoom);

      // Water cooler
      drawFurnitureSprite(c, 'water_cooler', (lx + 15) * T, (ly + 1) * T, zoom);

      // Camas de perro con perros durmiendo (area inferior)
      drawFurnitureSprite(c, 'dog_bed', (lx + 2) * T, (ly + 10) * T, zoom);
      drawFurnitureSprite(c, 'dog_idle_0', (lx + 2) * T, (ly + 10) * T, zoom);

      drawFurnitureSprite(c, 'dog_bed', (lx + 5) * T, (ly + 12) * T, zoom);
      drawFurnitureSprite(c, 'dog_idle_1', (lx + 5) * T, (ly + 12) * T, zoom);

      drawFurnitureSprite(c, 'dog_bed', (lx + 8) * T, (ly + 10) * T, zoom);
      drawFurnitureSprite(c, 'dog_idle_0', (lx + 8) * T, (ly + 10) * T, zoom);

      // Plantas grandes en esquinas del living
      drawFurnitureSprite(c, 'plant', (lx + 18) * T, (ly) * T, zoom);
      drawFurnitureSprite(c, 'plant', (lx) * T, (ly + 16) * T, zoom);
      drawFurnitureSprite(c, 'plant', (lx + 18) * T, (ly + 16) * T, zoom);

      // Bookshelf en pared derecha
      drawFurnitureSprite(c, 'bookshelf', (lx + 15) * T, (ly + 8) * T, zoom);

      // Printer en esquina
      drawFurnitureSprite(c, 'printer', (lx + 17) * T, (ly + 8) * T, zoom);
    }
  }

  console.log('[characters] Furniture renderizado en bgCanvas');
}
