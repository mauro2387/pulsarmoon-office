// BFS pathfinding sobre walkableGrid — limitado a tiles walkable

// BFS clasico: retorna array de {x,y} o null si no hay ruta
function bfs(grid, start, end) {
  const key = (x, y) => `${x},${y}`;
  const queue = [[start]];
  const visited = new Set([key(start.x, start.y)]);
  const dirs = [
    { x: 0, y: -1 },  // arriba
    { x: 0, y:  1 },  // abajo
    { x: -1, y: 0 },  // izquierda
    { x:  1, y: 0 },  // derecha
  ];

  while (queue.length) {
    const path = queue.shift();
    const cur = path[path.length - 1];
    if (cur.x === end.x && cur.y === end.y) return path;

    for (const d of dirs) {
      const nx = cur.x + d.x;
      const ny = cur.y + d.y;
      const k = key(nx, ny);
      if (!visited.has(k) && grid[ny]?.[nx]) {
        visited.add(k);
        queue.push([...path, { x: nx, y: ny }]);
      }
    }
  }
  return null;
}

// Wrapper de conveniencia — usa el walkableGrid global
function findPath(startTile, endTile) {
  return bfs(walkableGrid, startTile, endTile);
}
