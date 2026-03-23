"""
CRUD para la tabla clients — clientes activos de PulsarMoon.
"""
import logging
from db.database import get_db

logger = logging.getLogger(__name__)


def create_client(lead_id: int, business_name: str, phone: str,
                  email: str, sector: str, monthly_fee: float) -> dict | None:
    """Crea un cliente nuevo a partir de un lead convertido."""
    db = get_db()
    return db.fetchone(
        """INSERT INTO clients
           (lead_id, business_name, phone, email, sector, monthly_fee)
           VALUES (%s, %s, %s, %s, %s, %s)
           RETURNING *""",
        (lead_id, business_name, phone, email, sector, monthly_fee)
    )


def get_client(client_id: int) -> dict | None:
    """Obtiene un cliente por ID."""
    db = get_db()
    return db.fetchone("SELECT * FROM clients WHERE id = %s", (client_id,))


def get_all_clients() -> list[dict]:
    """Lista todos los clientes activos."""
    db = get_db()
    return db.fetchall(
        "SELECT * FROM clients WHERE active = TRUE ORDER BY created_at DESC"
    )


def update_client(client_id: int, **kwargs) -> bool:
    """Actualiza campos de un cliente. Solo acepta campos permitidos."""
    allowed = {"business_name", "phone", "email", "sector",
               "monthly_fee", "active", "notes"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        logger.warning("update_client: sin campos válidos para actualizar")
        return False

    # Construir SET dinámico con parámetros seguros
    set_parts = [f"{col} = %s" for col in fields]
    set_parts.append("updated_at = NOW()")
    values = list(fields.values()) + [client_id]

    db = get_db()
    rows = db.execute(
        f"UPDATE clients SET {', '.join(set_parts)} WHERE id = %s",
        tuple(values)
    )
    return rows > 0
