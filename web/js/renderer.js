// Pipeline de renderizado — orden obligatorio segun rendering.md

let lastFrameTime = 0;

function render(timestamp) {
  if (!lastFrameTime) lastFrameTime = timestamp || performance.now();
  const now = timestamp || performance.now();
  const dt = Math.min((now - lastFrameTime) / 1000, 0.1);
  lastFrameTime = now;

  // Update systems
  updateCharacters(dt);
  updateAnimations(dt);

  const { x: camX, y: camY, zoom } = state.camera;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // --- Mundo (transformado por camara y zoom) ---
  ctx.save();
  ctx.scale(zoom, zoom);
  ctx.translate(Math.floor(-camX / zoom), Math.floor(-camY / zoom));

  // 1. Fondo estatico
  ctx.drawImage(bgCanvas, 0, 0);

  // 2. Animated objects (TV flicker, cooler bubbles, corridor lamps, etc)
  renderAnimatedObjects(ctx);

  // 3. Personajes Z-sorted por Y, con sombras y efectos
  const chars = [...state.characters.values()];
  chars.sort((a, b) => (a.y + CHAR_H / 2) - (b.y + CHAR_H / 2));
  for (const char of chars) {
    renderCharShadow(ctx, char);
    renderCharacter(ctx, char);
    renderStatusIndicator(ctx, char);
  }

  // 4. Social bubbles y dog messengers (encima de todo en el mundo)
  renderSocialBubbles(ctx);
  renderDogMessengers(ctx);
  renderFlyingEnvelopes(ctx);

  ctx.restore();

  // 5. HUD sin transformacion
  renderHUD();
}
