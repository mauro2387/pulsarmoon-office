"""
Panel web del Prospector — Flask en puerto 8768.
Gestión de leads: listar, aprobar, rechazar, enviar WhatsApp.
"""
import logging
import sys
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Path para imports
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


@app.route("/health")
def health():
    """Estado del agente prospector."""
    return jsonify({"status": "ok", "agent": "prospector-01"})


@app.route("/leads")
def list_leads():
    """Lista leads con status='new' (o filtro via ?status=)."""
    from db.leads import get_leads_by_status, get_all_leads
    status = request.args.get("status")
    if status:
        leads = get_leads_by_status(status)
    else:
        leads = get_all_leads()
    return jsonify(leads)


@app.route("/leads/<int:lead_id>")
def get_lead_detail(lead_id: int):
    """Detalle de un lead con su mensaje generado."""
    from db.leads import get_lead
    lead = get_lead(lead_id)
    if not lead:
        return jsonify({"error": "Lead no encontrado"}), 404
    return jsonify(lead)


@app.route("/leads/<int:lead_id>/approve", methods=["POST"])
def approve_lead(lead_id: int):
    """Aprueba lead y envía WhatsApp si tiene teléfono."""
    from db.leads import get_lead, update_lead_status
    lead = get_lead(lead_id)
    if not lead:
        return jsonify({"error": "Lead no encontrado"}), 404

    update_lead_status(lead_id, "contacted")

    # Enviar WhatsApp si hay teléfono y mensaje
    if lead.get("phone") and lead.get("notes"):
        from agents.prospector.prospector_agent import _agent
        sent = _agent.send_whatsapp(lead["phone"], lead["notes"])
        return jsonify({"ok": True, "whatsapp_sent": sent})

    return jsonify({"ok": True, "whatsapp_sent": False})


@app.route("/leads/<int:lead_id>/reject", methods=["POST"])
def reject_lead(lead_id: int):
    """Rechaza un lead."""
    from db.leads import update_lead_status
    ok = update_lead_status(lead_id, "lost")
    if not ok:
        return jsonify({"error": "Error actualizando lead"}), 400
    return jsonify({"ok": True})


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    app.run(host="0.0.0.0", port=8768)
