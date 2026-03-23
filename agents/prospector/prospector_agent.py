"""
Agente Prospector de PulsarMoon.
Busca leads via Google Places, calcula score Python puro,
genera mensajes personalizados (Haiku solo para score alto).
"""
import logging
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from agents.base_agent import BaseAgent
from agents.templates.whatsapp import PRIMER_CONTACTO
from db.leads import create_lead, lead_exists, update_lead_status

load_dotenv()
logger = logging.getLogger(__name__)

PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

SECTORS = [
    "restaurant", "clinica", "inmobiliaria", "hotel", "tienda",
    "consultorio", "gym", "salon de belleza", "farmacia", "boutique",
]

# Fallback queries si inteligencia no disponible
_FALLBACK_QUERIES = [
    "restaurant Punta del Este", "hotel Maldonado",
    "clinica Punta del Este", "gimnasio Punta del Este",
    "inmobiliaria Maldonado",
]


class ProspectorAgent(BaseAgent):
    """Busca negocios sin web y los convierte en leads calificados."""

    def __init__(self):
        super().__init__(
            agent_id="prospector-01",
            agent_name="Prospector",
            department="oportunidades",
            model="haiku",
            company_id="pulsarmoon",
        )
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")

    # ── Búsqueda de leads (Python puro, sin LLM) ──

    def search_leads(self, city: str = "Punta del Este",
                     sector: str | None = None, limit: int = 20) -> list[dict]:
        """Busca negocios en Google Places y guarda los que califican."""
        if not self.api_key:
            logger.error("GOOGLE_MAPS_API_KEY no configurada")
            return []

        query = f"{sector or 'negocio'} en {city} Uruguay"
        try:
            resp = requests.get(PLACES_SEARCH_URL, params={
                "query": query, "key": self.api_key, "language": "es",
            }, timeout=15)
            resp.raise_for_status()
            results = resp.json().get("results", [])[:limit]
        except requests.RequestException as e:
            logger.error("Error Google Places: %s", e)
            return []

        leads = []
        for place in results:
            name = place.get("name", "")
            # Evitar duplicados
            if lead_exists(name, city):
                continue

            has_web = self.check_has_website(place)
            score = self._calculate_score(place, has_web)
            if score < 50:
                continue

            phone = place.get("formatted_phone_number", "")
            # Si no hay teléfono en búsqueda, intentar con details
            if not phone:
                phone = self._get_phone_from_details(place.get("place_id"))

            lead = create_lead(
                business_name=name,
                phone=phone,
                sector=sector or "general",
                city=city,
                source="google_places",
                score=score,
            )
            if lead:
                leads.append(lead)

        return leads

    def check_has_website(self, place_data: dict) -> bool:
        """Verifica si el negocio tiene website (Python puro, sin LLM)."""
        if "website" in place_data:
            return True
        # Consultar Place Details si hay place_id
        place_id = place_data.get("place_id")
        if not place_id or not self.api_key:
            return False
        try:
            resp = requests.get(PLACE_DETAILS_URL, params={
                "place_id": place_id, "fields": "website",
                "key": self.api_key,
            }, timeout=10)
            resp.raise_for_status()
            result = resp.json().get("result", {})
            return "website" in result
        except requests.RequestException:
            return False

    def _calculate_score(self, place: dict, has_website: bool) -> int:
        """Score Python puro — sin LLM."""
        score = 0
        if not has_website:
            score += 40
        if place.get("formatted_phone_number") or place.get("place_id"):
            score += 20
        rating = place.get("rating", 0)
        if rating > 4.0:
            score += 15
        reviews = place.get("user_ratings_total", 0)
        if reviews > 10:
            score += 10
        if not place.get("opening_hours"):
            score += 5
        return score

    def _get_phone_from_details(self, place_id: str | None) -> str:
        """Obtiene teléfono desde Place Details API."""
        if not place_id or not self.api_key:
            return ""
        try:
            resp = requests.get(PLACE_DETAILS_URL, params={
                "place_id": place_id,
                "fields": "formatted_phone_number",
                "key": self.api_key,
            }, timeout=10)
            resp.raise_for_status()
            return resp.json().get("result", {}).get(
                "formatted_phone_number", "")
        except requests.RequestException:
            return ""

    # ── Generación de mensajes (LLM solo para score alto) ──

    def generate_message(self, lead: dict) -> str:
        """Genera mensaje WhatsApp. LLM solo si score >= 70."""
        if lead.get("score", 0) < 70:
            # Template sin LLM
            return self.format_message(
                PRIMER_CONTACTO,
                nombre=lead.get("business_name", ""),
                negocio=lead.get("business_name", ""),
                ciudad=lead.get("city", "Punta del Este"),
            )
        # LLM (Haiku) para leads de alto score
        prompt = (
            f"Generá un mensaje WhatsApp personalizado y convincente "
            f"(máx 3 líneas) para {lead['business_name']}, "
            f"un {lead.get('sector', 'negocio')} en "
            f"{lead.get('city', 'Punta del Este')}. "
            f"Tono: cercano, profesional, sin presión. "
            f"Mencionar que no tienen web. "
            f"Terminar con pregunta abierta."
        )
        msg = self.call_llm(prompt, max_tokens=200)
        return msg or self.format_message(
            PRIMER_CONTACTO,
            nombre=lead.get("business_name", ""),
            negocio=lead.get("business_name", ""),
            ciudad=lead.get("city", "Punta del Este"),
        )

    # ── Pipeline diario ──

    def _get_search_queries(self) -> list[str]:
        """Obtiene queries del agente de inteligencia o usa fallback."""
        try:
            from agents.inteligencia.intelligence_agent import get_current_insights
            insights = get_current_insights()
            queries = insights.get("prospector_queries", [])
            if queries:
                logger.info("Usando %d queries de inteligencia", len(queries))
                return queries
        except Exception as e:
            logger.warning("Inteligencia no disponible: %s", e)
        return _FALLBACK_QUERIES

    def run_daily(self) -> dict:
        """Pipeline completo: busca leads con queries dinámicos."""
        self.write_event("working", "Buscando leads en Punta del Este...")
        total = 0
        all_leads = []
        queries = self._get_search_queries()

        for query in queries:
            try:
                # Extraer ciudad y sector del query
                parts = query.rsplit(" ", 2)
                city = " ".join(parts[-2:]) if len(parts) >= 2 else "Punta del Este"
                sector = parts[0] if len(parts) >= 2 else query
                leads = self.search_leads(city=city, sector=sector, limit=20)
                for lead in leads:
                    msg = self.generate_message(lead)
                    from db.database import get_db
                    get_db().execute(
                        "UPDATE leads SET notes = %s WHERE id = %s",
                        (msg, lead["id"]))
                    self.log("lead_found", {
                        "lead": lead["business_name"],
                        "score": lead["score"],
                        "sector": sector,
                    })
                    total += 1
                all_leads.extend(leads)
            except Exception as e:
                logger.error("Error en query '%s': %s", query, e)

        self.write_event("done", f"{total} leads nuevos encontrados")
        return {"total": total, "leads": all_leads}


# Instancia global
_agent = ProspectorAgent()


def run_daily() -> dict:
    """Wrapper para ejecutar desde scheduler."""
    return _agent.run_daily()
