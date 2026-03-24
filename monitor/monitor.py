"""
PulsarMoon Infrastructure Monitor — corre en server-monitor (192.168.1.10).
Chequea internet, servidores y servicios cada 60s.
Alerta por WhatsApp cuando algo cae o se recupera.
Solo stdlib, cero dependencias.
"""
import json
import logging
import socket
import subprocess
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

# ─── Config ───────────────────────────────────────────────
CHECK_INTERVAL = 60
ALERT_PHONE = "59891722750"
WA_URL = "http://192.168.1.11:3000/send"
LOG_FILE = "/var/log/pulsarmoon-monitor.log"

PING_TARGETS = {
    "internet": "8.8.8.8",
    "server-main": "192.168.1.19",
    "server-apps": "192.168.1.11",
}

PORT_TARGETS = {
    "pulsarmoon-api": ("192.168.1.19", 8766),
    "n8n": ("192.168.1.11", 5678),
    "whatsapp": ("192.168.1.11", 3000),
}

# ─── Estado (evita alertas repetidas) ─────────────────────
# True = up, False = down
state: dict[str, bool] = {}

# ─── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [monitor] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("monitor")


def ping(host: str, timeout: int = 5) -> bool:
    """Ping con subprocess. Linux: -c 1 -W timeout."""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), host],
            capture_output=True, timeout=timeout + 2,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def check_port(host: str, port: int, timeout: int = 5) -> bool:
    """Intenta conectar a un puerto TCP."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def send_alert(message: str) -> bool:
    """Envía alerta por WhatsApp via WWebJS HTTP API."""
    try:
        body = json.dumps({
            "number": ALERT_PHONE,
            "message": message,
        }).encode("utf-8")
        req = Request(
            WA_URL, data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        resp = urlopen(req, timeout=15)
        return resp.status == 200
    except (URLError, OSError) as e:
        logger.error("No se pudo enviar alerta WhatsApp: %s", e)
        return False


def process_check(name: str, is_up: bool):
    """Compara estado actual vs anterior. Alerta solo en transiciones."""
    prev = state.get(name)

    if prev is None:
        # Primera vez, registrar estado sin alertar
        state[name] = is_up
        status = "UP" if is_up else "DOWN"
        logger.info("[init] %s: %s", name, status)
        return

    if prev and not is_up:
        # Transición UP → DOWN
        state[name] = False
        logger.warning("[DOWN] %s", name)
        send_alert(f"🔴 *{name}* está CAÍDO")

    elif not prev and is_up:
        # Transición DOWN → UP
        state[name] = True
        logger.info("[RECOVERED] %s", name)
        send_alert(f"🟢 *{name}* se recuperó")


def run_checks():
    """Ejecuta todos los chequeos una vez."""
    # Pings
    for name, host in PING_TARGETS.items():
        result = ping(host)
        process_check(name, result)

    # Puertos (solo si el server responde ping)
    for name, (host, port) in PORT_TARGETS.items():
        # Buscar el ping target del host
        host_up = True
        for ping_name, ping_host in PING_TARGETS.items():
            if ping_host == host:
                host_up = state.get(ping_name, True)
                break

        if host_up:
            result = check_port(host, port)
        else:
            result = False
        process_check(name, result)


def main():
    logger.info("Monitor iniciado — intervalo: %ds", CHECK_INTERVAL)
    while True:
        try:
            run_checks()
        except Exception as e:
            logger.error("Error en ciclo de monitoreo: %s", e)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
