\# UI — HUD, Cámara, Controles



\## Cámara

```javascript

const camera = {x:0, y:0, zoom:2, minZoom:1, maxZoom:4};



function worldToScreen(wx, wy) {

&#x20; return { x: Math.floor(wx\*camera.zoom - camera.x),

&#x20;          y: Math.floor(wy\*camera.zoom - camera.y) };

}

function screenToWorld(sx, sy) {

&#x20; return { x:(sx+camera.x)/camera.zoom, y:(sy+camera.y)/camera.zoom };

}



// Pan con drag

canvas.addEventListener('mousedown', e => {

&#x20; isDragging=true; dragStart={x:e.clientX+camera.x, y:e.clientY+camera.y};

});

canvas.addEventListener('mousemove', e => {

&#x20; if(!isDragging) return;

&#x20; camera.x=dragStart.x-e.clientX; camera.y=dragStart.y-e.clientY; clampCamera();

});



// Zoom hacia cursor — SIEMPRE entero

canvas.addEventListener('wheel', e => {

&#x20; e.preventDefault();

&#x20; const delta = e.deltaY<0 ? 1 : -1;

&#x20; const nz = Math.max(1, Math.min(4, camera.zoom+delta));

&#x20; if(nz===camera.zoom) return;

&#x20; const wx=(e.clientX+camera.x)/camera.zoom;

&#x20; const wy=(e.clientY+camera.y)/camera.zoom;

&#x20; camera.zoom=nz; camera.x=wx\*nz-e.clientX; camera.y=wy\*nz-e.clientY;

&#x20; clampCamera();

}, {passive:false});



// Clamp

function clampCamera() {

&#x20; const mw=MAP\_W\*TILE\_SIZE\*camera.zoom, mh=MAP\_H\*TILE\_SIZE\*camera.zoom;

&#x20; camera.x=Math.max(0,Math.min(mw-innerWidth, camera.x));

&#x20; camera.y=Math.max(0,Math.min(mh-innerHeight,camera.y));

}



// Teclas

document.addEventListener('keydown', e=>{

&#x20; if(e.key==='Escape') resetCamera();  // zoom 1, centrado

&#x20; if(e.key===' ') centerCamera();      // centrar

});

```



\## Labels de salas según zoom

```javascript

// zoom 1: solo nombre

// zoom 2: nombre + "N activos"

// zoom 3+: no mostrar (personajes visibles)

```



\## Panel de detalle (click en agente)

```

Posición: derecha, 280px ancho, slide-in 200ms

┌────────────────────────────────┐

│  ● Nombre agente          \[×]  │

│  Departamento: X               │

│  Estado: ⚡ Trabajando         │

│  Modelo: claude-sonnet         │

│  Tarea: "..."                  │

│  Última actualización: Ns      │

└────────────────────────────────┘

```



\## Barra de estado (top, 32px)

```

◈ PulsarMoon Office | N agentes | N activos | ● ws | hora

Fondo: --hud-bg. Texto: --hud-text

```



\## Minimap (esquina inferior derecha, 200×150px)

\- Salas como rectángulos de color

\- Agentes como puntos 2×2px del color de su dept

\- Rectángulo blanco: área visible actual

\- Click: navegar a esa zona



\## CSS variables

```css

:root {

&#x20; --hud-bg: rgba(8,8,20,0.88);

&#x20; --hud-border: rgba(255,255,255,0.08);

&#x20; --hud-text: #d0d0e8;

&#x20; --hud-text-muted: #6a6a8a;

&#x20; --status-working: #4ade80;

&#x20; --status-idle: #64748b;

&#x20; --status-waiting: #fbbf24;

&#x20; --status-error: #f87171;

&#x20; --status-done: #60a5fa;

&#x20; --transition: 150ms ease;

}

```



\## config.js (frontend)

```javascript

const CONFIG = {

&#x20; WS\_URL:  window.OFFICE\_WS\_URL  || 'ws://localhost:8765',

&#x20; API\_URL: window.OFFICE\_API\_URL || 'http://localhost:8766',

&#x20; TILE\_SIZE: 16,

&#x20; MAP\_W: 80, MAP\_H: 60,

&#x20; MIN\_ZOOM: 1, MAX\_ZOOM: 4,

};

```



\## vercel.json

```json

{"outputDirectory":"web","framework":null,

&#x20;"rewrites":\[{"source":"/(.\*)","destination":"/index.html"}]}

```

```



\---



Ya tenés los 5 archivos. El resultado:



| Archivo | Chars | Cuándo se carga |

|---|---|---|

| CLAUDE.md | \~4k | Siempre |

| rendering.md | \~4k | Pasos 2,3,4 |

| backend.md | \~3k | Paso 2 |

| layout.md | \~2k | Paso 3 |

| ui.md | \~2k | Paso 5 |



De 51k siempre → 4k base + solo lo necesario. \*\*\~90% menos contexto base.\*\*



Cuando todo esté creado, volvé a abrir Claude Code y arrancamos el Paso 2 con este prompt:

```

Leé CLAUDE.md y .claude/docs/rendering.md y .claude/docs/backend.md.

Arrancá el PASO 2: Frontend fundamentos.

Crear: web/index.html, web/config.js, web/css/main.css, web/js/state.js, web/js/main.js

Canvas fullscreen conectado al WebSocket. Game loop básico corriendo.

No avanzar al Paso 3 hasta verificar que el WS recibe mensajes.

