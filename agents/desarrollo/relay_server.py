"""
Relay Server — bridge entre server-main (internet) y copilot-bridge local.
Corre en Windows en la PC de Mauro. CERO dependencias externas, solo stdlib.
Puerto: 7820 | Host: 0.0.0.0
"""
import json
import os
import glob
import shutil
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

# Resultados de tareas en memoria (background threads guardan aquí)


def _find_vscode() -> str:
    """Encuentra el ejecutable de VS Code en Windows."""
    code = shutil.which("code")
    if code:
        return code
    candidates = [
        r"C:\Program Files\Microsoft VS Code\bin\code.cmd",
        r"C:\Program Files (x86)\Microsoft VS Code\bin\code.cmd",
        os.path.expandvars(
            r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "code"
TASK_RESULTS: dict[str, dict] = {}


def _scaffold_project(workspace: str, tipo: str = "web") -> bool:
    """
    Crea el scaffold del proyecto en Windows antes de abrir VSCode.
    Corre npx create-next-app de manera no interactiva desde el relay.
    Retorna True si tuvo éxito.
    """
    if not workspace:
        return False

    os.makedirs(workspace, exist_ok=True)

    # Solo hacer scaffold si la carpeta está vacía
    if os.listdir(workspace):
        logger.info("Carpeta ya tiene contenido, saltando scaffold")
        return True

    logger.info("Creando scaffold Next.js en: %s", workspace)

    try:
        result = subprocess.run(
            [
                "npx", "create-next-app@14", ".",
                "--typescript",
                "--tailwind",
                "--eslint",
                "--app",
                "--src-dir",
                "--import-alias", "@/*",
                "--use-npm",
                "--no-git",
                "--yes",
            ],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=120,
            shell=True,
        )

        if result.returncode == 0:
            logger.info("Scaffold creado exitosamente en: %s", workspace)
            return True
        else:
            logger.warning("Scaffold falló: %s", result.stderr[:200])
            return False

    except subprocess.TimeoutExpired:
        logger.warning("Scaffold timeout en: %s", workspace)
        return False
    except Exception as e:
        logger.warning("Scaffold error: %s", e)
        return False


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
        timeout = min(data.get("timeout", 300), 900)
        phone = data.get("phone", "")
        token = data.get("token", "")

        if not message:
            self._send_json({"error": "message requerido"}, 400)
            return

        task_id = f"pending-{int(time.time())}"
        logger.info("Execute [%s]: mensaje de %d chars, timeout=%ds",
                     task_id, len(message), timeout)

        # Responder inmediatamente con taskId
        TASK_RESULTS[task_id] = {"status": "processing"}
        self._send_json({
            "status": "accepted",
            "taskId": task_id,
            "message": "Procesando en background",
        })

        # Ejecutar en background thread
        t = Thread(
            target=self._execute_background,
            args=(task_id, message, workspace, timeout, phone, token),
            daemon=True,
        )
        t.start()

    @staticmethod
    def _execute_background(task_id: str, message: str,
                            workspace: str, timeout: int,
                            phone: str = "", token: str = ""):
        """Busca bridge, envía prompt y hace polling en background."""
        # Crear carpeta y scaffold del proyecto
        if workspace:
            try:
                os.makedirs(workspace, exist_ok=True)
                logger.info("[%s] Carpeta creada: %s", task_id, workspace)
                _scaffold_project(workspace)
            except Exception as e:
                logger.warning("[%s] Error en setup: %s", task_id, e)

        bridge = _find_active_bridge()
        if not bridge and workspace:
            logger.info("[%s] Bridge no activo, abriendo VS Code...",
                        task_id)
            vscode = _find_vscode()
            subprocess.Popen([vscode, "--new-window", workspace],
                             shell=True)
            waited = 0
            while waited < BRIDGE_WAIT_TIMEOUT:
                time.sleep(2)
                waited += 2
                bridge = _find_active_bridge()
                if bridge:
                    break

        if not bridge:
            logger.error("[%s] Bridge no disponible", task_id)
            TASK_RESULTS[task_id] = {
                "status": "error", "error": "Bridge no disponible",
            }
            return

        port = bridge["port"]
        try:
            resp = _post_json(
                f"http://127.0.0.1:{port}/prompt",
                {"message": message},
                timeout=30,
            )
        except (URLError, OSError) as e:
            logger.error("[%s] Error enviando al bridge: %s", task_id, e)
            TASK_RESULTS[task_id] = {
                "status": "error", "error": str(e),
            }
            return

        bridge_task_id = resp.get("taskId", task_id)
        task_dir = resp.get("taskDir", "")
        logger.info("[%s] Tarea bridge: %s en %s",
                     task_id, bridge_task_id, task_dir)

        # Polling de result.json
        result_path = Path(task_dir) / "result.json" if task_dir else None
        start = time.time()

        while time.time() - start < timeout:
            if result_path and result_path.exists():
                try:
                    result = json.loads(
                        result_path.read_text(encoding="utf-8"))
                    # Esperar para que Copilot termine de escribir
                    logger.info("[%s] result.json encontrado, "
                                "esperando 30s para confirmar...",
                                task_id)
                    time.sleep(30)
                    # Releer por si cambió
                    try:
                        result = json.loads(
                            result_path.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                    logger.info("[%s] Tarea completada", task_id)
                    TASK_RESULTS[task_id] = {
                        "status": "done",
                        "taskId": bridge_task_id,
                        "result": result,
                        "summary": result.get("summary", ""),
                    }

                    # Notificar via WhatsApp directamente
                    vercel_url = result.get("vercel_url", "")
                    summary = result.get("summary",
                                         "Proyecto completado")
                    if phone and vercel_url:
                        try:
                            _post_json(
                                "http://192.168.1.11:3000/send",
                                {
                                    "number": phone,
                                    "message": (
                                        f"\u2705 *Proyecto listo!*\n\n"
                                        f"\U0001f517 *Link de producci\u00f3n:*\n"
                                        f"{vercel_url}\n\n"
                                        f"\U0001f4c4 Documento de entrega "
                                        f"generado en docs/\n\n"
                                        f"_{summary}_"
                                    ),
                                },
                                timeout=10,
                            )
                            logger.info("[%s] WhatsApp enviado a %s",
                                        task_id, phone)
                        except Exception as e:
                            logger.warning(
                                "[%s] Error enviando WhatsApp: %s",
                                task_id, e)

                    # Actualizar DB via API (server-main)
                    if token:
                        try:
                            _post_json(
                                "http://192.168.1.19:8766/dev/session/complete",
                                {"token": token,
                                 "vercel_url": vercel_url,
                                 "summary": summary},
                                timeout=10,
                            )
                        except Exception as e:
                            logger.warning(
                                "[%s] Error actualizando DB: %s",
                                task_id, e)

                    return
                except json.JSONDecodeError:
                    pass
            time.sleep(POLL_INTERVAL)

        logger.warning("[%s] Timeout", task_id)
        TASK_RESULTS[task_id] = {
            "status": "timeout", "taskId": bridge_task_id,
        }

    def _handle_status(self):
        task_id = self.path.split("/status/", 1)[-1]

        # Primero buscar en resultados en memoria
        if task_id in TASK_RESULTS:
            self._send_json({"taskId": task_id, **TASK_RESULTS[task_id]})
            return

        # Fallback: buscar result en directorio del bridge
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
