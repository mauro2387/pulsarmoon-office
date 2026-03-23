// Fase 4B — Animations, shadows, social behavior, dog messenger

// --- Global animation timer ---
let animTime = 0;

function updateAnimations(dt) {
  animTime += dt;
  if (typeof updateSocial === 'function') updateSocial(dt);
}

// --- Shadows ---
function renderShadow(ctx, x, y, w, h) {
  ctx.save();
  ctx.fillStyle = '#000000';
  ctx.globalAlpha = 0.15;
  ctx.beginPath();
  ctx.ellipse(Math.floor(x), Math.floor(y + h * 0.4), w * 0.5, h * 0.15, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function renderCharShadow(ctx, char) {
  ctx.save();
  ctx.fillStyle = '#000000';
  ctx.globalAlpha = 0.2;
  ctx.beginPath();
  ctx.ellipse(Math.floor(char.x), Math.floor(char.y + CHAR_H * 0.35), 6, 2, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

// --- Status indicators (animated) ---
function renderStatusIndicator(ctx, char) {
  const cx = Math.floor(char.x);
  const baseY = Math.floor(char.y - CHAR_H / 2 - 12);

  switch (char.status) {
    case 'working': {
      // Yellow sparks bouncing above head
      const sparkPhase = animTime * 4;
      const s1y = baseY - Math.abs(Math.sin(sparkPhase)) * 4;
      const s2y = baseY - Math.abs(Math.sin(sparkPhase + 1.5)) * 5;
      ctx.fillStyle = '#FFD700';
      ctx.globalAlpha = 0.6 + Math.sin(sparkPhase * 2) * 0.3;
      ctx.fillRect(cx - 2, Math.floor(s1y), 2, 2);
      ctx.fillStyle = '#FFEE88';
      ctx.fillRect(cx + 2, Math.floor(s2y), 1, 1);
      ctx.globalAlpha = 1;
      break;
    }
    case 'waiting': {
      // "..." sequential dots
      ctx.font = 'bold 6px monospace';
      ctx.textAlign = 'center';
      ctx.fillStyle = '#FFAA00';
      const dotCount = Math.floor(animTime * 2) % 4;
      const dots = '.'.repeat(Math.max(1, dotCount));
      ctx.globalAlpha = 0.8;
      ctx.fillText(dots, cx, baseY);
      ctx.globalAlpha = 1;
      break;
    }
    case 'error': {
      // "!" red blinking
      const blink = Math.sin(animTime * 6) > 0;
      if (blink) {
        ctx.font = 'bold 7px monospace';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#FF4444';
        ctx.globalAlpha = 0.9;
        ctx.fillText('!', cx, baseY);
        ctx.globalAlpha = 1;
      }
      break;
    }
    // idle: nothing
  }
}

// --- Animated objects (rendered per-frame over bgCanvas) ---
const ANIM_OBJECTS = [];

function registerAnimatedObject(type, tx, ty, extra) {
  ANIM_OBJECTS.push({ type, tx, ty, extra: extra || {} });
}

function renderAnimatedObjects(ctx) {
  for (const obj of ANIM_OBJECTS) {
    const px = obj.tx * T;
    const py = obj.ty * T;

    switch (obj.type) {
      case 'tv': {
        // Flickering colored pixels on screen area
        const phase = Math.floor(animTime * 2) % 4;
        const colors = ['#334466','#443355','#335544','#554433'];
        ctx.fillStyle = colors[phase];
        ctx.globalAlpha = 0.6;
        ctx.fillRect(px + 3, py + 3, 10, 7);
        // Random pixel noise
        for (let i = 0; i < 6; i++) {
          const nx = px + 4 + ((phase * 3 + i * 7) % 8);
          const ny = py + 4 + ((phase * 5 + i * 3) % 5);
          ctx.fillStyle = ['#6688AA','#AA6688','#88AA66','#AABB44'][i % 4];
          ctx.globalAlpha = 0.4;
          ctx.fillRect(nx, ny, 1, 1);
        }
        ctx.globalAlpha = 1;
        break;
      }
      case 'water_cooler': {
        // Bubble rising every 3 seconds
        const bubbleCycle = animTime % 3;
        if (bubbleCycle < 0.6) {
          const by = py + 2 - bubbleCycle * 5;
          ctx.fillStyle = '#AADDFF';
          ctx.globalAlpha = 0.5 * (1 - bubbleCycle / 0.6);
          ctx.fillRect(Math.floor(px + 7), Math.floor(by), 2, 2);
          ctx.globalAlpha = 1;
        }
        break;
      }
      case 'printer': {
        // Green LED blink
        const ledOn = Math.sin(animTime * 3) > 0;
        ctx.fillStyle = ledOn ? '#44FF44' : '#114411';
        ctx.fillRect(px + 4, py + 3, 2, 1);
        break;
      }
      case 'corridor_lamp': {
        // Soft halo pulse
        const pulse = 0.15 + Math.sin(animTime * 1.5 + obj.tx * 0.5) * 0.08;
        ctx.fillStyle = '#FFEE88';
        ctx.globalAlpha = pulse;
        ctx.fillRect(px + 3, py + 4, 10, 8);
        ctx.globalAlpha = pulse * 0.5;
        ctx.fillRect(px + 1, py + 3, 14, 10);
        ctx.globalAlpha = 1;
        break;
      }
      case 'dog': {
        // Perro grande y visible — 2x zoom
        const breathOffset = Math.sin(animTime * Math.PI * 2) > 0.5 ? -1 : 0;
        const dogFrame = breathOffset < 0 ? 'dog_idle_1' : 'dog_idle_0';
        drawFurnitureSprite(ctx, dogFrame, px - 4, py - 8 + breathOffset, 2);
        // Cola agitandose cada 4-6s
        const wagCycle = animTime % (4 + (obj.tx % 3));
        if (wagCycle < 0.3) {
          ctx.fillStyle = '#C49A6C';
          const tailX = px + 22 + (wagCycle < 0.15 ? 2 : -2);
          ctx.fillRect(Math.floor(tailX), py + 8 + breathOffset, 3, 2);
        }
        break;
      }
      case 'bookshelf': {
        // Amber glow when relevant agent nearby (check task keywords)
        let glowing = false;
        const keywords = ['dato', 'analiz', 'investig', 'busca', 'research', 'data'];
        for (const [, char] of state.characters) {
          if (char.status === 'working' && char.task) {
            const taskLow = char.task.toLowerCase();
            if (keywords.some(k => taskLow.includes(k))) {
              const dist = Math.abs(char.x - px) + Math.abs(char.y - py);
              if (dist < 200) { glowing = true; break; }
            }
          }
        }
        if (glowing) {
          const pulse = 0.1 + Math.sin(animTime * 2) * 0.06;
          ctx.fillStyle = '#FFAA33';
          ctx.globalAlpha = pulse;
          ctx.fillRect(px, py, T, T);
          ctx.globalAlpha = 1;
        }
        break;
      }
    }
  }
}

// --- Register animated objects from furniture placement ---
function registerLivingAnimations() {
  const living = getRoomById('living');
  if (!living) return;
  const lx = living.x + 1, ly = living.y + 1;

  registerAnimatedObject('tv', lx, ly + 2);
  registerAnimatedObject('water_cooler', lx + 15, ly + 1);
  registerAnimatedObject('dog', lx + 2, ly + 10);
  registerAnimatedObject('dog', lx + 5, ly + 12);
  registerAnimatedObject('dog', lx + 8, ly + 10);

  // Corridor lamps from map
  for (const vc of V_CORRIDORS) {
    for (let ty = vc.yStart + 2; ty < vc.yEnd; ty += 8) {
      registerAnimatedObject('corridor_lamp', vc.x, ty);
      registerAnimatedObject('corridor_lamp', vc.x + vc.w - 1, ty);
    }
  }

  // Bookshelves in rooms
  for (const room of ROOMS) {
    if (room.desks > 0 && room.id !== 'living' && room.id !== 'servidores') {
      const bx = room.x + Math.floor(room.w / 2) - 1;
      registerAnimatedObject('bookshelf', bx, room.y + 1);
    }
  }

  console.log('[anim] Registered', ANIM_OBJECTS.length, 'animated objects');
}
