\# Backend — Python WebSocket + SQLite + Flask



\## Stack

\- websockets>=12.0 (asyncio)

\- watchdog>=4.0.0

\- flask>=3.0.0 + flask-cors>=4.0.0

\- sqlite3 built-in



\## Protocolo WebSocket



\### Servidor → cliente

```json

// Al conectar

{"type":"initial\_state","agents":\[...],"timestamp":123}

// Update

{"type":"agent\_update","agent":{...},"timestamp":123}

// Eliminado

{"type":"agent\_removed","agent\_id":"x","timestamp":123}

// Keepalive

{"type":"ping","timestamp":123}

```



\### Cliente → servidor

```json

{"type":"pong"}

{"type":"request\_state"}

```



\## Flujo de datos

```

Agente escribe {id}.json → watchdog (\~50ms) →

valida JSON → upsert SQLite → insert event\_log →

ws\_server broadcast → browser → state.js →

characters.js FSM → renderer próximo frame

```



\## Esquema SQLite

```sql

CREATE TABLE IF NOT EXISTS agents (

&#x20; agent\_id TEXT PRIMARY KEY, agent\_name TEXT NOT NULL,

&#x20; department TEXT NOT NULL, status TEXT DEFAULT 'idle',

&#x20; task TEXT DEFAULT '', model TEXT DEFAULT '',

&#x20; timestamp INTEGER, metadata TEXT DEFAULT '{}',

&#x20; created\_at INTEGER DEFAULT (unixepoch()),

&#x20; updated\_at INTEGER DEFAULT (unixepoch())

);

CREATE TABLE IF NOT EXISTS agent\_positions (

&#x20; agent\_id TEXT PRIMARY KEY, desk\_index INTEGER, room\_id TEXT,

&#x20; FOREIGN KEY(agent\_id) REFERENCES agents(agent\_id) ON DELETE CASCADE

);

CREATE TABLE IF NOT EXISTS event\_log (

&#x20; id INTEGER PRIMARY KEY AUTOINCREMENT,

&#x20; agent\_id TEXT NOT NULL, status TEXT NOT NULL,

&#x20; task TEXT DEFAULT '', timestamp INTEGER NOT NULL,

&#x20; raw\_event TEXT NOT NULL

);

CREATE INDEX IF NOT EXISTS idx\_event\_log\_agent ON event\_log(agent\_id);

CREATE INDEX IF NOT EXISTS idx\_event\_log\_ts ON event\_log(timestamp);

```



\## Escritura atómica de eventos (demo\_agents.py)

```python

tmp = filepath + '.tmp'

with open(tmp, 'w', encoding='utf-8') as f:

&#x20;   json.dump(event, f, ensure\_ascii=False)

os.replace(tmp, filepath)  # atómico en Linux

```



\## Flask endpoints

\- GET /health → {status, uptime, agents\_total, agents\_active}

\- GET /agents → {agents:\[...], count, timestamp}

\- GET /agents/{id} → agente o 404

\- GET /events?limit=50 → últimos eventos del log



\## Variables de entorno

```bash

SUPABASE\_URL=https://xxx.supabase.co

SUPABASE\_KEY=eyJ...

CLOUDFLARE\_TUNNEL\_TOKEN=eyJ...

OFFICE\_WS\_URL=ws://localhost:8765

OFFICE\_API\_URL=http://localhost:8766

```



\## config.json

```json

{

&#x20; "server":{"host":"0.0.0.0","ws\_port":8765,"api\_port":8766,"ws\_ping\_interval":30},

&#x20; "paths":{"events\_dir":"agents/events","db\_path":"office.db","logs\_dir":"logs"},

&#x20; "office":{"map\_width\_tiles":80,"map\_height\_tiles":60,"tile\_size":16},

&#x20; "demo":{"enabled":true,"update\_interval\_min":3,"update\_interval\_max":8},

&#x20; "supabase":{"enabled":false,"url":"","key":"","sync\_interval\_seconds":60}

}

```

