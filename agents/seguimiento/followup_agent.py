"""
Agente de Seguimiento de PulsarMoon.
Detecta leads sin respuesta, genera follow-ups con templates Python,
y los deja en cola para aprobación humana. CERO LLM, CERO envío automático.
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.base_agent import BaseAgent
from agents.templates.whatsapp import FOLLOW_UP_1, FOLLOW_UP_2
from db.database import get_db

logger = logging.getLogger(__name__)


class FollowupAgent(BaseAgent):
    """Detecta leads sin respuesta y genera follow-ups para aprobación."""

    def __init__(self):
        super().__init__(
            agent_id="followup-01",
            agent_name="Seguimiento",
            department="oportunidades",
            model="haiku",
            company_id="pulsarmoon",
        )

    # ── SQL puro, sin LLM ──
    def check_pending_leads(self) -> list[dict]:
        """Busca leads contactados sin respuesta que necesitan follow-up."""
        db = get_db()
        return db.fetchall("""
            SELECT * FROM leads
            WHERE status = 'contacted'
              AND phone IS NOT NULL
              AND (
                (followup_count = 0
                 AND updated_at < NOW() - INTERVAL '3 days')
                OR
                (followup_count = 1
                 AND updated_at < NOW() - INTERVAL '7 days')
              )
              AND followup_count < 2
            ORDER BY updated_at ASC
        """)

    # ── Templates Python, sin LLM ──
    def generate_followup_message(self, lead: dict,
                                  followup_number: int) -> str:
        """Genera mensaje de follow-up desde template."""
        template = FOLLOW_UP_1 if followup_number == 1 else FOLLOW_UP_2
        return self.format_message(
            template,
            nombre=lead.get("business_name", ""),
            negocio=lead.get("business_name", ""),
        )

    def create_followup_batch(self) -> dict:
        """Genera follow-ups pendientes de aprobación. No envía nada."""
        self.write_event("working", "Detectando leads sin respuesta...")
        leads = self.check_pending_leads()

        if not leads:
            self.write_event("idle", "Sin leads pendientes de follow-up")
            self.log("followups_generated", {"count": 0})
            return {"pending": 0, "leads": []}

        db = get_db()
        created = []
        for lead in leads:
            fu_number = lead.get("followup_count", 0) + 1
            message = self.generate_followup_message(lead, fu_number)

            db.execute(
                """INSERT INTO followup_queue
                   (lead_id, phone, business_name, message, followup_number)
                   VALUES (%s, %s, %s, %s, %s)""",
                (lead["id"], lead["phone"], lead["business_name"],
                 message, fu_number),
            )
            created.append({
                "lead_id": lead["id"],
                "business_name": lead["business_name"],
                "followup_number": fu_number,
            })

        self.write_event(
            "waiting",
            f"{len(created)} follow-ups esperando aprobación",
        )
        self.log("followups_generated", {"count": len(created)})
        return {"pending": len(created), "leads": created}

    def send_approved_followup(self, followup_id: int) -> dict:
        """Envía un follow-up previamente aprobado por Mauro."""
        db = get_db()
        fu = db.fetchone(
            "SELECT * FROM followup_queue WHERE id = %s", (followup_id,))
        if not fu:
            return {"error": "Follow-up no encontrado"}

        # Enviar WhatsApp
        wa_sent = self.send_whatsapp(fu["phone"], fu["message"])

        # Actualizar lead
        db.execute(
            """UPDATE leads
               SET followup_count = followup_count + 1,
                   updated_at = NOW()
               WHERE id = %s""",
            (fu["lead_id"],),
        )

        # Si ya llegó a 2 follow-ups → cold
        lead = db.fetchone(
            "SELECT followup_count FROM leads WHERE id = %s",
            (fu["lead_id"],),
        )
        if lead and lead["followup_count"] >= 2:
            db.execute(
                "UPDATE leads SET status = 'cold' WHERE id = %s",
                (fu["lead_id"],),
            )

        # Marcar follow-up como enviado
        db.execute(
            """UPDATE followup_queue
               SET status = 'sent', sent_at = NOW()
               WHERE id = %s""",
            (followup_id,),
        )

        self.log("followup_sent", {
            "lead": fu["business_name"],
            "followup_number": fu["followup_number"],
            "whatsapp_sent": wa_sent,
        })
        return {"ok": True, "whatsapp_sent": wa_sent}


# Instancia global
_agent = FollowupAgent()
