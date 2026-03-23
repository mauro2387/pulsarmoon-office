"""
CRUD para la tabla content — contenido de marketing generado por IA.
"""
import logging
from db.database import get_db

logger = logging.getLogger(__name__)


def save_content(topic: str, blog: str, caption_ig: str,
                 caption_fb: str, image_url: str = None) -> dict | None:
    """Guarda contenido generado. Estado inicial: pending."""
    db = get_db()
    return db.fetchone(
        """INSERT INTO content
           (topic, blog, caption_ig, caption_fb, image_url)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING *""",
        (topic, blog, caption_ig, caption_fb, image_url)
    )


def get_pending_content() -> list[dict]:
    """Lista contenido pendiente de revisión."""
    db = get_db()
    return db.fetchall(
        "SELECT * FROM content WHERE status = 'pending' ORDER BY created_at DESC"
    )


def approve_content(content_id: int) -> bool:
    """Aprueba contenido para publicar."""
    db = get_db()
    rows = db.execute(
        "UPDATE content SET status = 'approved', reviewed_at = NOW() WHERE id = %s",
        (content_id,)
    )
    return rows > 0


def reject_content(content_id: int) -> bool:
    """Rechaza contenido."""
    db = get_db()
    rows = db.execute(
        "UPDATE content SET status = 'rejected', reviewed_at = NOW() WHERE id = %s",
        (content_id,)
    )
    return rows > 0
