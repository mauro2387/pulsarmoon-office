\# Rendering — Canvas 2D Pixel Art



\## Referencias obligatorias antes de codificar

\- Pixel Agents renderer.ts: https://github.com/pablodelucca/pixel-agents

\- Crisp pixel art MDN: https://developer.mozilla.org/en-US/docs/Games/Techniques/Crisp\_pixel\_art\_look

\- AgentOffice: https://dev.to/harishkotra/how-i-built-agentoffice-self-growing-ai-teams-in-a-pixel-art-virtual-office-4o0p



\## Reglas pixel-perfect — CRÍTICAS

```css

canvas#office {

&#x20; image-rendering: pixelated;

&#x20; image-rendering: crisp-edges;

&#x20; display: block; width: 100vw; height: 100vh;

}

```

```javascript

ctx.imageSmoothingEnabled = false;

// Zoom SIEMPRE entero: 1, 2, 3, 4 — NUNCA fracción

const drawX = Math.floor(worldX \* zoom - camera.x);

const drawY = Math.floor(worldY \* zoom - camera.y);

```



\## Pipeline de renderizado (orden obligatorio)

```javascript

function render() {

&#x20; ctx.clearRect(0, 0, canvas.width, canvas.height);

&#x20; ctx.save();

&#x20; ctx.translate(-camera.x, -camera.y);

&#x20; // 1. Fondo estático desde offscreen canvas (O(1))

&#x20; ctx.drawImage(bgCanvas, 0, 0);

&#x20; // 2. Furniture detrás (escritorios, estantes superiores)

&#x20; renderFurnitureBack();

&#x20; // 3. Personajes Z-sorted por Y

&#x20; \[...state.characters].sort((a,b) =>

&#x20;   (a.y + TILE\_SIZE/2 + 0.5) - (b.y + TILE\_SIZE/2 + 0.5)

&#x20; ).forEach(renderCharacter);

&#x20; // 4. Furniture delante (sillas, objetos inferiores)

&#x20; renderFurnitureFront();

&#x20; // 5. Efectos (burbujas, indicadores)

&#x20; renderEffects();

&#x20; ctx.restore();

&#x20; // 6. HUD sin transformación

&#x20; renderHUD();

}

```



\## Offscreen canvas — OBLIGATORIO

```javascript

const bgCanvas = document.createElement('canvas');

bgCanvas.width = MAP\_W \* TILE\_SIZE;

bgCanvas.height = MAP\_H \* TILE\_SIZE;

const bgCtx = bgCanvas.getContext('2d');

bgCtx.imageSmoothingEnabled = false;

// Renderizar fondo UNA vez, blittear en cada frame

```



\## Sprites programáticos

Arrays 2D de colores hex o null (transparente):

```javascript

const SPRITES = {

&#x20; char\_down\_0: \[

&#x20;   \[null,'#5B3A29','#5B3A29',null],

&#x20;   \['#5B3A29','#FDBCB4','#FDBCB4','#5B3A29'],

&#x20;   // ... 16 filas × 8 cols

&#x20; ]

};

function drawSprite(ctx, name, x, y, zoom) {

&#x20; const s = SPRITES\[name];

&#x20; for (let r = 0; r < s.length; r++)

&#x20;   for (let c = 0; c < s\[r].length; c++) {

&#x20;     if (!s\[r]\[c]) continue;

&#x20;     ctx.fillStyle = s\[r]\[c];

&#x20;     ctx.fillRect(Math.floor(x+c\*zoom), Math.floor(y+r\*zoom), zoom, zoom);

&#x20;   }

}

```



\## Sprites requeridos

Personaje (8×16px): char\_down\_0/1, char\_up\_0/1, char\_left\_0/1,

&#x20; char\_sit, char\_type\_0/1, char\_idle\_0/1

Furniture (16×16px): desk, chair\_down, chair\_up, plant, bookshelf, server\_rack

Tiles (16×16px): floor\_dark, floor\_wood, wall\_h, wall\_v,

&#x20; wall\_tl, wall\_tr, wall\_bl, wall\_br

Indicadores (8×8px): ind\_working, ind\_idle, ind\_waiting, ind\_error, ind\_done



\## State machine personajes (FSM)

```javascript

const STATES = { SPAWNING:'spawning', WALKING:'walking',

&#x20; SITTING:'sitting', TYPING:'typing', IDLE:'idle',

&#x20; WAITING:'waiting', ERROR:'error' };

const STATUS\_TO\_STATE = {

&#x20; working: STATES.TYPING, idle: STATES.IDLE,

&#x20; waiting: STATES.WAITING, error: STATES.ERROR, done: STATES.IDLE

};

// Velocidad: WALK\_SPEED = 1.5 tiles/seg

// Frames: FRAME\_DURATION = 200ms

// Sitting offset: -6px Y (igual que Pixel Agents)

```



\## Colorización por departamento

Tint sobre sprite base grayscale → color del dept.

```javascript

const PALETTES = {

&#x20; direccion:     {primary:'#7F77DD',dark:'#3C3489',light:'#CECBF6'},

&#x20; desarrollo:    {primary:'#378ADD',dark:'#0C447C',light:'#B5D4F4'},

&#x20; ux\_ui:         {primary:'#1D9E75',dark:'#085041',light:'#9FE1CB'},

&#x20; qa:            {primary:'#639922',dark:'#27500A',light:'#C0DD97'},

&#x20; marketing:     {primary:'#D85A30',dark:'#712B13',light:'#F5C4B3'},

&#x20; atencion:      {primary:'#BA7517',dark:'#633806',light:'#FAC775'},

&#x20; oportunidades: {primary:'#D4537E',dark:'#72243E',light:'#F4C0D1'},

&#x20; administrativo:{primary:'#888780',dark:'#444441',light:'#D3D1C7'},

};

```



\## BFS Pathfinding (limitado a sala)

```javascript

function bfs(grid, start, end) {

&#x20; const key = (x,y) => `${x},${y}`;

&#x20; const queue = \[\[start]];

&#x20; const visited = new Set(\[key(start.x, start.y)]);

&#x20; const dirs = \[{x:0,y:-1},{x:0,y:1},{x:-1,y:0},{x:1,y:0}];

&#x20; while (queue.length) {

&#x20;   const path = queue.shift();

&#x20;   const cur = path\[path.length-1];

&#x20;   if (cur.x===end.x \&\& cur.y===end.y) return path;

&#x20;   for (const d of dirs) {

&#x20;     const nx=cur.x+d.x, ny=cur.y+d.y, k=key(nx,ny);

&#x20;     if (!visited.has(k) \&\& grid\[ny]?.\[nx]) {

&#x20;       visited.add(k); queue.push(\[...path,{x:nx,y:ny}]);

&#x20;     }

&#x20;   }

&#x20; }

&#x20; return null;

}

```

