"""
Módulo de base de datos SQLite para PulsarMoon Office.
Maneja el esquema, conexiones y todas las operaciones CRUD.
"""
import sqlite3
import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Conexión global — inicializada una vez en setup()
_db_path: str = "office.db"


def setup(db_path: str) -> None:
    """Inicializa la base de datos creando tablas si no existen."""
    global _db_path
    _db_path = db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id    TEXT PRIMARY KEY,
                agent_name  TEXT NOT NULL,
                department  TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'idle',
                task        TEXT DEFAULT '',
                model       TEXT DEFAULT '',
                timestamp   INTEGER,
                metadata    TEXT DEFAULT '{}',
                created_at  INTEGER DEFAULT (unixepoch()),
                updated_at  INTEGER DEFAULT (unixepoch())
            );

            CREATE TABLE IF NOT EXISTS agent_positions (
                agent_id    TEXT PRIMARY KEY,
                desk_index  INTEGER,
                room_id     TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS event_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id    TEXT NOT NULL,
                status      TEXT NOT NULL,
                task        TEXT DEFAULT '',
                timestamp   INTEGER NOT NULL,
                raw_event   TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_event_log_agent ON event_log(agent_id);
            CREATE INDEX IF NOT EXISTS idx_event_log_ts    ON event_log(timestamp);
        """)
    logger.info(f"Base de datos inicializada en: {db_path}")


def _connect() -> sqlite3.Connection:
    """Abre una conexión SQLite con row_factory para dicts."""
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ─── Agentes ───────────────────────────────────────────────────────────────────

def upsert_agent(event: dict) -> None:
    """Inserta o actualiza un agente desde un evento JSON."""
    now = int(time.time())
    with _connect() as conn:
        conn.execute("""
            INSERT INTO agents (agent_id, agent_name, department, status, task, model, timestamp, metadata, created_at, updated_at)
            VALUES (:agent_id, :agent_name, :department, :status, :task, :model, :timestamp, :metadata, :now, :now)
            ON CONFLICT(agent_id) DO UPDATE SET
                agent_name  = excluded.agent_name,
                department  = excluded.department,
                status      = excluded.status,
                task        = excluded.task,
                model       = excluded.model,
                timestamp   = excluded.timestamp,
                metadata    = excluded.metadata,
                updated_at  = :now
        """, {
            "agent_id":   event["agent_id"],
            "agent_name": event["agent_name"],
            "department": event["department"],
            "status":     event.get("status", "idle"),
            "task":       event.get("task", ""),
            "model":      event.get("model", ""),
            "timestamp":  event.get("timestamp", now),
            "metadata":   json.dumps(event.get("metadata", {})),
            "now":        now,
        })


def get_agent(agent_id: str) -> Optional[dict]:
    """Devuelve un agente por ID, o None si no existe."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM agents WHERE agent_id = ?", (agent_id,)
        ).fetchone()
    if row is None:
        return None
    return _row_to_agent(row)


def get_all_agents() -> list[dict]:
    """Devuelve todos los agentes registrados."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM agents ORDER BY department, agent_name"
        ).fetchall()
    return [_row_to_agent(r) for r in rows]


def delete_agent(agent_id: str) -> None:
    """Elimina un agente y sus datos relacionados."""
    with _connect() as conn:
        conn.execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,))
    logger.info(f"Agente eliminado: {agent_id}")


def _row_to_agent(row: sqlite3.Row) -> dict:
    """Convierte una fila de SQLite a dict serializable."""
    d = dict(row)
    # Parsear metadata JSON
    try:
        d["metadata"] = json.loads(d.get("metadata") or "{}")
    except (json.JSONDecodeError, TypeError):
        d["metadata"] = {}
    return d


# ─── Posiciones ────────────────────────────────────────────────────────────────

def upsert_agent_position(agent_id: str, desk_index: int, room_id: str) -> None:
    """Asigna o actualiza la posición (escritorio) de un agente."""
    with _connect() as conn:
        conn.execute("""
            INSERT INTO agent_positions (agent_id, desk_index, room_id)
            VALUES (?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
                desk_index = excluded.desk_index,
                room_id    = excluded.room_id
        """, (agent_id, desk_index, room_id))


def get_agent_position(agent_id: str) -> Optional[dict]:
    """Devuelve la posición asignada de un agente."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM agent_positions WHERE agent_id = ?", (agent_id,)
        ).fetchone()
    return dict(row) if row else None


def get_all_positions() -> list[dict]:
    """Devuelve todas las posiciones asignadas."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM agent_positions").fetchall()
    return [dict(r) for r in rows]


# ─── Event log ─────────────────────────────────────────────────────────────────

def log_event(event: dict) -> None:
    """Registra un evento en el log histórico."""
    now = int(time.time())
    with _connect() as conn:
        conn.execute("""
            INSERT INTO event_log (agent_id, status, task, timestamp, raw_event)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event["agent_id"],
            event.get("status", "idle"),
            event.get("task", ""),
            event.get("timestamp", now),
            json.dumps(event, ensure_ascii=False),
        ))


def get_recent_events(limit: int = 100) -> list[dict]:
    """Devuelve los eventos más recientes del log."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM event_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_agent_events(agent_id: str, limit: int = 50) -> list[dict]:
    """Devuelve los eventos recientes de un agente específico."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM event_log WHERE agent_id = ? ORDER BY timestamp DESC LIMIT ?",
            (agent_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]
