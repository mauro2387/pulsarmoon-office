"""
Generador de contenido usando Anthropic API (Claude Sonnet 4.6).
Produce blog post SEO, caption Instagram y caption Facebook.
"""
import logging
import os
import sys
import base64
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic
from openai import OpenAI

load_dotenv()
logger = logging.getLogger(__name__)

# Path para imports de db/
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

# Contexto de marca hardcodeado como fallback
_BRAND_CONTEXT_FALLBACK = """
Empresa: PulsarMoon — agencia de desarrollo web, sistemas, aplicaciones móviles
y marketing digital ubicada en Punta del Este, Uruguay.
Tono: formal, elegante y cercano. Profesional pero accesible.
Audiencia: empresas y emprendedores en Uruguay y la región.
"""

_CONTEXT_FILE = Path(__file__).parent / "context.md"


def load_context() -> str:
    """Lee contexto de marca desde context.md. Usa fallback si no existe."""
    if _CONTEXT_FILE.exists():
        return _CONTEXT_FILE.read_text(encoding="utf-8")
    logger.warning("context.md no encontrado, usando fallback")
    return _BRAND_CONTEXT_FALLBACK


# Cargar contexto una vez al importar
BRAND_CONTEXT = load_context()


def get_recent_topics(limit: int = 5) -> list[str]:
    """Obtiene temas recientes de PostgreSQL para evitar repetir contenido."""
    try:
        from db.database import get_db
        rows = get_db().fetchall(
            "SELECT topic, created_at FROM content "
            "ORDER BY created_at DESC LIMIT %s", (limit,))
        return [f"{r['topic']} ({r['created_at'].strftime('%d/%m')})" for r in rows]
    except Exception:
        return []


def _get_client() -> Anthropic:
    """Inicializa cliente Anthropic con API key desde .env."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY no configurada en .env")
    return Anthropic(api_key=api_key)


def _get_openai_client() -> OpenAI:
    """Inicializa cliente OpenAI con API key desde .env."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY no configurada en .env")
    return OpenAI(api_key=api_key)


def generate_image(topic: str) -> str | None:
    """Genera imagen de marketing con OpenAI gpt-image-1. Retorna data URI o None."""
    logger.info("Generando imagen para: %s", topic)

    prompt = (
        "Professional marketing image for a web development and digital marketing "
        f"agency in Uruguay. Topic: {topic}. Style: modern, clean, corporate, "
        "minimal. Colors: deep blue and white. No text in image."
    )

    try:
        client = _get_openai_client()
        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
            n=1,
        )
        # gpt-image-1 retorna b64_json por defecto
        b64 = result.data[0].b64_json
        if b64:
            return f"data:image/png;base64,{b64}"
        # Fallback a URL si el modelo retorna url
        if result.data[0].url:
            return result.data[0].url
        return None
    except Exception as e:
        logger.warning("Error generando imagen (no bloqueante): %s", e)
        return None


def generate_blog_post(keyword: str, trends: list[dict], history: str = "") -> str:
    """Genera blog post SEO de ~800 palabras sobre el keyword trending."""
    logger.info("Generando blog post sobre: %s", keyword)

    trends_text = "\n".join(
        f"- {t['keyword']} (score: {t['score']:.0f})" for t in trends
    )

    prompt = f"""Escribí un blog post SEO en español para PulsarMoon.
{BRAND_CONTEXT}

Tema principal: {keyword}
Tendencias actuales en Uruguay:
{trends_text}

{history}REQUISITOS:
- ~800 palabras
- Título H1 atractivo con la keyword principal
- 2-3 subtítulos H2
- Introducción que enganche
- Secciones con valor real para el lector
- Call to action final mencionando PulsarMoon
- Optimizado para SEO (keyword en título, primer párrafo, subtítulos)
- Formato: Markdown
- NO uses "en el mundo digital de hoy" ni frases cliché similares

Devolvé SOLO el blog post en Markdown, sin explicaciones adicionales."""

    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def generate_caption_ig(keyword: str, blog_summary: str, history: str = "") -> str:
    """Genera caption de Instagram (máx 2200 chars, emojis, 5 hashtags)."""
    logger.info("Generando caption Instagram sobre: %s", keyword)

    prompt = f"""Escribí un caption de Instagram para PulsarMoon.
{BRAND_CONTEXT}

Tema: {keyword}
Resumen del blog: {blog_summary[:500]}

{history}REQUISITOS:
- Máximo 2200 caracteres
- Emojis relevantes pero sin abusar (3-5 emojis)
- Gancho en la primera línea (la gente ve solo las primeras palabras)
- Contenido de valor, no solo promoción
- Terminá con call to action
- Exactamente 5 hashtags al final (relevantes para Uruguay y el tema)
- Español rioplatense natural

Devolvé SOLO el caption, sin explicaciones."""

    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def generate_caption_fb(keyword: str, blog_summary: str, history: str = "") -> str:
    """Genera caption de Facebook (más largo e informativo)."""
    logger.info("Generando caption Facebook sobre: %s", keyword)

    prompt = f"""Escribí un post de Facebook para PulsarMoon.
{BRAND_CONTEXT}

Tema: {keyword}
Resumen del blog: {blog_summary[:500]}

{history}REQUISITOS:
- Más largo que Instagram, informativo y profesional
- Sin límite estricto de caracteres pero no más de 3000
- Puede tener formato con saltos de línea
- Emojis moderados (2-3 máximo)
- Incluí datos o estadísticas si es relevante
- Call to action al final con link al blog (placeholder: [LINK])
- Tono que invite al diálogo y comentarios

Devolvé SOLO el post de Facebook, sin explicaciones."""

    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1524,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def generate_all(trends: list[dict]) -> dict:
    """
    Pipeline completo: genera blog + IG + FB para la tendencia top.
    Retorna dict con todo el contenido generado.
    """
    if not trends:
        raise ValueError("Sin tendencias para generar contenido")

    top = trends[0]
    keyword = top["keyword"]

    # Memoria: evitar temas repetidos
    recent = get_recent_topics()
    history = ""
    if recent:
        topics_list = "\n".join(f"- {t}" for t in recent)
        history = (
            "IMPORTANTE — Temas de posts anteriores (NO repetir ni temas similares):\n"
            f"{topics_list}\n"
            "El nuevo post debe ser sobre un tema DIFERENTE y FRESCO.\n\n"
        )

    blog = generate_blog_post(keyword, trends, history)
    # Usar primeros 500 chars del blog como resumen para captions
    blog_summary = blog[:500]
    ig = generate_caption_ig(keyword, blog_summary, history)
    fb = generate_caption_fb(keyword, blog_summary, history)

    # Generar imagen (no bloqueante si falla)
    image_url = generate_image(keyword)

    return {
        "keyword": keyword,
        "score": top["score"],
        "blog_post": blog,
        "caption_ig": ig,
        "caption_fb": fb,
        "image_url": image_url or "",
    }
