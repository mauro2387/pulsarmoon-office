"""
Clase base para todos los agentes de PulsarMoon.
Maneja eventos, logging a PostgreSQL y envío de WhatsApp.
"""
import json
import logging
import time
from pathlib import Path

import requests
from db.database import get_db

logger = logging.getLogger(__name__)

EVENTS_DIR = Path(__file__).parent / "events"
CONTEXT_FILE = Path(__file__).parent / "marketing" / "context.md"
WA_API = "https://wa.vydre.me/send"

VALID_STATUSES = {"idle", "working", "waiting", "error", "done"}


class BaseAgent:
    """Clase base que todos los agentes de PulsarMoon heredan."""

    def __init__(self, agent_id: str, agent_name: str,
                 department: str, model: str = "sonnet-4"):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.department = department
        self.model = model

    def write_event(self, status: str, task: str = "") -> None:
        """Escribe estado actual en agents/events/{agent_id}.json."""
        if status not in VALID_STATUSES:
            logger.warning("Estado inválido: %s", status)
            return
        event = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "department": self.department,
            "status": status,
            "task": task,
            "model": self.model,
            "timestamp": int(time.time()),
        }
        EVENTS_DIR.mkdir(parents=True, exist_ok=True)
        path = EVENTS_DIR / f"{self.agent_id}.json"
        path.write_text(json.dumps(event, ensure_ascii=False), encoding="utf-8")

    def log(self, action: str, data: dict = None) -> None:
        """Guarda log de acción en PostgreSQL tabla agent_logs."""
        try:
            db = get_db()
            db.execute(
                """INSERT INTO agent_logs (agent_id, action, data)
                   VALUES (%s, %s, %s)""",
                (self.agent_id, action, json.dumps(data or {}))
            )
        except Exception as e:
            logger.error("Error guardando log en DB: %s", e)

    def send_whatsapp(self, number: str, message: str) -> bool:
        """Envía mensaje vía API de WhatsApp. Retorna True si fue exitoso."""
        try:
            resp = requests.post(
                WA_API,
                json={"number": number, "message": message},
                timeout=15,
            )
            ok = resp.status_code == 200
            if not ok:
                logger.error("WhatsApp API error %d: %s", resp.status_code, resp.text)
            return ok
        except requests.RequestException as e:
            logger.error("Error enviando WhatsApp: %s", e)
            return False

    def read_context(self) -> str:
        """Lee el archivo de contexto de marca y lo retorna como string."""
        if CONTEXT_FILE.exists():
            return CONTEXT_FILE.read_text(encoding="utf-8")
        logger.warning("Archivo de contexto no encontrado: %s", CONTEXT_FILE)
        return ""
