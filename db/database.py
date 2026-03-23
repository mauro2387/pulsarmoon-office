"""
Conexión central a PostgreSQL para PulsarMoon.
Singleton con reconexión automática y context managers.
"""
import logging
import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_instance = None


class Database:
    """Conexión PostgreSQL con reconexión automática."""

    def __init__(self):
        self._conn = None
        self._config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "dbname": os.getenv("DB_NAME", "pulsarmoon_db"),
            "user": os.getenv("DB_USER", "pulsarmoon"),
            "password": os.getenv("DB_PASS", ""),
        }
        self._connect()

    def _connect(self):
        """Establece conexión al servidor PostgreSQL."""
        try:
            self._conn = psycopg2.connect(**self._config)
            self._conn.autocommit = False
            logger.info("Conectado a PostgreSQL: %s@%s/%s",
                        self._config["user"], self._config["host"],
                        self._config["dbname"])
        except psycopg2.Error as e:
            logger.error("Error conectando a PostgreSQL: %s", e)
            self._conn = None

    def _ensure_connection(self):
        """Reconecta si la conexión se perdió."""
        if self._conn is None or self._conn.closed:
            logger.warning("Reconectando a PostgreSQL...")
            self._connect()
        else:
            try:
                # Verificar que la conexión sigue viva
                with self._conn.cursor() as cur:
                    cur.execute("SELECT 1")
            except psycopg2.Error:
                logger.warning("Conexión perdida, reconectando...")
                self._connect()

    @contextmanager
    def _cursor(self):
        """Context manager que provee cursor con commit/rollback automático."""
        self._ensure_connection()
        if self._conn is None:
            raise psycopg2.OperationalError("Sin conexión a PostgreSQL")
        try:
            with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
                self._conn.commit()
        except psycopg2.Error as e:
            self._conn.rollback()
            logger.error("Error en query: %s", e)
            raise

    def execute(self, query: str, params: tuple = None) -> int:
        """Ejecuta INSERT/UPDATE/DELETE. Retorna filas afectadas."""
        with self._cursor() as cur:
            cur.execute(query, params)
            return cur.rowcount

    def fetchone(self, query: str, params: tuple = None) -> dict | None:
        """Retorna un registro como dict o None."""
        with self._cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def fetchall(self, query: str, params: tuple = None) -> list[dict]:
        """Retorna lista de registros como dicts."""
        with self._cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def close(self):
        """Cierra la conexión."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("Conexión PostgreSQL cerrada.")

    def setup_tables(self):
        """Crea tablas base si no existen."""
        with self._cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    whatsapp TEXT,
                    context_path TEXT,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id SERIAL PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    data JSONB DEFAULT '{}',
                    company_id TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS content (
                    id SERIAL PRIMARY KEY,
                    topic TEXT NOT NULL,
                    blog TEXT NOT NULL,
                    caption_ig TEXT NOT NULL,
                    caption_fb TEXT NOT NULL,
                    image_url TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    reviewed_at TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id SERIAL PRIMARY KEY,
                    business_name TEXT NOT NULL,
                    phone TEXT,
                    sector TEXT,
                    city TEXT,
                    source TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    score INTEGER DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'new',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                INSERT INTO companies (id, name, whatsapp, context_path)
                VALUES
                    ('pulsarmoon', 'PulsarMoon', '59891722750',
                     'companies/pulsarmoon/context.md'),
                    ('verlyx', 'Verlyx', NULL,
                     'companies/verlyx/context.md')
                ON CONFLICT DO NOTHING
            """)
        logger.info("Tablas base creadas/verificadas.")

    def setup_intelligence_tables(self):
        """Crea tablas para el agente de inteligencia de mercado."""
        with self._cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS raw_intelligence (
                    id SERIAL PRIMARY KEY,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    content TEXT,
                    collected_at TIMESTAMP DEFAULT NOW(),
                    week_number INTEGER,
                    year INTEGER
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS intelligence_insights (
                    id SERIAL PRIMARY KEY,
                    week_number INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    hot_sectors JSONB,
                    prospector_queries JSONB,
                    marketing_topic TEXT,
                    marketing_keywords JSONB,
                    opportunity_summary TEXT,
                    raw_signals_count INTEGER,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(week_number, year)
                )
            """)
        logger.info("Tablas de inteligencia creadas/verificadas.")


def get_db() -> Database:
    """Retorna instancia singleton de Database."""
    global _instance
    if _instance is None:
        _instance = Database()
    return _instance
