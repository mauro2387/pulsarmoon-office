"""
Agente principal de marketing de PulsarMoon.
Orquesta: tendencias → generación → guardado → evento para oficina visual.
Ejecutable manual: python -m agents.marketing.marketing_agent
"""
import logging
import sys
import time
from pathlib import Path

# Agregar raíz del proyecto al path para imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.base_agent import BaseAgent
from agents.marketing.trends import fetch_trends
from agents.marketing.generator import generate_all
from agents.marketing.db import save_content, save_trends

logger = logging.getLogger(__name__)


class MarketingAgent(BaseAgent):
    """Agente de marketing que hereda de BaseAgent."""

    def __init__(self):
        super().__init__(
            agent_id="marketing-01",
            agent_name="Marketing AI",
            department="marketing",
            model="sonnet",
            company_id="pulsarmoon",
        )


# Instancia global del agente
_agent = MarketingAgent()


def run_pipeline() -> dict:
    """
    Pipeline completo:
    1. Buscar tendencias en Uruguay
    2. Generar contenido con Claude Sonnet
    3. Guardar en SQLite
    4. Actualizar estado en la oficina visual
    """
    _agent.write_event("working", "Analizando tendencias en Uruguay...")

    # 1. Tendencias
    try:
        trends = fetch_trends()
        save_trends(trends)
        _agent.log("trends_fetched", {"count": len(trends)})
    except Exception as e:
        _agent.write_event("error", f"Error en tendencias: {e}")
        raise

    _agent.write_event("working", f"Generando contenido sobre: {trends[0]['keyword']}")

    # 2. Generar contenido
    try:
        content = generate_all(trends)
        _agent.log("content_generated", {"keyword": content["keyword"]})
    except Exception as e:
        _agent.write_event("error", f"Error generando contenido: {e}")
        raise

    _agent.write_event("working", "Guardando en base de datos...")

    # 3. Guardar en SQLite
    try:
        content_id = save_content(
            trend_keyword=content["keyword"],
            trend_score=content["score"],
            blog_post=content["blog_post"],
            caption_ig=content["caption_ig"],
            caption_fb=content["caption_fb"],
            image_url=content.get("image_url", ""),
        )
        _agent.log("content_saved", {"id": content_id})
    except Exception as e:
        _agent.write_event("error", f"Error guardando: {e}")
        raise

    _agent.write_event("done", f"Contenido #{content_id} listo para revisión")

    # Volver a idle después de 30 segundos
    time.sleep(30)
    _agent.write_event("idle", "")

    return content


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    logger.info("=== Ejecución manual del agente de marketing ===")
    result = run_pipeline()
    logger.info("Keyword: %s", result["keyword"])
    logger.info("Blog: %d chars", len(result["blog_post"]))
    logger.info("IG: %d chars", len(result["caption_ig"]))
    logger.info("FB: %d chars", len(result["caption_fb"]))
    logger.info("=== Completado ===")
