// Sistema social: 3 modos de interaccion entre agentes
// Modo 1 — Encuentro presencial (40%): caminar, charlar, volver
// Modo 2 — Perro mensajero (30%): perro lleva sobre entre agentes
// Modo 3 — Sobre volador parabolico (30%): sobre vuela en arco

const _socials = [];
const _envelopes = [];
const _SOC_MAX = 2;
const _DOG_SPEED = 1.0;
let _nextSocTime = 0;

function initSocial() {
  _nextSocTime = 15 + Math.random() * 15;
}

function updateSocial(dt) {
  // Trigger nuevos eventos cada 15-30s
  if (animTime >= _nextSocTime && _socials.length < _SOC_MAX) {
    _spawnSocial();
    _nextSocTime = animTime + 15 + Math.random() * 15;
  }
  // Actualizar interacciones activas
  for (let i = _socials.length - 1; i >= 0; i--) {
    if (!_tickEvent(_socials[i], dt)) _socials.splice(i, 1);
  }
  // Actualizar sobres voladores
  for (let i = _envelopes.length - 1; i >= 0; i--) {
    const e = _envelopes[i];
    e.t += dt;
    if (e.t >= e.dur) {
      const c = state.characters.get(e.toId);
      if (c) c._mailTimer = 1;
      _envelopes.splice(i, 1);
    }
  }
  // Decrementar mail timers
  for (const [, ch] of state.characters) {
    if (ch._mailTimer > 0) ch._mailTimer -= dt;
  }
}

// --- Seleccion de agentes disponibles ---
function _freePair() {
  const busy = new Set();
  for (const s of _socials) { busy.add(s.aId); busy.add(s.bId); }
  const free = [...state.characters.values()].filter(c =>
    !busy.has(c.id) && c.state !== STATES.WALKING && c.state !== STATES.SPAWNING
  );
  if (free.length < 2) return null;
  const i = Math.floor(Math.random() * free.length);
  let j; do { j = Math.floor(Math.random() * free.length); } while (j === i);
  return [free[i], free[j]];
}

function _spawnSocial() {
  const pair = _freePair();
  if (!pair) return;
  const [a, b] = pair;
  const roll = Math.random();
  if (roll < 0.4) _startVisit(a, b);
  else if (roll < 0.7) _startDog(a, b);
  else _startEnvelope(a, b);
}

// --- MODO 1: Encuentro presencial ---
function _startVisit(a, b) {
  const sT = { x: Math.floor(a.x / T), y: Math.floor(a.y / T) };
  const bT = { x: Math.floor(b.x / T), y: Math.floor(b.y / T) };
  const offsets = [[-2,0],[2,0],[0,-2],[0,2],[-1,0],[1,0],[0,-1],[0,1]];
  let path = null;
  for (const [ox, oy] of offsets) {
    const tgt = { x: bT.x + ox, y: bT.y + oy };
    if (walkableGrid[tgt.y]?.[tgt.x]) {
      path = findPath(sT, tgt);
      if (path && path.length > 1) break;
      path = null;
    }
  }
  if (!path) return;
  a.state = STATES.WALKING;
  a._inSocialEvent = true;
  _socials.push({
    mode: 'visit', aId: a.id, bId: b.id,
    phase: 'walk', path, pi: 1,
    ox: a.x, oy: a.y, timer: 0,
    chatDur: 2 + Math.random() * 2,
    retPath: null, ri: 0,
  });
}

function _walkStep(ch, path, idx, dt) {
  if (idx >= path.length) return [idx, true];
  const g = path[idx], gx = g.x * T + T / 2, gy = g.y * T + T / 2;
  const dx = gx - ch.x, dy = gy - ch.y;
  const d = Math.sqrt(dx * dx + dy * dy);
  if (Math.abs(dx) > Math.abs(dy)) ch.direction = dx > 0 ? 'right' : 'left';
  else ch.direction = dy > 0 ? 'down' : 'up';
  const step = WALK_SPEED * T * dt;
  if (d <= step) { ch.x = gx; ch.y = gy; return [idx + 1, false]; }
  ch.x += (dx / d) * step; ch.y += (dy / d) * step;
  return [idx, false];
}

function _tickVisit(ev, dt) {
  const a = state.characters.get(ev.aId);
  const b = state.characters.get(ev.bId);
  if (!a || !b) { if (a) { a._inSocialEvent = false; } return false; }
  ev.timer += dt;

  switch (ev.phase) {
    case 'walk': {
      const [ni, done] = _walkStep(a, ev.path, ev.pi, dt);
      ev.pi = ni;
      if (done || ev.timer > 25) { ev.phase = 'chat'; ev.timer = 0; }
      break;
    }
    case 'chat':
      if (ev.timer > ev.chatDur + 1) { ev.phase = 'check'; ev.timer = 0; }
      break;
    case 'check':
      if (ev.timer > 1.5) {
        ev.phase = 'ret'; ev.timer = 0;
        const cur = { x: Math.floor(a.x / T), y: Math.floor(a.y / T) };
        const home = { x: Math.floor(ev.ox / T), y: Math.floor(ev.oy / T) };
        ev.retPath = findPath(cur, home) || [];
        ev.ri = Math.min(1, ev.retPath.length);
        a.state = STATES.WALKING;
      }
      break;
    case 'ret': {
      if (!ev.retPath || ev.ri >= ev.retPath.length || ev.timer > 25) {
        a.x = ev.ox; a.y = ev.oy;
        a._inSocialEvent = false;
        a.state = STATES.SITTING;
        a._enterTargetState();
        return false;
      }
      const [ni, done] = _walkStep(a, ev.retPath, ev.ri, dt);
      ev.ri = ni;
      if (done) {
        a.x = ev.ox; a.y = ev.oy;
        a._inSocialEvent = false;
        a.state = STATES.SITTING;
        a._enterTargetState();
        return false;
      }
      break;
    }
    default: return false;
  }
  return true;
}

// --- MODO 2: Perro mensajero ---
function _startDog(a, b) {
  const liv = getRoomById('living');
  if (!liv) { _startEnvelope(a, b); return; }
  const bx = (liv.x + 3) * T, by = (liv.y + 12) * T;
  _socials.push({
    mode: 'dog', aId: a.id, bId: b.id,
    phase: 'wake', timer: 0, env: false,
    dog: { x: bx, y: by, hx: bx, hy: by, f: 0, ft: 0 },
  });
}

function _tickDog(ev, dt) {
  const a = state.characters.get(ev.aId);
  const b = state.characters.get(ev.bId);
  if (!a || !b) return false;
  ev.timer += dt;
  const d = ev.dog;
  d.ft += dt;
  if (d.ft > 0.3) { d.ft = 0; d.f = (d.f + 1) % 2; }
  const move = (tx, ty) => {
    const dx = tx - d.x, dy = ty - d.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 3) return true;
    const s = _DOG_SPEED * T * dt;
    d.x += (dx / dist) * s; d.y += (dy / dist) * s;
    return false;
  };
  switch (ev.phase) {
    case 'wake': if (ev.timer > 0.5) { ev.phase = 'pickup'; ev.timer = 0; } break;
    case 'pickup': if (move(a.x, a.y)) { ev.env = true; ev.phase = 'deliver'; } break;
    case 'deliver': if (move(b.x, b.y)) { ev.env = false; b._mailTimer = 2; ev.phase = 'home'; } break;
    case 'home': if (move(d.hx, d.hy)) { ev.phase = 'sleep'; ev.timer = 0; } break;
    case 'sleep': if (ev.timer > 1) return false; break;
  }
  return true;
}

// --- MODO 3: Sobre volador parabolico ---
function _startEnvelope(a, b) {
  _envelopes.push({
    fx: a.x, fy: a.y - CHAR_H / 2,
    tx: b.x, ty: b.y - CHAR_H / 2,
    toId: b.id, t: 0, dur: 1.5,
  });
}

// --- Dispatcher ---
function _tickEvent(ev, dt) {
  if (ev.mode === 'visit') return _tickVisit(ev, dt);
  if (ev.mode === 'dog') return _tickDog(ev, dt);
  return false;
}

// --- RENDER: burbujas de chat ---
function renderSocialBubbles(ctx) {
  for (const ev of _socials) {
    if (ev.mode !== 'visit') continue;
    const a = state.characters.get(ev.aId), b = state.characters.get(ev.bId);
    if (!a || !b) continue;
    const bubble = (ch, txt) => {
      const bx = Math.floor(ch.x - 6), by = Math.floor(ch.y - CHAR_H / 2 - 18);
      ctx.fillStyle = '#FFFFFF'; ctx.globalAlpha = 0.9;
      ctx.fillRect(bx, by, 14, 10);
      ctx.fillStyle = '#000000'; ctx.globalAlpha = 0.3;
      ctx.fillRect(bx + 2, by + 10, 3, 2);
      ctx.globalAlpha = 1;
      ctx.font = '6px monospace'; ctx.textAlign = 'left';
      ctx.fillStyle = '#3355AA';
      ctx.fillText(txt, bx + 2, by + 8);
    };
    if (ev.phase === 'chat') {
      bubble(a, '💬');
      if (ev.timer > 1) bubble(b, '...');
    }
    if (ev.phase === 'check') {
      const check = (ch) => {
        ctx.font = '8px monospace'; ctx.textAlign = 'center';
        ctx.fillStyle = '#44DD44';
        ctx.fillText('✓', Math.floor(ch.x), Math.floor(ch.y - CHAR_H / 2 - 12));
      };
      check(a); check(b);
    }
  }
}

// --- RENDER: perros mensajeros ---
function renderDogMessengers(ctx) {
  for (const ev of _socials) {
    if (ev.mode !== 'dog') continue;
    const { dog } = ev;
    const dx = Math.floor(dog.x), dy = Math.floor(dog.y);
    ctx.fillStyle = '#000000'; ctx.globalAlpha = 0.15;
    ctx.beginPath(); ctx.ellipse(dx + 5, dy + 10, 5, 2, 0, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 1;
    const spr = ev.phase === 'sleep' ? 'dog_idle_0' : (dog.f === 0 ? 'dog_idle_0' : 'dog_idle_1');
    drawFurnitureSprite(ctx, spr, dx - 5, dy - 5, 1);
    if (ev.env) {
      ctx.fillStyle = '#FFFFCC'; ctx.fillRect(dx + 6, dy - 4, 5, 3);
      ctx.fillStyle = '#CC9933'; ctx.fillRect(dx + 6, dy - 4, 5, 1);
    }
  }
  // Iconos de mail recibido sobre personajes
  for (const [, ch] of state.characters) {
    if (ch._mailTimer > 0) {
      ctx.font = '7px monospace'; ctx.textAlign = 'center';
      ctx.fillStyle = '#FFD700';
      ctx.globalAlpha = Math.min(1, ch._mailTimer);
      ctx.fillText('📬', Math.floor(ch.x), Math.floor(ch.y - CHAR_H / 2 - 14));
      ctx.globalAlpha = 1;
    }
  }
}

// --- RENDER: sobres voladores parabolicos ---
function renderFlyingEnvelopes(ctx) {
  for (const e of _envelopes) {
    const p = e.t / e.dur;
    const x = e.fx + (e.tx - e.fx) * p;
    const baseY = e.fy + (e.ty - e.fy) * p;
    const y = baseY - 40 * Math.sin(p * Math.PI);
    // Sombra
    ctx.fillStyle = '#000'; ctx.globalAlpha = 0.1;
    ctx.fillRect(Math.floor(x) - 2, Math.floor(baseY) + 4, 6, 2);
    // Sobre
    ctx.globalAlpha = 0.95;
    ctx.fillStyle = '#FFFFEE'; ctx.fillRect(Math.floor(x) - 3, Math.floor(y) - 2, 7, 5);
    ctx.fillStyle = '#CC9933'; ctx.fillRect(Math.floor(x) - 3, Math.floor(y) - 2, 7, 1);
    // Solapa V
    ctx.fillStyle = '#DDAA44';
    ctx.fillRect(Math.floor(x) - 1, Math.floor(y) - 1, 1, 1);
    ctx.fillRect(Math.floor(x) + 1, Math.floor(y) - 1, 1, 1);
    ctx.fillRect(Math.floor(x), Math.floor(y), 1, 1);
    ctx.globalAlpha = 1;
  }
}
