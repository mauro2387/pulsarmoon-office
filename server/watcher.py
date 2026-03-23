"""
Watchdog de archivos de eventos de agentes.
Detecta cambios en agents/events/ y procesa los JSON de estado.
"""
import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Callable, Coroutine, Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from server import db

logger = logging.getLogger(__name__)

# Campos obligatorios en cada evento
REQUIRED_FIELDS = {"agent_id", "agent_name", "department", "status", "timestamp"}

# Estados válidos
VALID_STATUSES = {"idle", "working", "waiting", "error", "done"}


class AgentEventHandler(FileSystemEventHandler):
    """
    Handler de watchdog que procesa archivos JSON de eventos de agentes.
    Detecta creaciones y modificaciones — no eliminaciones.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        on_agent_update: Callable[[dict], Coroutine[Any, Any, None]],
    ) -> None:
        super().__init__()
        self._loop = loop
        self._on_agent_update = on_agent_update
        # Debounce: evitar procesar el mismo archivo múltiples veces seguidas
        self._last_processed: dict[str, float] = {}
        self._debounce_seconds = 0.1

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._process(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._process(event.src_path)

    def _process(self, path: str) -> None:
        """Valida el archivo y despacha el evento al loop asyncio."""
        # Solo archivos .json (ignorar .tmp)
        if not path.endswith(".json"):
            return

        # Debounce simple por archivo
        now = time.monotonic()
        last = self._last_processed.get(path, 0)
        if now - last < self._debounce_seconds:
            return
        self._last_processed[path] = now

        # Leer y validar el JSON
        event_data = _read_event_file(path)
        if event_data is None:
            return

        # Persistir en SQLite
        try:
            db.upsert_agent(event_data)
            db.log_event(event_data)
        except Exception as e:
            logger.error(f"Error al persistir evento de {path}: {e}")
            return

        # Despachar al loop asyncio para broadcast WebSocket
        asyncio.run_coroutine_threadsafe(
            self._on_agent_update(event_data),
            self._loop,
        )


def _read_event_file(path: str) -> dict | None:
    """
    Lee y valida un archivo de evento.
    Devuelve el dict si es válido, None si hay cualquier error.
    """
    # Reintentar la lectura hasta 3 veces (escritura atómica puede causar vacíos)
    for attempt in range(3):
        try:
            content = Path(path).read_text(encoding="utf-8").strip()
            if not content:
                if attempt < 2:
                    time.sleep(0.05)
                    continue
                return None

            data = json.loads(content)

            # Validar campos obligatorios
            missing = REQUIRED_FIELDS - data.keys()
            if missing:
                logger.warning(f"Evento inválido en {path} — faltan campos: {missing}")
                return None

            # Validar status
            if data["status"] not in VALID_STATUSES:
                logger.warning(
                    f"Status inválido '{data['status']}' en {path} — "
                    f"valores válidos: {VALID_STATUSES}"
                )
                return None

            return data

        except json.JSONDecodeError as e:
            if attempt < 2:
                time.sleep(0.05)
                continue
            logger.error(f"JSON inválido en {path}: {e}")
            return None
        except OSError as e:
            logger.error(f"No se pudo leer {path}: {e}")
            return None

    return None


async def run(
    events_dir: str,
    loop: asyncio.AbstractEventLoop,
    on_agent_update: Callable[[dict], Coroutine[Any, Any, None]],
) -> None:
    """
    Inicia el watcher de archivos de eventos.
    Corre indefinidamente como tarea asyncio.
    """
    os.makedirs(events_dir, exist_ok=True)

    handler = AgentEventHandler(loop, on_agent_update)
    observer = Observer()
    observer.schedule(handler, events_dir, recursive=False)
    observer.start()
    logger.info(f"Watcher activo en: {events_dir}")

    try:
        # Cargar archivos existentes al iniciar (agentes ya activos)
        await _load_existing_events(events_dir, on_agent_update)

        # Mantener el watcher corriendo
        while True:
            await asyncio.sleep(1)
            if not observer.is_alive():
                logger.error("Observer de watchdog murió — reiniciando")
                observer.start()

    except asyncio.CancelledError:
        logger.info("Watcher detenido")
    finally:
        observer.stop()
        observer.join()


async def _load_existing_events(
    events_dir: str,
    on_agent_update: Callable[[dict], Coroutine[Any, Any, None]],
) -> None:
    """
    Procesa todos los archivos .json existentes en events_dir al arrancar.
    Esto restaura el estado de agentes de sesiones anteriores.
    """
    events_path = Path(events_dir)
    json_files = list(events_path.glob("*.json"))

    if not json_files:
        return

    logger.info(f"Cargando {len(json_files)} eventos existentes al iniciar")
    for filepath in json_files:
        event_data = _read_event_file(str(filepath))
        if event_data is None:
            continue
        try:
            db.upsert_agent(event_data)
            # No loguear eventos viejos al event_log para no inflar el historial
        except Exception as e:
            logger.error(f"Error cargando evento existente {filepath}: {e}")

    # Notificar a clientes conectados (si los hay) del estado inicial
    agents = db.get_all_agents()
    logger.info(f"Estado restaurado: {len(agents)} agentes cargados")
