"""
WebSocket server asyncio para PulsarMoon Office.
Emite estado inicial y actualizaciones en tiempo real a todos los clientes.
"""
import asyncio
import json
import logging
import time
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol
from websockets.http11 import Request, Response
from websockets.datastructures import Headers

from server import db

logger = logging.getLogger(__name__)

# Set de conexiones activas
_clients: set[WebSocketServerProtocol] = set()

# Config inyectada desde main.py
_config: dict = {}


def setup(config: dict) -> None:
    """Recibe la configuración del servidor."""
    global _config
    _config = config


# ─── Broadcast ─────────────────────────────────────────────────────────────────

async def broadcast(message: dict) -> None:
    """Envía un mensaje JSON a todos los clientes conectados."""
    if not _clients:
        return
    payload = json.dumps(message, ensure_ascii=False)
    # Copiar el set para evitar modificaciones durante iteración
    dead: set[WebSocketServerProtocol] = set()
    for client in _clients.copy():
        try:
            await client.send(payload)
        except websockets.exceptions.ConnectionClosed:
            dead.add(client)
        except Exception as e:
            logger.error(f"Error enviando a cliente: {e}")
            dead.add(client)
    for client in dead:
        _clients.discard(client)


async def broadcast_agent_update(agent: dict) -> None:
    """Emite una actualización de agente a todos los clientes."""
    await broadcast({
        "type": "agent_update",
        "agent": agent,
        "timestamp": int(time.time()),
    })


async def broadcast_agent_removed(agent_id: str) -> None:
    """Emite la eliminación de un agente a todos los clientes."""
    await broadcast({
        "type": "agent_removed",
        "agent_id": agent_id,
        "timestamp": int(time.time()),
    })


# ─── Handler de conexión ───────────────────────────────────────────────────────

async def _handle_connection(websocket: WebSocketServerProtocol) -> None:
    """Maneja una nueva conexión WebSocket."""
    client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    logger.info(f"Cliente conectado: {client_info}")
    _clients.add(websocket)

    try:
        # Enviar estado inicial completo
        await _send_initial_state(websocket)

        # Escuchar mensajes del cliente
        async for raw in websocket:
            await _handle_client_message(websocket, raw)

    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"Cliente desconectado normalmente: {client_info}")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"Cliente desconectado con error: {client_info} — {e}")
    except Exception as e:
        logger.error(f"Error inesperado con cliente {client_info}: {e}")
    finally:
        _clients.discard(websocket)
        logger.info(f"Clientes activos: {len(_clients)}")


async def _send_initial_state(websocket: WebSocketServerProtocol) -> None:
    """Envía el estado completo de todos los agentes al cliente recién conectado."""
    agents = db.get_all_agents()
    message = {
        "type": "initial_state",
        "agents": agents,
        "timestamp": int(time.time()),
    }
    await websocket.send(json.dumps(message, ensure_ascii=False))
    logger.info(f"Estado inicial enviado: {len(agents)} agentes")


async def _handle_client_message(
    websocket: WebSocketServerProtocol, raw: str
) -> None:
    """Procesa un mensaje recibido del cliente."""
    try:
        message = json.loads(raw)
        msg_type = message.get("type")

        if msg_type == "pong":
            # Respuesta al ping — ignorar silenciosamente
            pass
        elif msg_type == "request_state":
            # Cliente solicita estado completo (reconexión)
            await _send_initial_state(websocket)
        else:
            logger.warning(f"Mensaje desconocido del cliente: {msg_type}")

    except json.JSONDecodeError:
        logger.warning(f"Mensaje no-JSON recibido del cliente: {raw[:100]}")
    except Exception as e:
        logger.error(f"Error procesando mensaje del cliente: {e}")


# ─── Ping periódico ─────────────────────────────────────────────────────────────

async def _ping_loop(interval: int) -> None:
    """Envía ping a todos los clientes cada `interval` segundos."""
    while True:
        await asyncio.sleep(interval)
        if _clients:
            await broadcast({
                "type": "ping",
                "timestamp": int(time.time()),
            })


# ─── HTTP handler para servir API desde el mismo puerto ─────────────────────

def _json_response(status: int, body: bytes) -> Response:
    """Construye una Response HTTP con headers CORS + JSON."""
    hdrs = Headers({
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
    })
    phrase = "OK" if status == 200 else "Not Found"
    return Response(status, phrase, hdrs, body)


async def _http_handler(connection, request: Request) -> Optional[Response]:
    """Intercepta requests HTTP normales (no WS upgrade) para servir API REST."""
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return None  # dejar pasar al handler WS
    path = request.path
    if path == "/health":
        body = json.dumps({"status": "ok", "agents": len(db.get_all_agents())})
        return _json_response(200, body.encode())
    if path == "/agents":
        agents = db.get_all_agents()
        body = json.dumps({"agents": agents, "count": len(agents)})
        return _json_response(200, body.encode())
    if path.startswith("/agents/"):
        aid = path.split("/agents/", 1)[1].split("/")[0]
        agent = db.get_agent(aid)
        if agent:
            return _json_response(200, json.dumps(agent).encode())
        return _json_response(404, b'{"error":"not found"}')
    return None


# ─── Entry point ───────────────────────────────────────────────────────────────

async def run(host: str, port: int, ping_interval: int) -> None:
    """Inicia el WebSocket server y lo mantiene corriendo."""
    logger.info(f"WebSocket server escuchando en ws://{host}:{port}")
    ping_task = asyncio.create_task(_ping_loop(ping_interval))

    try:
        async with websockets.serve(
            _handle_connection,
            host,
            port,
            compression=None,
            process_request=_http_handler,
        ):
            logger.info("WebSocket server listo para recibir conexiones")
            await asyncio.Future()  # correr indefinidamente
    finally:
        ping_task.cancel()


def get_client_count() -> int:
    """Devuelve el número de clientes conectados actualmente."""
    return len(_clients)
