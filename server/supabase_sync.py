"""
Sincronización asíncrona del event_log local a Supabase.
Solo activo si supabase.enabled=true en config.json.
"""
import asyncio
import logging
import os
import time

logger = logging.getLogger(__name__)


async def run_sync(config: dict) -> None:
    """
    Sincroniza event_log a Supabase periódicamente.
    Si supabase no está habilitado, no hace nada.
    """
    if not config.get("enabled", False):
        logger.info("Sync a Supabase deshabilitado en config.json")
        return

    url = config.get("url") or os.environ.get("SUPABASE_URL", "")
    key = config.get("key") or os.environ.get("SUPABASE_KEY", "")

    if not url or not key:
        logger.warning(
            "Supabase habilitado en config pero sin URL/KEY — sync deshabilitado"
        )
        return

    interval = config.get("sync_interval_seconds", 60)
    logger.info(f"Sync a Supabase habilitado — intervalo: {interval}s")

    try:
        from supabase import create_client  # type: ignore
        client = create_client(url, key)
    except ImportError:
        logger.error("Paquete 'supabase' no instalado — sync deshabilitado")
        return
    except Exception as e:
        logger.error(f"Error inicializando cliente Supabase: {e}")
        return

    last_synced_id = 0

    while True:
        try:
            await asyncio.sleep(interval)
            last_synced_id = await _sync_batch(client, last_synced_id)
        except asyncio.CancelledError:
            logger.info("Sync a Supabase detenido")
            return
        except Exception as e:
            logger.error(f"Error en ciclo de sync a Supabase: {e}")


async def _sync_batch(client: object, last_id: int) -> int:
    """
    Sincroniza el lote de eventos nuevos desde last_id.
    Devuelve el último ID sincronizado.
    """
    from server import db

    # Obtener eventos más recientes que no hemos enviado
    # (simplificación: sincronizamos los últimos 100)
    events = db.get_recent_events(100)
    if not events:
        return last_id

    # Filtrar solo los que tienen id > last_synced
    new_events = [e for e in events if e.get("id", 0) > last_id]
    if not new_events:
        return last_id

    try:
        # Preparar rows para Supabase (snake_case, tipos compatibles)
        rows = [
            {
                "agent_id":  e["agent_id"],
                "status":    e["status"],
                "task":      e.get("task", ""),
                "timestamp": e["timestamp"],
                "raw_event": e["raw_event"],
            }
            for e in new_events
        ]

        # Insertar en lote
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.table("event_log").insert(rows).execute()
        )

        max_id = max(e.get("id", 0) for e in new_events)
        logger.info(f"Supabase: {len(rows)} eventos sincronizados (último ID: {max_id})")
        return max_id

    except Exception as e:
        logger.error(f"Error enviando batch a Supabase: {e}")
        return last_id
