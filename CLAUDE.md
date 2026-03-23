# PulsarMoon Office — CLAUDE.md

## PRINCIPIO CORE
Mínimo gasto de tokens, máxima potencia. Siempre.
- Leer solo los docs que necesitás para la tarea actual
- /compact cuando el contexto crece mucho
- Subagentes para tareas aisladas que generan output verbose

## ANTES DE CODIFICAR
Investigar siempre:
- Pixel Agents: https://github.com/pablodelucca/pixel-agents
- Su CLAUDE.md: https://github.com/pablodelucca/pixel-agents/blob/main/CLAUDE.md
- DeepWiki: https://deepwiki.com/pablodelucca/pixel-agents

## QUÉ ES ESTO
Oficina de agentes IA de PulsarMoon. Mapa top-down pixel art profesional,
tiempo real vía WebSocket, accesible desde cualquier lugar.
FASE 1: infraestructura base + interfaz visual con agentes demo.

## ARQUITECTURA
```
Frontend (Vercel) ←WebSocket→ Backend (Laptop Linux + Cloudflare Tunnel)
web/          → HTML+CSS+JS estático, desplegado en Vercel
server/       → Python, corre en laptop siempre encendida
agents/events/→ agentes escriben JSON aquí
office.db     → SQLite estado tiempo real (NO Supabase para esto)
```
WS_URL y API_URL vienen de CONFIG en web/js/config.js — nunca hardcodeadas.

## STACK
- Python 3.11+: websockets, watchdog, flask, flask-cors
- JS vanilla ES2022 + HTML5 Canvas — sin frameworks, sin npm en frontend
- SQLite built-in — estado tiempo real
- Supabase free — solo logs históricos (opcional)

## ESTRUCTURA
```
pulsarmoon-office/
├── CLAUDE.md
├── vercel.json
├── run.py
├── config.json
├── requirements.txt
├── server/
│   ├── main.py, db.py, ws_server.py
│   ├── api.py, watcher.py
│   ├── demo_agents.py, supabase_sync.py
├── agents/events/
├── web/
│   ├── index.html
│   ├── config.js
│   ├── css/main.css
│   └── js/
│       ├── main.js, state.js, config.js
│       ├── camera.js, map.js, renderer.js
│       ├── sprites.js, characters.js
│       ├── pathfinding.js, ui.js
└── logs/
```

## DOCS DE REFERENCIA
Leer solo el doc relevante a la tarea actual:
- Visual/Canvas/Sprites/Rendering → .claude/docs/rendering.md
- Backend/WebSocket/DB/Eventos   → .claude/docs/backend.md
- Mapa/Salas/Layout/Coordenadas  → .claude/docs/layout.md
- UI/HUD/Cámara/Controles        → .claude/docs/ui.md

## PROTOCOLO DE EVENTOS
Agentes escriben `agents/events/{agent_id}.json`:
```json
{"agent_id":"dev-01","agent_name":"Arquitecto","department":"desarrollo",
 "status":"working","task":"Codificando API","model":"sonnet","timestamp":123}
```
Estados: idle | working | waiting | error | done

## REGLAS DE CÓDIGO
- Comentarios español, código inglés
- Type hints en todo Python
- Nunca except sin log
- Máx 200 líneas por archivo
- Zoom siempre entero (1,2,3,4) — nunca fracción
- imageSmoothingEnabled = false siempre
- image-rendering: pixelated en CSS siempre
- Math.floor() en todas las coordenadas de dibujo

## ORDEN DE CONSTRUCCIÓN
✅ PASO 1: Backend Python — COMPLETADO
   server/ completo, python run.py funciona

⬜ PASO 2: Frontend fundamentos
   index.html + config.js + state.js + main.js (canvas + WS)
   → Ver .claude/docs/rendering.md y .claude/docs/backend.md

⬜ PASO 3: Mapa y cámara
   camera.js + map.js + renderer.js
   → Ver .claude/docs/rendering.md y .claude/docs/layout.md

⬜ PASO 4: Sprites y personajes
   sprites.js + pathfinding.js + characters.js
   → Ver .claude/docs/rendering.md

⬜ PASO 5: UI completa
   ui.js (HUD, panel, minimap, labels)
   → Ver .claude/docs/ui.md

⬜ PASO 6: Vercel deployment
   vercel.json ya existe, configurar env vars

## DEFINICIÓN DE ÉXITO FASE 1
✓ python run.py sin errores
✓ Canvas fullscreen pixel-perfect en todos los zooms
✓ 8 departamentos con personajes animados
✓ Pan drag + zoom scroll (1x-4x) suave
✓ Click agente → panel detalle
✓ WebSocket tiempo real funcionando
✓ Accesible desde celular vía Vercel + Cloudflare