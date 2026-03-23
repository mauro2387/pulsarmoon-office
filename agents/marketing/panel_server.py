"""
Servidor HTTP para el panel de aprobación de contenido de marketing.
Sirve el panel estático y expone API REST para gestionar contenido.
Puerto: 8767
"""
import json
import logging
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.marketing.db import get_all_content, get_content_by_id, update_status, get_recent_keywords
from agents.marketing.trends import fetch_trends, _load_context, _get_haiku_keywords, _search_pytrends

logger = logging.getLogger(__name__)
PANEL_DIR = Path(__file__).parent / "panel"
PORT = 8767


class PanelHandler(SimpleHTTPRequestHandler):
    """Handler que sirve archivos estáticos del panel y API REST."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PANEL_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        # API: listar contenido
        if parsed.path == "/content":
            params = parse_qs(parsed.query)
            status = params.get("status", [None])[0]
            data = get_all_content(status)
            self._json_response(200, data)
            return

        # API: obtener contenido por ID
        if parsed.path.startswith("/content/"):
            try:
                cid = int(parsed.path.split("/")[-1])
                item = get_content_by_id(cid)
                if item:
                    self._json_response(200, item)
                else:
                    self._json_response(404, {"error": "No encontrado"})
            except ValueError:
                self._json_response(400, {"error": "ID inválido"})
            return

        # API: tendencias actuales
        if parsed.path == "/trends":
            try:
                trends = fetch_trends()
                self._json_response(200, trends)
            except Exception as e:
                self._json_response(500, {"error": str(e)})
            return

        # API: solo generar keywords con Haiku (sin pytrends)
        if parsed.path == "/keywords":
            try:
                context = _load_context()
                recent = get_recent_keywords(5)
                keywords = _get_haiku_keywords(context, recent)
                self._json_response(200, {"keywords": keywords, "recent_used": recent})
            except Exception as e:
                self._json_response(500, {"error": str(e)})
            return

        # API: buscar scores de keywords específicas
        if parsed.path == "/scores":
            params = parse_qs(parsed.query)
            kw_list = params.get("kw", [])
            if not kw_list:
                self._json_response(400, {"error": "Falta param ?kw="})
                return
            try:
                # kw viene separadas por coma
                keywords = kw_list[0].split(",") if kw_list else []
                scores = _search_pytrends(keywords)
                results = sorted(
                    [{"keyword": k, "score": v} for k, v in scores.items()],
                    key=lambda x: x["score"], reverse=True
                )
                self._json_response(200, results)
            except Exception as e:
                self._json_response(500, {"error": str(e)})
            return

        # API: estado del agente en la oficina visual
        if parsed.path == "/event":
            event_file = PROJECT_ROOT / "agents" / "events" / "marketing-01.json"
            if event_file.exists():
                data = json.loads(event_file.read_text(encoding="utf-8"))
                self._json_response(200, data)
            else:
                self._json_response(200, {"status": "offline", "task": ""})
            return

        # Archivos estáticos del panel
        super().do_GET()

    def do_POST(self):
        # API: ejecutar pipeline del agente
        if self.path == "/run":
            import threading
            from agents.marketing.marketing_agent import run_pipeline

            def _bg_run():
                try:
                    run_pipeline()
                except Exception as e:
                    logger.error("Error en pipeline: %s", e)

            threading.Thread(target=_bg_run, daemon=True).start()
            self._json_response(200, {"ok": True, "msg": "Pipeline iniciado"})
            return
        self._json_response(404, {"error": "Not found"})

    def do_PUT(self):
        # API: actualizar estado de contenido
        if self.path.startswith("/content/"):
            try:
                cid = int(self.path.split("/")[-1])
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}
                new_status = body.get("status", "")
                notes = body.get("notes", "")

                if update_status(cid, new_status, notes):
                    self._json_response(200, {"ok": True})
                else:
                    self._json_response(400, {"error": "Estado inválido"})
            except (ValueError, json.JSONDecodeError) as e:
                self._json_response(400, {"error": str(e)})
            return

        self._json_response(404, {"error": "Not found"})

    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _json_response(self, code: int, data) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        logger.info(fmt, *args)


def start_panel_server() -> None:
    """Inicia el servidor del panel en el puerto configurado."""
    server = HTTPServer(("0.0.0.0", PORT), PanelHandler)
    logger.info("Panel de marketing en http://localhost:%d", PORT)
    server.serve_forever()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    start_panel_server()
