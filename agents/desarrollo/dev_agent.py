"""
Agente de Desarrollo de PulsarMoon.
Genera briefs técnicos (Sonnet), coordina con Copilot vía relay bridge.
Sesiones controladas por token, solo Mauro puede crearlas.
"""
import json
import logging
import os
import secrets
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.base_agent import BaseAgent
from db.database import get_db

logger = logging.getLogger(__name__)

BRIDGE_URL = "https://bridge.vydre.me"
FORM_BASE = "https://forms.vydre.me/dev"
TOKEN_EXPIRY_HOURS = 24


class DevAgent(BaseAgent):
    """Genera briefs técnicos y coordina desarrollo con Copilot."""

    def __init__(self):
        super().__init__(
            agent_id="dev-01",
            agent_name="Arquitecto",
            department="desarrollo",
            model="sonnet",
            company_id="pulsarmoon",
        )

    # ── Python puro, sin LLM ──
    def create_session(self, phone: str) -> dict:
        """Crea sesión de desarrollo con token único."""
        token = secrets.token_urlsafe(8)
        db = get_db()
        db.execute(
            """INSERT INTO dev_sessions (token, phone, status)
               VALUES (%s, %s, 'pending')""",
            (token, phone),
        )
        url = f"{FORM_BASE}?token={token}"
        self.log("session_created", {"token": token, "phone": phone})
        return {"token": token, "url": url}

    # ── LLM (Sonnet) — 1 llamada por proyecto ~~$0.01 ──
    def process_form(self, token: str, form_data: dict) -> str:
        """Genera brief técnico para Copilot desde los datos del form."""
        self.write_event("working", "Generando brief técnico...")
        db = get_db()

        nombre = form_data.get("nombre_negocio", "")
        nombre_safe = "".join(
            c if c.isalnum() or c in "-_ " else ""
            for c in nombre
        ).strip().replace(" ", "_").lower().replace("/", "_")

        workspace_path = (
            f"C:\\Users\\mauro\\OneDrive\\Desktop"
            f"\\projects\\{nombre_safe}"
        )

        # Crear carpeta del proyecto directamente
        os.makedirs(workspace_path, exist_ok=True)
        logger.info("Carpeta del proyecto creada: %s", workspace_path)

        # Guardar workspace_path en form_data para send_to_copilot
        form_data_dict = form_data if isinstance(form_data, dict) else json.loads(form_data)
        db.execute(
            """UPDATE dev_sessions
               SET form_data = %s, updated_at = NOW()
               WHERE token = %s""",
            (json.dumps({**form_data_dict, "workspace_path": workspace_path},
                        ensure_ascii=False), token),
        )

        prompt = (
            "Generá un prompt técnico detallado para GitHub Copilot Agent "
            "para crear el siguiente proyecto:\n\n"
            f"Tipo: {form_data.get('tipo_proyecto', '')}\n"
            f"Negocio: {nombre} ({form_data.get('rubro', '')})\n"
            f"Descripción: {form_data.get('descripcion', '')}\n"
            f"Páginas/Funcionalidades: "
            f"{form_data.get('paginas_funcionalidades', 'A definir')}\n"
            f"Estilo: {form_data.get('estilo_colores', 'Moderno')}\n"
            f"Plazo: {form_data.get('plazo', 'normal')}\n"
            f"Presupuesto: {form_data.get('presupuesto', 'a_discutir')}\n\n"
            "El prompt debe:\n"
            "1. Especificar el stack (Next.js + Tailwind para webs)\n"
            "2. Listar todas las páginas y componentes a crear\n"
            "3. Describir funcionalidades específicas\n"
            "4. Incluir instrucciones de SEO, mobile-first, performance\n"
            "5. Terminar SIEMPRE con estas instrucciones exactas:\n"
            "   'Al terminar todo el trabajo:\n"
            "    1. Ejecutá: vercel --prod --yes y guardá la URL\n"
            f"    2. Creá docs/entrega_{nombre_safe}.md con:\n"
            "       - URL de producción de Vercel\n"
            "       - Lista de páginas creadas\n"
            "       - Tecnologías utilizadas\n"
            "       - Instrucciones para el cliente\n"
            "       - Instrucciones para actualizar contenido\n"
            "    3. Creá result.json en la carpeta de tarea con:\n"
            '       {"schema_version":"1.0","status":"exito",'
            '"vercel_url":"URL","summary":"resumen",'
            '"files_changed":[],"errors":[]}\'\n'
            "\n"
            "Escribí el prompt en español, directo y técnico."
        )

        brief = self.call_llm(prompt, max_tokens=2000, temperature=0.2)

        db.execute(
            """UPDATE dev_sessions
               SET brief_prompt = %s, updated_at = NOW()
               WHERE token = %s""",
            (brief, token),
        )
        self.write_event("done", f"Brief generado para {nombre}")
        self.log("brief_generated", {"token": token, "negocio": nombre})
        return brief

    # ── Python puro, sin LLM — async, no espera resultado ──
    def send_to_copilot(self, token: str) -> dict:
        """Envía brief al relay bridge. Retorna inmediatamente."""
        db = get_db()
        session = db.fetchone(
            "SELECT * FROM dev_sessions WHERE token = %s", (token,))
        if not session or not session.get("brief_prompt"):
            return {"error": "Brief no encontrado"}

        # Leer workspace_path de form_data
        raw = session.get("form_data")
        if isinstance(raw, dict):
            form_data_dict = raw
        elif isinstance(raw, str):
            form_data_dict = json.loads(raw)
        else:
            form_data_dict = {}
        workspace_path = form_data_dict.get(
            "workspace_path",
            "C:\\Users\\mauro\\OneDrive\\Desktop\\pulsarmoon-office",
        )

        self.write_event("working", "Enviando a Copilot...")
        try:
            resp = requests.post(
                f"{BRIDGE_URL}/execute",
                json={
                    "message": session["brief_prompt"],
                    "workspace": workspace_path,
                    "timeout": 600,
                },
                timeout=10,
            )
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Error enviando al bridge: %s", e)
            return {"error": str(e)}

        task_id = data.get("taskId", "")
        db.execute(
            """UPDATE dev_sessions
               SET copilot_task_id = %s, status = 'in_progress',
                   updated_at = NOW()
               WHERE token = %s""",
            (task_id, token),
        )
        self.write_event("working", f"Copilot trabajando: {task_id}")
        self.log("sent_to_copilot", {"token": token, "task_id": task_id})
        return {"task_id": task_id, "status": "in_progress"}

    # ── Python puro, sin LLM ──
    def check_completion(self, token: str) -> dict:
        """Consulta estado de la tarea en el bridge."""
        db = get_db()
        session = db.fetchone(
            "SELECT * FROM dev_sessions WHERE token = %s", (token,))
        if not session:
            return {"error": "Sesión no encontrada"}

        if session["status"] == "completed":
            return {
                "status": "done",
                "vercel_url": session.get("vercel_url", ""),
            }

        task_id = session.get("copilot_task_id")
        if not task_id:
            return {"status": session["status"]}

        try:
            resp = requests.get(
                f"{BRIDGE_URL}/status/{task_id}", timeout=10)
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Error consultando bridge: %s", e)
            return {"status": "pending"}

        if data.get("status") == "done":
            result = data.get("result", {})
            vercel_url = result.get("vercel_url", "")
            summary = result.get("summary", "")
            db.execute(
                """UPDATE dev_sessions
                   SET status = 'completed', vercel_url = %s,
                       updated_at = NOW()
                   WHERE token = %s""",
                (vercel_url, token),
            )
            self.write_event("done", f"Proyecto entregado: {vercel_url}")
            return {
                "status": "done",
                "vercel_url": vercel_url,
                "summary": summary,
            }

        return {"status": data.get("status", "pending")}


# Instancia global
_agent = DevAgent()
