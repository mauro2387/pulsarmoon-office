"""
Agente Project Manager de PulsarMoon.
Genera roadmaps con Gemini 2.5 Pro, gestiona proyectos en PostgreSQL.
Todo lo demás es Python puro y SQL — sin LLM.
"""
import json
import logging
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

from google import genai
from dotenv import load_dotenv

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.base_agent import BaseAgent
from db.database import get_db

load_dotenv()
logger = logging.getLogger(__name__)

MAURO_PHONE = os.getenv("MAURO_PHONE", "59891722750")
WA_URL = "http://192.168.1.11:3000/send"

# Emojis por fase para formato WhatsApp
_PHASE_EMOJI = {
    "demo": "🔬", "development": "⚙️",
    "testing": "🧪", "delivery": "🚀",
}


class PMAgent(BaseAgent):
    """Project Manager — roadmap con Gemini, gestión con Python."""

    def __init__(self):
        super().__init__(
            agent_id="pm-01",
            agent_name="Project Manager",
            department="pm",
            model="gemini",
            company_id="pulsarmoon",
        )
        self._gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # ── Gemini 2.5 Pro — ÚNICA llamada LLM del agente ──
    def generate_roadmap(self, brief: str, client: str,
                         deadline: str) -> dict | None:
        """Genera roadmap completo con Gemini. Reintenta 1 vez."""
        self.write_event("working", "Generando roadmap...")
        prompt = (
            "Sos el Project Manager de PulsarMoon. "
            "Generá un roadmap completo y realista para este proyecto.\n\n"
            f"Cliente: {client}\nDeadline: {deadline}\n"
            f"Fecha de hoy: {date.today().isoformat()}\n"
            f"Brief:\n{brief}\n\n"
            "Retorná SOLO un JSON válido con esta estructura exacta, "
            "sin markdown, sin explicaciones:\n"
            '{"phases":[{"name":"demo","status":"pending",'
            '"week_range":"semana 1","started_at":null,'
            '"finished_at":null,"tasks":[{"id":"T-001",'
            '"title":"título","description":"desc",'
            '"status":"pending","finished_at":null}]},'
            '{"name":"development",...},'
            '{"name":"testing",...},'
            '{"name":"delivery",...}]}\n\n'
            "Reglas:\n"
            "- Las 4 fases SIEMPRE: demo, development, testing, delivery\n"
            "- Calculá week_range basándote en deadline y hoy\n"
            "- Cada fase: 3-8 tareas realistas\n"
            "- Development debe ser la más detallada\n"
            "- IDs correlativos globales: T-001, T-002...\n"
            "- Solo retorná el JSON, nada más"
        )

        for attempt in range(2):
            try:
                resp = self._gemini.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=self.context + "\n\n" + prompt,
                    config={"temperature": 0.2},
                )
                text = resp.text.strip()
                # Limpiar backticks si Gemini los agrega
                if text.startswith("```"):
                    text = text.split("\n", 1)[1]
                    text = text.rsplit("```", 1)[0].strip()
                roadmap = json.loads(text)

                usage = getattr(resp, "usage_metadata", None)
                self.log("gemini_call", {
                    "attempt": attempt + 1,
                    "input_tokens": getattr(usage, "prompt_token_count", 0),
                    "output_tokens": getattr(usage, "candidates_token_count", 0),
                })
                self.write_event("done", "Roadmap generado")
                return roadmap
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Gemini JSON inválido (intento %d): %s",
                               attempt + 1, e)
            except Exception as e:
                logger.error("Error Gemini (intento %d): %s",
                             attempt + 1, e)

        self.write_event("error", "Gemini falló 2 veces")
        return None

    # ── Python puro, sin LLM ──
    def create_project(self, dev_session_token: str) -> str | None:
        """Crea proyecto desde sesión de dev completada."""
        self.write_event("working", "Creando proyecto...")
        db = get_db()
        session = db.fetchone(
            "SELECT * FROM dev_sessions WHERE token = %s",
            (dev_session_token,))
        if not session:
            return None

        raw = session.get("form_data")
        form = json.loads(raw) if isinstance(raw, str) else (raw or {})
        brief = session.get("brief_prompt", "")
        client = form.get("nombre_negocio", "Cliente")
        deadline = form.get("plazo", "4 semanas")
        tipo = form.get("tipo_proyecto", "web")
        vercel_url = session.get("vercel_url", "")

        # Generar ID: PM-2026-001, PM-2026-002...
        year = date.today().year
        last = db.fetchone(
            "SELECT id FROM projects WHERE id LIKE %s "
            "ORDER BY id DESC LIMIT 1",
            (f"PM-{year}-%",))
        if last:
            seq = int(last["id"].split("-")[2]) + 1
        else:
            seq = 1
        project_id = f"PM-{year}-{seq:03d}"

        roadmap = self.generate_roadmap(brief, client, deadline)
        if roadmap is None:
            return None

        title = f"{tipo.capitalize()} — {client}"
        db.execute(
            """INSERT INTO projects
               (id, company_id, client, type, title, description,
                deadline, phases, link_production, logs)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (project_id, self.company_id, client, tipo, title,
             brief[:500], deadline,
             json.dumps(roadmap, ensure_ascii=False),
             vercel_url,
             json.dumps([{
                 "event": "project_created",
                 "ts": datetime.now().isoformat(),
                 "token": dev_session_token,
             }])),
        )
        self.log("project_created", {"project_id": project_id})
        self.write_event("done", f"Proyecto {project_id} creado")
        return project_id

    # ── Python puro, sin LLM ──
    def format_whatsapp_message(self, project_id: str) -> str:
        """Formatea mensaje de WhatsApp con roadmap completo."""
        db = get_db()
        p = db.fetchone("SELECT * FROM projects WHERE id = %s",
                        (project_id,))
        if not p:
            return ""
        phases = p["phases"]
        if isinstance(phases, str):
            phases = json.loads(phases)
        phase_list = phases.get("phases", phases) if isinstance(
            phases, dict) else phases

        lines = [
            f"📋 *NUEVO PROYECTO: {p['title']}*",
            f"👤 Cliente: {p['client']}",
            f"📅 Deadline: {p['deadline'] or 'pendiente'}",
            f"🔗 Producción: {p['link_production'] or 'pendiente'}",
            "", "🗺️ *ROADMAP:*", "",
        ]
        for phase in phase_list:
            emoji = _PHASE_EMOJI.get(phase["name"], "📌")
            wr = phase.get("week_range", "")
            lines.append(f"{emoji} *{phase['name'].upper()}* ({wr})")
            for t in phase.get("tasks", []):
                lines.append(f"  • {t['id']}: {t['title']}")
            lines.append("")

        budget = float(p.get("budget_agreed") or 0)
        lines.append(f"💰 Presupuesto: ${budget:.0f} USD")
        lines.append("")
        lines.append("Respondé *APROBAR* o *RECHAZAR*")
        return "\n".join(lines)

    # ── Python puro, sin LLM ──
    def notify_mauro(self, project_id: str) -> bool:
        """Envía roadmap a Mauro por WhatsApp con reintentos."""
        msg = self.format_whatsapp_message(project_id)
        if not msg:
            return False
        for attempt in range(3):
            try:
                body = json.dumps({"number": MAURO_PHONE,
                                   "message": msg}).encode()
                req = Request(WA_URL, data=body, method="POST",
                              headers={"Content-Type": "application/json"})
                resp = urlopen(req, timeout=30)
                if resp.status == 200:
                    self.log("whatsapp_sent", {"project_id": project_id})
                    return True
            except (URLError, OSError) as e:
                logger.warning("WhatsApp intento %d: %s", attempt + 1, e)
                if attempt < 2:
                    time.sleep(10)
        return False

    # ── Python puro, sin LLM ──
    def approve(self, project_id: str) -> bool:
        """Aprueba proyecto — activa el roadmap."""
        db = get_db()
        p = db.fetchone("SELECT * FROM projects WHERE id = %s",
                        (project_id,))
        if not p:
            return False
        logs = p.get("logs", [])
        if isinstance(logs, str):
            logs = json.loads(logs)
        logs.append({"event": "roadmap_approved",
                     "ts": datetime.now().isoformat()})
        db.execute(
            """UPDATE projects SET status='active', logs=%s
               WHERE id = %s""",
            (json.dumps(logs), project_id))
        self.log("project_approved", {"project_id": project_id})
        # Confirmar por WhatsApp
        body = json.dumps({
            "number": MAURO_PHONE,
            "message": f"✅ Proyecto *{p['title']}* activado.",
        }).encode()
        try:
            req = Request(WA_URL, data=body, method="POST",
                          headers={"Content-Type": "application/json"})
            urlopen(req, timeout=30)
        except (URLError, OSError):
            pass
        return True

    # ── Python puro, sin LLM ──
    def reject(self, project_id: str) -> bool:
        """Rechaza proyecto — lo cancela."""
        db = get_db()
        p = db.fetchone("SELECT * FROM projects WHERE id = %s",
                        (project_id,))
        if not p:
            return False
        logs = p.get("logs", [])
        if isinstance(logs, str):
            logs = json.loads(logs)
        logs.append({"event": "project_cancelled",
                     "ts": datetime.now().isoformat()})
        db.execute(
            """UPDATE projects SET status='cancelled', logs=%s
               WHERE id = %s""",
            (json.dumps(logs), project_id))
        self.log("project_rejected", {"project_id": project_id})
        return True


# Instancia global
_agent = PMAgent()
