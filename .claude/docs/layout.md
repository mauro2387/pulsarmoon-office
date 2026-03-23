\# Layout — Mapa y Salas



\## Sistema de coordenadas

\- Tile: 16×16 px

\- Mapa: 80×60 tiles = 1280×960 px (mundo)

\- Canvas: 100% viewport

\- Pasillos: 2 tiles entre salas



\## Layout (80×60 tiles)

```

Col:  0    20  22    42  44    64  66   80

&#x20;     ┌─────┬──┬─────┬──┬──────────┐

R 0   │DIR  │P │DEV  │P │          │

R 14  ├─────┤A ├─────┤A │ SERVER   │

R 16  │UX   │S │QA   │S │ (14×60t) │

R 30  ├─────┤I ├─────┤I │          │

R 32  │MKT  │L │CLI  │L │          │

R 46  ├─────┤L ├─────┤L │          │

R 48  │OPP  │O │ADM  │O │          │

R 60  └─────┴──┴─────┴──┴──────────┘

P = pasillo 2 tiles

```



\## Definición de salas

```javascript

const ROOMS = \[

&#x20; {id:'direccion',    name:'Dirección',    color:'#7F77DD', x:0,  y:0,  w:20, h:14, desks:3},

&#x20; {id:'desarrollo',   name:'Desarrollo',   color:'#378ADD', x:22, y:0,  w:20, h:14, desks:5},

&#x20; {id:'ux\_ui',        name:'UX / UI',      color:'#1D9E75', x:0,  y:16, w:20, h:14, desks:4},

&#x20; {id:'qa',           name:'QA',           color:'#639922', x:22, y:16, w:20, h:14, desks:4},

&#x20; {id:'marketing',    name:'Marketing',    color:'#D85A30', x:0,  y:32, w:20, h:14, desks:5},

&#x20; {id:'atencion',     name:'Atención',     color:'#BA7517', x:22, y:32, w:20, h:14, desks:4},

&#x20; {id:'oportunidades',name:'Oportunidades',color:'#D4537E', x:0,  y:48, w:20, h:14, desks:4},

&#x20; {id:'administrativo',name:'Admin',       color:'#888780', x:22, y:48, w:20, h:14, desks:4},

&#x20; {id:'servidores',   name:'Servidores',   color:'#2C2C2A', x:66, y:0,  w:14, h:60, desks:0},

];

```



\## Colores de piso (semi-transparente sobre fondo oscuro)

```javascript

const FLOOR\_COLORS = {

&#x20; direccion:     'rgba(127,119,221,0.15)',

&#x20; desarrollo:    'rgba(55,138,221,0.15)',

&#x20; ux\_ui:         'rgba(29,158,117,0.15)',

&#x20; qa:            'rgba(99,153,34,0.15)',

&#x20; marketing:     'rgba(216,90,48,0.15)',

&#x20; atencion:      'rgba(186,117,23,0.15)',

&#x20; oportunidades: 'rgba(212,83,126,0.15)',

&#x20; administrativo:'rgba(136,135,128,0.15)',

&#x20; servidores:    'rgba(44,44,42,0.5)',

};

```



\## Colores globales de la oficina (SIEMPRE oscuros)

```css

\--office-bg: #0d0d1a;

\--wall-fill: #12122a;

\--wall-border: #1e1e3f;

\--floor-base: #16162e;

```

