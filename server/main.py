"""
Orquestador principal de PulsarMoon Office Backend.
Levanta todos los servicios en un único event loop asyncio.
"""
import asyncio
import logging
import threading
from typing import Any

from server import db, ws_server, watcher, demo_agents, supabase_sync
from server.api import run as run_flask


logger = logging.getLogger(__name__)


async def _on_agent_update(event: dict) -> None:
    """
    Callback invocado por el watcher cuando detecta un cambio de agente.
    Emite la actualización a todos los clientes WebSocket conectados.
    """
    await ws_server.broadcast_agent_update(event)


async def run(config: dict) -> None:
    """
    Inicia todos los servicios del backend de forma concurrente.
    El servidor Flask corre en un thread separado (es WSGI, no asyncio).
    """
    server_cfg  = config["server"]
    paths_cfg   = config["paths"]
    demo_cfg    = config["demo"]
    supa_cfg    = config["supabase"]

    # Inicializar base de datos
    db.setup(paths_cfg["db_path"])
    logger.info("Base de datos lista")

    # Configurar WS server
    ws_server.setup(config)

    # Iniciar Flask en thread separado (no bloquea el event loop)
    flask_thread = threading.Thread(
        target=run_flask,
        args=(server_cfg["host"], server_cfg["api_port"]),
        daemon=True,
        name="flask-api",
    )
    flask_thread.start()
    logger.info(f"Flask API iniciado en thread: {flask_thread.name}")

    # Construir las tareas asyncio
    loop = asyncio.get_running_loop()

    tasks: list[asyncio.Task[Any]] = [
        # WebSocket server principal
        asyncio.create_task(
            ws_server.run(
                host=server_cfg["host"],
                port=server_cfg["ws_port"],
                ping_interval=server_cfg["ws_ping_interval"],
            ),
            name="ws-server",
        ),
        # Watcher de archivos de eventos
        asyncio.create_task(
            watcher.run(
                events_dir=paths_cfg["events_dir"],
                loop=loop,
                on_agent_update=_on_agent_update,
            ),
            name="watcher",
        ),
    ]

    # Demo agents — solo si está habilitado en config
    if demo_cfg.get("enabled", True):
        tasks.append(
            asyncio.create_task(
                demo_agents.run_demo_agents(paths_cfg["events_dir"]),
                name="demo-agents",
            )
        )
        logger.info("Demo agents habilitados")
    else:
        logger.info("Demo agents deshabilitados en config")

    # Sync a Supabase — solo si está habilitado
    tasks.append(
        asyncio.create_task(
            supabase_sync.run_sync(supa_cfg),
            name="supabase-sync",
        )
    )

    logger.info(
        f"PulsarMoon Office Backend arrancando — "
        f"WS: ws://{server_cfg['host']}:{server_cfg['ws_port']} — "
        f"API: http://{server_cfg['host']}:{server_cfg['api_port']}"
    )

    # Esperar hasta que alguna tarea falle o el proceso sea interrumpido
    try:
        done, pending = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_EXCEPTION
        )

        # Si alguna tarea falló, loguear el error
        for task in done:
            exc = task.exception()
            if exc is not None:
                logger.error(f"Tarea '{task.get_name()}' falló con: {exc}", exc_info=exc)

    except asyncio.CancelledError:
        logger.info("Servidor detenido por señal de cancelación")
    finally:
        # Cancelar todas las tareas pendientes limpiamente
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Todos los servicios detenidos correctamente")
