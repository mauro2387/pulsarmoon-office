"""
Flask REST API para PulsarMoon Office.
Expone endpoints para consultar el estado de los agentes.
"""
import logging
import threading
import time
from typing import Any

import requests as req
from flask import Flask, jsonify, request
from flask_cors import CORS

from server import db

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins="*")

# Timestamp de inicio del servidor
_start_time = int(time.time())


def _error(message: str, code: int = 400) -> tuple[Any, int]:
    """Respuesta de error estandarizada."""
    return jsonify({"error": message}), code


# ─── Health ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health() -> Any:
    """Endpoint de salud — verifica que el servidor está corriendo."""
    agents = db.get_all_agents()
    active = sum(1 for a in agents if a["status"] == "working")
    return jsonify({
        "status": "ok",
        "uptime_seconds": int(time.time()) - _start_time,
        "agents_total": len(agents),
        "agents_active": active,
        "timestamp": int(time.time()),
    })


# ─── Agentes ───────────────────────────────────────────────────────────────────

@app.route("/agents", methods=["GET"])
def list_agents() -> Any:
    """Devuelve todos los agentes con su estado actual."""
    try:
        agents = db.get_all_agents()
        return jsonify({
            "agents": agents,
            "count": len(agents),
            "timestamp": int(time.time()),
        })
    except Exception as e:
        logger.error(f"Error al obtener agentes: {e}")
        return _error("Error interno al obtener agentes", 500)


@app.route("/agents/<string:agent_id>", methods=["GET"])
def get_agent(agent_id: str) -> Any:
    """Devuelve los datos de un agente específico."""
    try:
        agent = db.get_agent(agent_id)
        if agent is None:
            return _error(f"Agente '{agent_id}' no encontrado", 404)
        return jsonify(agent)
    except Exception as e:
        logger.error(f"Error al obtener agente {agent_id}: {e}")
        return _error("Error interno al obtener el agente", 500)


@app.route("/agents/<string:agent_id>/events", methods=["GET"])
def get_agent_events(agent_id: str) -> Any:
    """Devuelve el log de eventos de un agente específico."""
    try:
        limit = min(int(request.args.get("limit", 50)), 500)
        agent = db.get_agent(agent_id)
        if agent is None:
            return _error(f"Agente '{agent_id}' no encontrado", 404)
        events = db.get_agent_events(agent_id, limit)
        return jsonify({
            "agent_id": agent_id,
            "events": events,
            "count": len(events),
        })
    except ValueError:
        return _error("El parámetro 'limit' debe ser un entero válido")
    except Exception as e:
        logger.error(f"Error al obtener eventos de {agent_id}: {e}")
        return _error("Error interno al obtener eventos", 500)


# ─── Eventos recientes ─────────────────────────────────────────────────────────

@app.route("/events", methods=["GET"])
def list_events() -> Any:
    """Devuelve los eventos más recientes de todos los agentes."""
    try:
        limit = min(int(request.args.get("limit", 100)), 1000)
        events = db.get_recent_events(limit)
        return jsonify({
            "events": events,
            "count": len(events),
            "timestamp": int(time.time()),
        })
    except ValueError:
        return _error("El parámetro 'limit' debe ser un entero válido")
    except Exception as e:
        logger.error(f"Error al obtener eventos: {e}")
        return _error("Error interno al obtener eventos", 500)


# ─── Desarrollo ────────────────────────────────────────────────────────────────

@app.route("/dev/session", methods=["POST"])
def dev_create_session() -> Any:
    """Crea sesión de desarrollo con token único."""
    from agents.desarrollo.dev_agent import _agent
    data = request.get_json()
    if not data or not data.get("phone"):
        return _error("phone requerido")
    result = _agent.create_session(data["phone"])
    return jsonify(result)


@app.route("/dev/brief", methods=["POST"])
def dev_submit_brief() -> Any:
    """Recibe formulario, genera brief, envía a Copilot."""
    from agents.desarrollo.dev_agent import _agent
    from db.database import get_db
    data = request.get_json()
    if not data or not data.get("token"):
        return _error("token requerido")

    token = data["token"]
    db = get_db()
    session = db.fetchone(
        "SELECT * FROM dev_sessions WHERE token = %s", (token,))
    if not session:
        return _error("Token inválido", 404)
    if session["status"] != "pending":
        return _error("Sesión ya procesada")

    # Verificar expiración (24hs)
    from datetime import datetime, timedelta, timezone
    created = session["created_at"]
    if hasattr(created, 'tzinfo') and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if now - created > timedelta(hours=24):
        return _error("Token expirado")

    form_data = {k: v for k, v in data.items() if k != "token"}
    brief = _agent.process_form(token, form_data)
    result = _agent.send_to_copilot(token)

    # Leer workspace_path de form_data guardado por process_form
    updated_session = db.fetchone(
        "SELECT form_data FROM dev_sessions WHERE token = %s", (token,))
    _fd = updated_session.get("form_data", {}) if updated_session else {}
    if isinstance(_fd, str):
        import json as _json
        _fd = _json.loads(_fd)
    workspace_path = _fd.get("workspace_path", "")

    # Notificar a n8n (fire and forget)
    def _notify_n8n(tkn, phone, brief_text, nombre, ws_path):
        try:
            req.post(
                "https://n8n.vydre.me/webhook/dev-brief-received",
                json={"token": tkn, "phone": phone,
                      "brief_prompt": brief_text,
                      "nombre_negocio": nombre,
                      "workspace_path": ws_path},
                timeout=5,
            )
        except Exception:
            pass

    threading.Thread(
        target=_notify_n8n,
        args=(token, session["phone"], brief,
              data.get("nombre_negocio", ""), workspace_path),
        daemon=True,
    ).start()

    return jsonify({"status": "ok", "message": "Brief enviado a Copilot",
                     **result})


@app.route("/dev/status/<string:token>", methods=["GET"])
def dev_check_status(token: str) -> Any:
    """Consulta estado de una sesión de desarrollo."""
    from agents.desarrollo.dev_agent import _agent
    result = _agent.check_completion(token)
    return jsonify(result)


@app.route("/dev/session/complete", methods=["POST"])
def dev_complete_session() -> Any:
    """n8n llama esto cuando Copilot terminó el proyecto."""
    from agents.desarrollo.dev_agent import _agent
    from db.database import get_db
    data = request.get_json()
    if not data or not data.get("token"):
        return _error("token requerido")

    token = data["token"]
    vercel_url = data.get("vercel_url", "")

    db = get_db()
    db.execute(
        """UPDATE dev_sessions
           SET status = 'completed', vercel_url = %s, updated_at = NOW()
           WHERE token = %s""",
        (vercel_url, token),
    )
    _agent.log("session_completed", {"token": token, "vercel_url": vercel_url})
    return jsonify({"status": "ok", "token": token, "vercel_url": vercel_url})


# ─── Iniciar servidor ──────────────────────────────────────────────────────────

def run(host: str, port: int) -> None:
    """Inicia el servidor Flask en modo producción (sin debug)."""
    logger.info(f"Flask API escuchando en http://{host}:{port}")
    # Usar threaded=True para manejar requests concurrentes
    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
