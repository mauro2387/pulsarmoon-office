"""
Panel web del Email Prospector — Flask en puerto 8771.
Aprobación manual de cold emails antes de envío.
"""
import logging
import sys
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

DAILY_LIMIT = 60
SEND_DELAY_SECS = 30


def _agent():
    from agents.prospector.email_prospector import get_agent
    return get_agent()


def _paginate(query: str, params: tuple, page: int, per_page: int) -> dict:
    from db.database import get_db
    db = get_db()
    offset = (page - 1) * per_page
    rows = db.fetchall(query + " LIMIT %s OFFSET %s",
                        params + (per_page, offset))
    return {"page": page, "per_page": per_page, "items": rows}


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "agent": "email-prospector-01",
                    "port": 8771})


@app.route("/leads/pending")
def leads_pending():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    return jsonify(_paginate(
        """SELECT * FROM leads
           WHERE status = 'pending_approval' AND has_email = TRUE
           ORDER BY score DESC, created_at DESC""",
        (), page, per_page,
    ))


@app.route("/leads/no-email")
def leads_no_email():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    return jsonify(_paginate(
        """SELECT id, business_name, phone, city, country, sector,
                  score, notes, site_issues, created_at
             FROM leads
            WHERE has_email = FALSE
              AND status IN ('pending_approval', 'new')
            ORDER BY score DESC, created_at DESC""",
        (), page, per_page,
    ))


@app.route("/leads/sent")
def leads_sent():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    return jsonify(_paginate(
        """SELECT * FROM leads
           WHERE email_sent = TRUE
           ORDER BY email_sent_at DESC""",
        (), page, per_page,
    ))


@app.route("/leads/<int:lead_id>/approve", methods=["POST"])
def approve_lead(lead_id: int):
    try:
        ok = _agent().send_email(lead_id)
        if not ok:
            return jsonify({"ok": False,
                             "error": "Envío falló (revisar logs / límite diario)"}), 400
        return jsonify({"ok": True})
    except Exception as e:
        logger.exception("Error aprobando lead %s", lead_id)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/leads/<int:lead_id>/reject", methods=["POST"])
def reject_lead(lead_id: int):
    from db.leads import update_lead_status
    if not update_lead_status(lead_id, "lost"):
        return jsonify({"ok": False, "error": "No se pudo actualizar"}), 400
    return jsonify({"ok": True})


# ── Aprobar todos (con delay y límite diario) ─────────────────────────────

_approve_all_lock = threading.Lock()
_approve_all_state: dict = {"running": False, "sent": 0, "skipped": 0,
                              "started_at": None}


def _approve_all_worker(lead_ids: list[int]) -> None:
    global _approve_all_state
    agent = _agent()
    sent = skipped = 0
    try:
        for lid in lead_ids:
            if agent.emails_sent_today() >= DAILY_LIMIT:
                logger.info("Límite diario alcanzado, frenando approve-all")
                break
            try:
                ok = agent.send_email(lid)
                if ok:
                    sent += 1
                    _approve_all_state["sent"] = sent
                else:
                    skipped += 1
                    _approve_all_state["skipped"] = skipped
            except Exception as e:
                logger.error("Error en approve-all lead %s: %s", lid, e)
                skipped += 1
            time.sleep(SEND_DELAY_SECS)
    finally:
        _approve_all_state["running"] = False
        logger.info("approve-all terminado: sent=%d skipped=%d",
                    sent, skipped)


@app.route("/leads/approve-all", methods=["POST"])
def approve_all():
    global _approve_all_state
    with _approve_all_lock:
        if _approve_all_state["running"]:
            return jsonify({"ok": False,
                             "error": "Ya hay un envío masivo en curso",
                             "state": _approve_all_state}), 409

        from db.database import get_db
        rows = get_db().fetchall(
            """SELECT id FROM leads
               WHERE status = 'pending_approval' AND has_email = TRUE
                 AND email_sent = FALSE
               ORDER BY score DESC"""
        )
        lead_ids = [r["id"] for r in rows]

        sent_today = _agent().emails_sent_today()
        remaining = max(0, DAILY_LIMIT - sent_today)
        lead_ids = lead_ids[:remaining]

        _approve_all_state = {
            "running": True, "sent": 0, "skipped": 0,
            "started_at": time.time(), "queued": len(lead_ids),
        }
        threading.Thread(target=_approve_all_worker,
                         args=(lead_ids,), daemon=True).start()

    return jsonify({"ok": True, "queued": len(lead_ids),
                     "remaining_today": remaining})


@app.route("/leads/approve-all/status")
def approve_all_status():
    return jsonify(_approve_all_state)


@app.route("/stats")
def stats():
    from db.database import get_db
    db = get_db()
    try:
        leads_today = db.fetchone(
            "SELECT COUNT(*) AS c FROM leads "
            "WHERE created_at::date = CURRENT_DATE"
        )["c"]
        leads_total = db.fetchone(
            "SELECT COUNT(*) AS c FROM leads"
        )["c"]
        emails_today = db.fetchone(
            "SELECT COUNT(*) AS c FROM leads "
            "WHERE email_sent = TRUE AND email_sent_at::date = CURRENT_DATE"
        )["c"]
        emails_total = db.fetchone(
            "SELECT COUNT(*) AS c FROM leads WHERE email_sent = TRUE"
        )["c"]
        pending = db.fetchone(
            "SELECT COUNT(*) AS c FROM leads "
            "WHERE status = 'pending_approval' AND has_email = TRUE"
        )["c"]
        no_email = db.fetchone(
            "SELECT COUNT(*) AS c FROM leads WHERE has_email = FALSE"
        )["c"]
        top_cities = db.fetchall(
            """SELECT city, COUNT(*) AS count FROM leads
               WHERE city IS NOT NULL
               GROUP BY city ORDER BY count DESC LIMIT 5"""
        )
        top_niches = db.fetchall(
            """SELECT sector AS niche, COUNT(*) AS count FROM leads
               WHERE sector IS NOT NULL
               GROUP BY sector ORDER BY count DESC LIMIT 5"""
        )
        return jsonify({
            "leads_today": leads_today, "leads_total": leads_total,
            "emails_sent_today": emails_today,
            "emails_sent_total": emails_total,
            "pending_approval": pending, "no_email_count": no_email,
            "top_cities": top_cities, "top_niches": top_niches,
            "daily_limit": DAILY_LIMIT,
        })
    except Exception as e:
        logger.exception("Error en /stats")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    app.run(host="0.0.0.0", port=8771)
