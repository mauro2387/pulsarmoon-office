"""
CRUD para la tabla leads — prospectos de PulsarMoon.
"""
import logging
from db.database import get_db

logger = logging.getLogger(__name__)


def create_lead(business_name: str, phone: str, sector: str,
                city: str, source: str = "", notes: str = "",
                score: int = 0) -> dict | None:
    """Crea un lead nuevo. Retorna el registro creado."""
    db = get_db()
    return db.fetchone(
        """INSERT INTO leads (business_name, phone, sector, city, source, notes, score)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           RETURNING *""",
        (business_name, phone, sector, city, source, notes, score)
    )


def lead_exists(business_name: str, city: str) -> bool:
    """Verifica si un lead ya existe por nombre + ciudad."""
    db = get_db()
    row = db.fetchone(
        "SELECT id FROM leads WHERE business_name = %s AND city = %s",
        (business_name, city)
    )
    return row is not None


def get_lead(lead_id: int) -> dict | None:
    """Obtiene un lead por ID."""
    db = get_db()
    return db.fetchone("SELECT * FROM leads WHERE id = %s", (lead_id,))


def update_lead_status(lead_id: int, status: str) -> bool:
    """Actualiza el estado de un lead. Estados: new, contacted, qualified, converted, lost."""
    valid = {"new", "contacted", "qualified", "converted", "lost"}
    if status not in valid:
        logger.warning("Estado inválido para lead: %s", status)
        return False
    db = get_db()
    rows = db.execute(
        "UPDATE leads SET status = %s, updated_at = NOW() WHERE id = %s",
        (status, lead_id)
    )
    return rows > 0


def get_leads_by_status(status: str) -> list[dict]:
    """Lista leads filtrados por estado."""
    db = get_db()
    return db.fetchall(
        "SELECT * FROM leads WHERE status = %s ORDER BY created_at DESC",
        (status,)
    )


def get_all_leads() -> list[dict]:
    """Lista todos los leads ordenados por fecha."""
    db = get_db()
    return db.fetchall("SELECT * FROM leads ORDER BY created_at DESC")
