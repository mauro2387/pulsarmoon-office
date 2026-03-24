"""
Relay Server — bridge entre server-main (internet) y copilot-bridge local.
Corre en Windows en la PC de Mauro. CERO dependencias externas, solo stdlib.
Puerto: 7820 | Host: 0.0.0.0
"""
import json
import os
import glob
import subprocess
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import URLError
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [relay] %(levelname)s: %(message)s",
)
logger = logging.getLogger("relay")

BRIDGE_DIR = Path.home() / ".copilot-bridge"
FORMS_DIR = Path(__file__).resolve().parent / "forms"
RELAY_PORT = 7820
POLL_INTERVAL = 5
BRIDGE_WAIT_TIMEOUT = 60


def _find_active_bridge() -> dict | None:
    """Busca bridge activo en ~/.copilot-bridge/*.json."""
    if not BRIDGE_DIR.exists():
        return None
    for fp in sorted(BRIDGE_DIR.glob("*.json"), key=os.path.getmtime,
                     reverse=True):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            port = data.get("port")
            if not port:
                continue
            # Verificar que el bridge responde
            req = Request(f"http://127.0.0.1:{port}/health")
            resp = urlopen(req, timeout=3)
            if resp.status == 200:
                data["_file"] = str(fp)
                return data
        except (json.JSONDecodeError, URLError, OSError):
            continue
    return None


def _post_json(url: str, payload: dict, timeout: int = 30) -> dict:
    """POST JSON con stdlib."""
    body = json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, method="POST",
                  headers={"Content-Type": "application/json"})
    resp = urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str, timeout: int = 10) -> dict:
    """GET JSON con stdlib."""
    req = Request(url)
    resp = urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode("utf-8"))


class RelayHandler(BaseHTTPRequestHandler):
    """Handler HTTP para el relay."""

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _send_html(self, filepath: Path):
        """Sirve archivo HTML estático."""
        if not filepath.exists():
            self._send_json({"error": "Not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(filepath.read_bytes())

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods",
                         "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]  # Ignorar query params para routing
        if path == "/health":
            self._handle_health()
        elif path in ("/", "/dev", "/dev/"):
            self._send_html(FORMS_DIR / "index.html")
        elif path.startswith("/status/"):
            self._handle_status()
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path == "/execute":
            self._handle_execute()
        elif self.path == "/open-vscode":
            self._handle_open_vscode()
        else:
            self._send_json({"error": "Not found"}, 404)

    def _handle_health(self):
        bridge = _find_active_bridge()
        self._send_json({
            "status": "ok",
            "bridge_active": bridge is not None,
            "port": bridge.get("port") if bridge else None,
            "workspace": bridge.get("workspace") if bridge else None,
        })

    def _handle_execute(self):
        data = self._read_body()
        message = data.get("message", "")
        workspace = data.get("workspace", "")
        timeout = min(data.get("timeout", 300), 1800)

        if not message:
            self._send_json({"error": "message requerido"}, 400)
            return

        logger.info("Execute: mensaje de %d chars, timeout=%ds",
                     len(message), timeout)

        # Buscar bridge activo
        bridge = _find_active_bridge()
        if not bridge and workspace:
            logger.info("Bridge no activo, abriendo VS Code...")
            subprocess.Popen(["code", workspace])
            waited = 0
            while waited < BRIDGE_WAIT_TIMEOUT:
                time.sleep(2)
                waited += 2
                bridge = _find_active_bridge()
                if bridge:
                    break

        if not bridge:
            self._send_json({
                "status": "error",
                "error": "Bridge no disponible",
            }, 503)
            return

        # Enviar prompt al bridge
        port = bridge["port"]
        try:
            resp = _post_json(
                f"http://127.0.0.1:{port}/prompt",
                {"message": message},
                timeout=30,
            )
        except (URLError, OSError) as e:
            logger.error("Error enviando al bridge: %s", e)
            self._send_json({"status": "error", "error": str(e)}, 502)
            return

        task_id = resp.get("taskId", "")
        task_dir = resp.get("taskDir", "")
        logger.info("Tarea creada: %s en %s", task_id, task_dir)

        # Polling de result.json
        result_path = Path(task_dir) / "result.json" if task_dir else None
        start = time.time()
        result = None

        while time.time() - start < timeout:
            if result_path and result_path.exists():
                try:
                    result = json.loads(
                        result_path.read_text(encoding="utf-8"))
                    break
                except json.JSONDecodeError:
                    pass
            time.sleep(POLL_INTERVAL)

        if result:
            logger.info("Tarea completada: %s", task_id)
            self._send_json({
                "status": "done", "taskId": task_id,
                "result": result,
                "summary": result.get("summary", ""),
            })
        else:
            logger.warning("Timeout para tarea: %s", task_id)
            self._send_json({
                "status": "timeout", "taskId": task_id,
            })

    def _handle_status(self):
        task_id = self.path.split("/status/", 1)[-1]
        # Buscar result en directorio del bridge
        bridge = _find_active_bridge()
        if not bridge:
            self._send_json({"status": "unknown", "taskId": task_id})
            return
        tasks_dir = BRIDGE_DIR / "tasks" / task_id
        result_path = tasks_dir / "result.json"
        if result_path.exists():
            try:
                result = json.loads(
                    result_path.read_text(encoding="utf-8"))
                self._send_json({
                    "status": "done", "taskId": task_id,
                    "result": result,
                })
                return
            except json.JSONDecodeError:
                pass
        self._send_json({"status": "pending", "taskId": task_id})

    def _handle_open_vscode(self):
        data = self._read_body()
        workspace = data.get("workspace", "")
        if not workspace:
            self._send_json({"error": "workspace requerido"}, 400)
            return
        subprocess.Popen(["code", workspace])
        logger.info("VS Code abierto en: %s", workspace)
        self._send_json({"status": "ok"})

    def log_message(self, fmt, *args):
        logger.debug(fmt, *args)


class ThreadedHTTPServer(HTTPServer):
    """HTTPServer con threads por request."""
    def process_request(self, request, client_address):
        t = Thread(target=self._handle, args=(request, client_address))
        t.daemon = True
        t.start()

    def _handle(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


def main():
    server = ThreadedHTTPServer(("0.0.0.0", RELAY_PORT), RelayHandler)
    logger.info("Relay server en http://0.0.0.0:%d", RELAY_PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Relay detenido.")
        server.server_close()


if __name__ == "__main__":
    main()
