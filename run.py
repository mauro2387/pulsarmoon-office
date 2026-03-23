"""
Entry point de PulsarMoon Office Backend.
Uso: python run.py
"""
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path


def setup_logging(logs_dir: str) -> None:
    """Configura logging estructurado a consola y archivo."""
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(logs_dir) / "office.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Handler de archivo
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Silenciar logs verbosos de librerías externas
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("watchdog").setLevel(logging.WARNING)


def load_config() -> dict:
    """Carga config.json desde la raíz del proyecto."""
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print(f"ERROR: No se encontró config.json en {config_path}")
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    config = load_config()
    setup_logging(config["paths"]["logs_dir"])

    logger = logging.getLogger("run")
    logger.info("=" * 60)
    logger.info("  PulsarMoon Office — Backend v1.0")
    logger.info("=" * 60)

    # Importar DESPUÉS de configurar logging
    from server.main import run

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Manejar Ctrl+C limpiamente
    def _shutdown(signum: int, frame: object) -> None:
        logger.info("Señal de cierre recibida — deteniendo servidor...")
        for task in asyncio.all_tasks(loop):
            task.cancel()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(run(config))
    except KeyboardInterrupt:
        logger.info("Interrupción por teclado — cerrando")
    finally:
        loop.close()
        logger.info("Servidor cerrado correctamente")


if __name__ == "__main__":
    main()
