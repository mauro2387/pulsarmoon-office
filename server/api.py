"""
Flask REST API para PulsarMoon Office.
Expone endpoints para consultar el estado de los agentes.
"""
import logging
import time
from typing import Any

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


# ─── Iniciar servidor ──────────────────────────────────────────────────────────

def run(host: str, port: int) -> None:
    """Inicia el servidor Flask en modo producción (sin debug)."""
    logger.info(f"Flask API escuchando en http://{host}:{port}")
    # Usar threaded=True para manejar requests concurrentes
    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
