// Estado global de la aplicacion — unica fuente de verdad
const state = {
  // Agentes: agent_id -> objeto agente (del backend)
  agents: new Map(),

  // Personajes visuales: agent_id -> Character instance
  characters: new Map(),

  // Camara: posicion en pixels del mundo, zoom entero
  camera: {
    x:    0,
    y:    0,
    zoom: 3,  // zoom inicial 3x — sprites detallados
  },

  // Agente seleccionado (agent_id string o null)
  selectedAgent: null,

  // Estado de la conexion WebSocket
  wsConnected: false,
};
