"""
Módulo de tendencias inteligente para PulsarMoon.
1. Haiku genera 15 keywords dinámicas basadas en contexto + fecha + historial
2. pytrends busca esos keywords en Google Trends Uruguay
3. Retorna top 5 con scores reales
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from pytrends.request import TrendReq

from agents.marketing.db import get_recent_keywords

load_dotenv()
logger = logging.getLogger(__name__)

CONTEXT_FILE = Path(__file__).parent / "context.md"
BATCH_SIZE = 5
GEO = "UY"
TIMEFRAME = "today 3-m"
HAIKU_MODEL = "claude-haiku-4-20250514"

# Meses y estaciones en español
SEASONS = {
    1: "verano (temporada alta turística)",
    2: "verano (temporada alta turística)",
    3: "fin de verano / inicio de otoño",
    4: "otoño (temporada baja, empresas evalúan presupuesto)",
    5: "otoño (temporada baja)",
    6: "invierno (presupuestos del segundo semestre)",
    7: "invierno",
    8: "invierno (planificación para temporada alta)",
    9: "primavera (empresas preparan temporada)",
    10: "primavera (preparación pre-verano)",
    11: "primavera tardía (últimos preparativos pre-temporada)",
    12: "inicio de verano (temporada alta arranca)",
}


def _load_context() -> str:
    """Lee el archivo context.md con info de PulsarMoon."""
    if CONTEXT_FILE.exists():
        return CONTEXT_FILE.read_text(encoding="utf-8")
    logger.warning("context.md no encontrado, usando contexto mínimo")
    return "PulsarMoon: agencia de desarrollo web y marketing digital en Punta del Este, Uruguay."


def _get_haiku_keywords(context: str, recent: list[str]) -> list[str]:
    """Llama a Haiku para generar 15 keywords inteligentes."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("Sin ANTHROPIC_API_KEY, usando keywords por defecto")
        return _default_keywords()

    now = datetime.now()
    season = SEASONS.get(now.month, "")
    recent_text = ", ".join(recent) if recent else "(ninguno, es la primera vez)"

    prompt = f"""Sos un estratega de marketing digital para PulsarMoon.

CONTEXTO DE LA EMPRESA:
{context[:2000]}

FECHA ACTUAL: {now.strftime('%d de %B de %Y')}
MES/ESTACIÓN: {now.strftime('%B')} — {season}
ÚLTIMOS TEMAS USADOS (NO repetir): {recent_text}

TAREA: Generá exactamente 15 keywords para buscar en Google Trends Uruguay.

REGLAS:
- Keywords en español, como las buscaría alguien en Uruguay
- Mezcla de: keywords del rubro de PulsarMoon + eventos/contexto actual + estacionales
- Pensá en qué puede estar buscando un empresario de Punta del Este HOY
- NO repitas los temas ya usados
- Cada keyword debe ser 2-4 palabras (lo que busca la gente)
- Incluí razonamiento breve de por qué elegís esas keywords

FORMATO DE RESPUESTA (JSON estricto):
{{
  "reasoning": "Breve explicación de tu lógica...",
  "keywords": ["keyword 1", "keyword 2", ..., "keyword 15"]
}}

Respondé SOLO el JSON, nada más."""

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        # Parsear JSON de la respuesta
        data = json.loads(text)
        keywords = data.get("keywords", [])
        reasoning = data.get("reasoning", "")
        logger.info("Haiku razonamiento: %s", reasoning)
        logger.info("Haiku generó %d keywords: %s", len(keywords), keywords)
        return keywords[:15] if keywords else _default_keywords()
    except Exception as e:
        logger.warning("Error en Haiku, usando keywords por defecto: %s", e)
        return _default_keywords()


def _default_keywords() -> list[str]:
    """Keywords fallback si Haiku no responde."""
    return [
        "desarrollo web Uruguay",
        "página web empresa",
        "marketing digital Punta del Este",
        "tienda online Uruguay",
        "diseño web profesional",
        "aplicación móvil empresa",
        "automatización procesos",
        "sistema gestión empresa",
        "e-commerce Uruguay",
        "consultoría tecnológica",
        "transformación digital pyme",
        "redes sociales empresa",
        "SEO Uruguay",
        "software a medida",
        "mantenimiento web",
    ]


def _search_pytrends(keywords: list[str]) -> dict[str, float]:
    """Busca keywords en Google Trends UY. Retorna dict keyword→score."""
    logger.info("Buscando %d keywords en Google Trends (geo=%s)...", len(keywords), GEO)
    all_scores: dict[str, float] = {}

    try:
        pytrends = TrendReq(hl="es-UY", tz=180)
    except Exception as e:
        logger.error("Error inicializando pytrends: %s", e)
        return {kw: 0 for kw in keywords}

    for i in range(0, len(keywords), BATCH_SIZE):
        batch = keywords[i:i + BATCH_SIZE]
        try:
            pytrends.build_payload(batch, cat=0, timeframe=TIMEFRAME, geo=GEO)
            df = pytrends.interest_over_time()
            if df.empty:
                logger.warning("Sin datos para batch: %s", batch)
                for kw in batch:
                    all_scores[kw] = 0
                continue
            for kw in batch:
                all_scores[kw] = float(df[kw].mean()) if kw in df.columns else 0
        except Exception as e:
            logger.warning("Error en batch %s: %s", batch, e)
            for kw in batch:
                all_scores[kw] = 0

    return all_scores


def fetch_trends() -> list[dict]:
    """
    Pipeline completo:
    1. Haiku genera keywords inteligentes
    2. pytrends busca scores reales en Uruguay
    3. Retorna top 5 ordenados por score
    """
    # Cargar contexto y historial
    context = _load_context()
    recent = get_recent_keywords(5)

    # 1. Haiku genera keywords
    keywords = _get_haiku_keywords(context, recent)

    # 2. pytrends busca scores reales
    scores = _search_pytrends(keywords)

    # 3. Ordenar y retornar top 5
    results = [
        {"keyword": kw, "score": score}
        for kw, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
    ][:5]

    logger.info("Top tendencias: %s", [r["keyword"] for r in results])
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    trends = fetch_trends()
    print("\nTop 5 tendencias:")
    for t in trends:
        print(f"  {t['keyword']}: {t['score']:.1f}")
