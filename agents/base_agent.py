"""
Clase base para todos los agentes de PulsarMoon.
Multi-empresa, LLM centralizado con cache, WhatsApp, logging a PostgreSQL.
"""
import json
import logging
import os
import time
from pathlib import Path

import requests
from anthropic import Anthropic
from dotenv import load_dotenv

from db.database import get_db

load_dotenv()
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVENTS_DIR = PROJECT_ROOT / "agents" / "events"
WA_API = "https://wa.vydre.me/send"
VALID_STATUSES = {"idle", "working", "waiting", "error", "done"}

# Mapeo de modelos cortos a IDs oficiales
_MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-20250514",
}


class BaseAgent:
    """Clase base que todos los agentes de PulsarMoon heredan."""

    def __init__(self, agent_id: str, agent_name: str, department: str,
                 model: str = "haiku", company_id: str = "pulsarmoon"):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.department = department
        self.model = model
        self.company_id = company_id
        self.context = self._load_context()
        self._llm_client = None

    def _load_context(self) -> str:
        """Lee contexto de la empresa desde companies/{id}/context.md."""
        path = PROJECT_ROOT / "companies" / self.company_id / "context.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        # Fallback al viejo path
        fallback = PROJECT_ROOT / "agents" / "marketing" / "context.md"
        if fallback.exists():
            logger.warning("Usando context.md fallback de marketing/")
            return fallback.read_text(encoding="utf-8")
        logger.warning("Sin context.md para %s", self.company_id)
        return ""

    def _get_llm(self) -> Anthropic:
        """Cliente Anthropic lazy-init."""
        if self._llm_client is None:
            self._llm_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        return self._llm_client

    def write_event(self, status: str, task: str = "") -> None:
        """Escribe estado en agents/events/{agent_id}.json."""
        if status not in VALID_STATUSES:
            return
        event = {
            "agent_id": self.agent_id, "agent_name": self.agent_name,
            "department": self.department, "status": status,
            "task": task, "model": self.model, "timestamp": int(time.time()),
        }
        EVENTS_DIR.mkdir(parents=True, exist_ok=True)
        (EVENTS_DIR / f"{self.agent_id}.json").write_text(
            json.dumps(event, ensure_ascii=False), encoding="utf-8")

    def log(self, action: str, data: dict = None) -> None:
        """Guarda log en PostgreSQL agent_logs."""
        try:
            get_db().execute(
                "INSERT INTO agent_logs (agent_id, action, data, company_id) "
                "VALUES (%s, %s, %s, %s)",
                (self.agent_id, action, json.dumps(data or {}), self.company_id))
        except Exception as e:
            logger.error("Error log DB: %s", e)

    def send_whatsapp(self, number: str, message: str) -> bool:
        """Envía mensaje vía API WhatsApp."""
        try:
            r = requests.post(WA_API, json={"number": number, "message": message}, timeout=15)
            return r.status_code == 200
        except requests.RequestException as e:
            logger.error("Error WhatsApp: %s", e)
            return False

    def call_llm(self, user_message: str, system_extra: str = "",
                 max_tokens: int = 1000, temperature: float = 0.3) -> str:
        """Llamada centralizada a LLM con cache ephemeral en contexto."""
        sys_text = self.context + ("\n\n" + system_extra if system_extra else "")
        system = [{"type": "text", "text": sys_text,
                    "cache_control": {"type": "ephemeral"}}]
        try:
            resp = self._get_llm().messages.create(
                model=_MODELS.get(self.model, self.model),
                max_tokens=max_tokens, temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user_message}])
            usage = {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens}
            self.log("llm_call", {"model": self.model, "tokens": usage})
            return resp.content[0].text
        except Exception as e:
            logger.error("Error LLM: %s", e)
            return ""

    def call_llm_json(self, user_message: str, system_extra: str = "",
                      max_tokens: int = 1000) -> dict:
        """Igual que call_llm pero parsea respuesta como JSON."""
        extra = (system_extra + "\n\n" if system_extra else "")
        extra += "Responde SOLO con JSON válido, sin texto extra ni backticks."
        text = self.call_llm(user_message, extra, max_tokens, temperature=0)
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Error parseando JSON de LLM: %s", e)
            return {}

    def format_message(self, template: str, **kwargs) -> str:
        """Formatea template de mensaje sin gastar LLM."""
        return template.format(**kwargs)
