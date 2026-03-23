"""
Base de datos SQLite para contenido de marketing generado.
Guarda blog posts, captions de Instagram y Facebook con estado de aprobación.
"""
import sqlite3
import json
import time
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "marketing.db"


def get_conn() -> sqlite3.Connection:
    """Retorna conexión a SQLite con row_factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Crea las tablas si no existen."""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at REAL NOT NULL,
            trend_keyword TEXT NOT NULL,
            trend_score REAL DEFAULT 0,
            blog_post TEXT NOT NULL,
            caption_ig TEXT NOT NULL,
            caption_fb TEXT NOT NULL,
            image_url TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            reviewed_at REAL,
            notes TEXT DEFAULT ''
        )
    """)
    # Migración: agregar columna image_url si la tabla ya existía sin ella
    try:
        conn.execute("ALTER TABLE content ADD COLUMN image_url TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # Ya existe la columna
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trends_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetched_at REAL NOT NULL,
            keywords_json TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_content(trend_keyword: str, trend_score: float,
                 blog_post: str, caption_ig: str, caption_fb: str,
                 image_url: str = "") -> int:
    """Guarda contenido generado. Retorna el ID."""
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO content
           (created_at, trend_keyword, trend_score, blog_post, caption_ig, caption_fb, image_url, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
        (time.time(), trend_keyword, trend_score, blog_post, caption_ig, caption_fb, image_url)
    )
    content_id = cur.lastrowid
    conn.commit()
    conn.close()
    return content_id


def save_trends(keywords: list[dict]) -> None:
    """Guarda log de tendencias obtenidas."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO trends_log (fetched_at, keywords_json) VALUES (?, ?)",
        (time.time(), json.dumps(keywords, ensure_ascii=False))
    )
    conn.commit()
    conn.close()


def get_all_content(status: Optional[str] = None) -> list[dict]:
    """Retorna todo el contenido, opcionalmente filtrado por estado."""
    conn = get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM content WHERE status = ? ORDER BY created_at DESC",
            (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM content ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_content_by_id(content_id: int) -> Optional[dict]:
    """Retorna una pieza de contenido por ID."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM content WHERE id = ?", (content_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_status(content_id: int, status: str, notes: str = "") -> bool:
    """Actualiza estado: pending/approved/rejected."""
    if status not in ("pending", "approved", "rejected"):
        return False
    conn = get_conn()
    conn.execute(
        "UPDATE content SET status = ?, reviewed_at = ?, notes = ? WHERE id = ?",
        (status, time.time(), notes, content_id)
    )
    conn.commit()
    conn.close()
    return True


def get_recent_keywords(limit: int = 5) -> list[str]:
    """Retorna los últimos N keywords usados para no repetir temas."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT trend_keyword FROM content ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [r["trend_keyword"] for r in rows]


# Inicializar al importar
init_db()
