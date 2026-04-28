"""
Email Prospector Agent — PulsarMoon.
Pipeline diario internacional: Google Places + análisis de sitio (BS4) +
Haiku para cold emails. NO envía mails automáticamente — solo guarda
con status='pending_approval' y notifica por WhatsApp.
"""
import json
import logging
import os
import re
import smtplib
import time
from datetime import datetime, date
from difflib import SequenceMatcher
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from agents.base_agent import BaseAgent
from db.database import get_db
from db.leads import lead_exists

load_dotenv()
logger = logging.getLogger(__name__)

PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

NICHES = [
    "restaurante", "hotel", "clínica dental", "psicólogo",
    "fisioterapia", "inmobiliaria", "veterinaria", "farmacia",
    "gimnasio", "salon de belleza", "boutique ropa", "joyería",
    "arquitecto", "contador", "abogado", "agencia de viajes",
    "escuela de idiomas", "centro de estética", "fotógrafo", "catering",
]

CITIES = [
    {"city": "Buenos Aires", "country": "AR", "lang": "es"},
    {"city": "Córdoba", "country": "AR", "lang": "es"},
    {"city": "Bogotá", "country": "CO", "lang": "es"},
    {"city": "Medellín", "country": "CO", "lang": "es"},
    {"city": "Ciudad de México", "country": "MX", "lang": "es"},
    {"city": "Guadalajara", "country": "MX", "lang": "es"},
    {"city": "Lima", "country": "PE", "lang": "es"},
    {"city": "Santiago", "country": "CL", "lang": "es"},
    {"city": "Madrid", "country": "ES", "lang": "es"},
    {"city": "Barcelona", "country": "ES", "lang": "es"},
    {"city": "Valencia", "country": "ES", "lang": "es"},
    {"city": "Montevideo", "country": "UY", "lang": "es"},
    {"city": "Asunción", "country": "PY", "lang": "es"},
    {"city": "Quito", "country": "EC", "lang": "es"},
    {"city": "Miami", "country": "US", "lang": "en"},
    {"city": "Houston", "country": "US", "lang": "en"},
]

EMAIL_BLACKLIST = ["sentry", "example", "woocommerce", "jquery", "schema",
                   "noreply", "no-reply", "wordpress", "plugin"]
DIRECTORY_DOMAINS = ["google.", "facebook.", "instagram.", "tripadvisor.",
                     "yelp.", "yelu.", "guiaempresas.", "paginasamarillas.",
                     "linkedin.", "twitter.", "youtube.", "wikipedia.",
                     "doctoralia.", "booking.", "trivago.", "foursquare."]
CONTACT_PATHS = ["/contacto", "/contact", "/about", "/nosotros",
                 "/quienes-somos", "/contact-us", "/contactenos"]
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PulsarMoonProspector/1.0)"
}
DAILY_EMAIL_LIMIT = 60


class EmailProspectorAgent(BaseAgent):
    """Prospector internacional por email — pipeline completo diario."""

    def __init__(self):
        super().__init__(
            agent_id="email-prospector-01",
            agent_name="Email Prospector",
            department="oportunidades",
            model="haiku",
            company_id="pulsarmoon",
        )
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self._run_migrations()

    # ── Migraciones ───────────────────────────────────────────────────────

    def _run_migrations(self) -> None:
        """Agrega columnas nuevas a la tabla leads (idempotente)."""
        migrations = [
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS email TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS website TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS country TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS has_email BOOLEAN DEFAULT FALSE",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_sent BOOLEAN DEFAULT FALSE",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_sent_at TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS site_issues JSONB DEFAULT '[]'",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS site_score INTEGER DEFAULT 0",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS lang TEXT DEFAULT 'es'",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_subject TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_body TEXT",
        ]
        for sql in migrations:
            try:
                get_db().execute(sql)
            except Exception as e:
                logger.warning("Migration skip (%s): %s", sql[:60], e)

    # ── Selección del día ─────────────────────────────────────────────────

    def get_today_target(self) -> tuple[str, dict]:
        """Devuelve (nicho, ciudad) según día del año."""
        doy = date.today().timetuple().tm_yday
        return NICHES[doy % len(NICHES)], CITIES[doy % len(CITIES)]

    # ── Etapa 1: Google Places ────────────────────────────────────────────

    def search_places(self, niche: str, city: str, lang: str) -> list[dict]:
        """Busca negocios via Google Places Text Search."""
        if not self.api_key:
            logger.error("GOOGLE_MAPS_API_KEY no configurada")
            return []
        try:
            resp = requests.get(PLACES_SEARCH_URL, params={
                "query": f"{niche} en {city}",
                "key": self.api_key,
                "language": lang,
            }, timeout=10)
            resp.raise_for_status()
            return resp.json().get("results", [])[:20]
        except requests.RequestException as e:
            logger.error("Google Places error: %s", e)
            return []

    def get_place_details(self, place_id: str) -> dict:
        """Obtiene detalles completos de un place_id."""
        if not place_id or not self.api_key:
            return {}
        try:
            resp = requests.get(PLACE_DETAILS_URL, params={
                "place_id": place_id,
                "fields": ("name,formatted_phone_number,formatted_address,"
                           "rating,user_ratings_total,website,opening_hours"),
                "key": self.api_key,
            }, timeout=10)
            resp.raise_for_status()
            return resp.json().get("result", {})
        except requests.RequestException as e:
            logger.warning("Place details error: %s", e)
            return {}

    # ── Etapa 2: Buscar website (sin Google Places) ───────────────────────

    def find_website_fallback(self, business_name: str, city: str) -> str | None:
        """Búsqueda DuckDuckGo HTML para encontrar website (sin API key)."""
        try:
            q = f'"{business_name}" "{city}" sitio web'
            resp = requests.get("https://duckduckgo.com/html/",
                                params={"q": q},
                                headers=HTTP_HEADERS, timeout=10)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.select("a.result__url, a.result__a"):
                href = a.get("href", "")
                if not href.startswith("http"):
                    continue
                domain = urlparse(href).netloc.lower()
                if any(d in domain for d in DIRECTORY_DOMAINS):
                    continue
                clean_name = re.sub(r"[^a-z0-9]", "",
                                     business_name.lower())
                clean_dom = re.sub(r"[^a-z0-9]", "", domain)
                ratio = SequenceMatcher(None, clean_name, clean_dom).ratio()
                if ratio > 0.4 or clean_name[:6] in clean_dom:
                    return f"{urlparse(href).scheme}://{domain}"
            return None
        except Exception as e:
            logger.warning("Website fallback error: %s", e)
            return None

    # ── Etapa 3: Análisis del sitio ───────────────────────────────────────

    def analyze_site(self, url: str) -> dict:
        """Analiza el sitio devolviendo métricas, issues y score."""
        result = {"site_score": 0, "site_issues": [], "html": "", "base_url": url}
        try:
            t0 = time.time()
            resp = requests.get(url, headers=HTTP_HEADERS,
                                timeout=10, allow_redirects=True)
            load_ms = int((time.time() - t0) * 1000)
            html = resp.text or ""
        except requests.RequestException as e:
            result["site_issues"] = [f"sitio inaccesible ({type(e).__name__})"]
            return result

        result["html"] = html
        soup = BeautifulSoup(html, "lxml")
        issues: list[str] = []

        if not url.startswith("https://"):
            issues.append("no usa HTTPS (sin certificado SSL)")
        if load_ms > 4000:
            issues.append(f"carga muy lenta ({load_ms}ms)")
        if not soup.find("meta", attrs={"name": "viewport"}):
            issues.append("no es mobile-friendly (sin viewport)")

        scripts_text = " ".join(s.get("src", "") + (s.string or "")
                                 for s in soup.find_all("script"))
        has_analytics = any(k in scripts_text.lower()
                            for k in ["google-analytics", "gtag", "googletagmanager",
                                      "fbq(", "facebook.net/", "fbevents"])
        if not has_analytics:
            issues.append("sin analytics ni pixel de seguimiento")

        has_chat = any(k in html.lower()
                       for k in ["tidio", "intercom", "wa.me/", "whatsapp.com/send"])
        if not has_chat:
            issues.append("sin chat ni botón de WhatsApp")

        has_blog = any(a.get("href", "").lower().rstrip("/").endswith(
            ("/blog", "/noticias", "/articulos"))
            for a in soup.find_all("a", href=True))

        m = re.search(r"©\s*(\d{4})", html)
        if m:
            year = int(m.group(1))
            if year < datetime.now().year - 1:
                issues.append(f"footer desactualizado (©{year})")

        old_tech = False
        if re.search(r"jquery[/-](1\.|2\.0)", scripts_text, re.I):
            old_tech = True
            issues.append("usa jQuery viejo (1.x/2.0)")
        if re.search(r"bootstrap[/-]3\.", scripts_text, re.I):
            old_tech = True
            issues.append("usa Bootstrap 3 (deprecado)")
        if len(soup.find_all("table")) > 3 and not soup.find("nav"):
            old_tech = True
            issues.append("layout con tablas (HTML antiguo)")

        has_email_form = any(
            f.find("input", attrs={"type": "email"})
            for f in soup.find_all("form")
        )
        if not has_email_form:
            issues.append("sin formulario de contacto con email")

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        if len(title) < 10:
            issues.append("title tag pobre o vacío")

        # Score: parte de 100, restamos por cada issue
        score = 100 - len(issues) * 12
        if load_ms > 6000:
            score -= 10
        score = max(0, min(100, score))

        result.update({
            "site_score": score,
            "site_issues": issues,
            "load_time_ms": load_ms,
            "has_ssl": url.startswith("https://"),
            "has_analytics": has_analytics,
            "has_blog": has_blog,
            "uses_old_tech": old_tech,
        })
        return result

    # ── Etapa 4: Extracción de email ──────────────────────────────────────

    def extract_email(self, base_url: str, base_html: str = "") -> str | None:
        """Busca emails en homepage + páginas de contacto."""
        candidates: list[str] = []

        def scan(html: str) -> None:
            for m in EMAIL_REGEX.findall(html or ""):
                low = m.lower()
                if any(b in low for b in EMAIL_BLACKLIST):
                    continue
                if low not in candidates:
                    candidates.append(low)

        scan(base_html)
        for path in CONTACT_PATHS:
            if candidates:
                break
            try:
                url = urljoin(base_url, path)
                r = requests.get(url, headers=HTTP_HEADERS, timeout=10)
                if r.status_code == 200:
                    scan(r.text)
            except requests.RequestException:
                continue

        return candidates[0] if candidates else None

    # ── Etapa 5: Scoring ──────────────────────────────────────────────────

    def score_lead(self, has_website: bool, site_score: int,
                   phone: str, rating: float, reviews: int,
                   email: str | None) -> int:
        """Score 0-100 según fórmula del spec."""
        s = 0
        if not has_website:
            s += 30
        if has_website and site_score < 50:
            s += 25
        if has_website and site_score < 30:
            s += 40
        if phone:
            s += 15
        if rating and rating > 4.0:
            s += 10
        if reviews and reviews > 20:
            s += 10
        if email:
            s += 15
        return s

    # ── Etapa 6: Generación de mail con Haiku ─────────────────────────────

    def generate_email(self, lead: dict) -> dict:
        """Genera subject + body via Haiku. Devuelve {} si falla."""
        prompt = (
            f"Idioma: {lead.get('lang', 'es')}\n"
            f"Negocio: {lead['business_name']}, {lead.get('sector', '')}, "
            f"{lead.get('city', '')}, {lead.get('country', '')}\n"
            f"Problemas detectados: {', '.join(lead.get('site_issues', []))}\n"
            f"Rating Google: {lead.get('rating', 'N/A')}/5 "
            f"({lead.get('reviews', 0)} reseñas)\n\n"
            "Escribí un cold email que:\n"
            "- Asunto: mencione UN problema específico, máx 8 palabras\n"
            "- Cuerpo: máx 5 líneas\n"
            "- Mencione UN problema concreto detectado\n"
            "- Proponga UNA solución concreta\n"
            "- Termine con UNA pregunta abierta\n"
            "- Tono directo, humano, sin presión\n"
            "- NO uses: garantizado, gratis, oferta, urgente, increíble, "
            "revolucionario\n"
            "- NO menciones Uruguay ni Latinoamérica\n"
            "- Firma exacta: 'Anto — PulsarMoon (pulsarmoon.com)'\n"
            "- Sin HTML, sin emojis, solo texto plano\n\n"
            'Respondé SOLO con: {"subject":"...","body":"..."}'
        )
        data = self.call_llm_json(prompt, max_tokens=600)
        if not isinstance(data, dict) or "subject" not in data or "body" not in data:
            return {}
        return {"subject": data["subject"].strip(),
                "body": data["body"].strip()}

    # ── Procesamiento de un negocio individual ────────────────────────────

    def process_business(self, place: dict, niche: str,
                         city_info: dict) -> dict | None:
        """Procesa un negocio. Devuelve dict del lead guardado o None."""
        name = (place.get("name") or "").strip()
        city = city_info["city"]
        if not name or lead_exists(name, city):
            return None

        details = self.get_place_details(place.get("place_id", "")) or {}
        time.sleep(1)  # rate limit

        phone = details.get("formatted_phone_number") or \
                place.get("formatted_phone_number", "")
        rating = details.get("rating") or place.get("rating", 0) or 0
        reviews = details.get("user_ratings_total") or \
                   place.get("user_ratings_total", 0) or 0
        website = details.get("website") or ""

        # Etapa 2: fallback de website
        if not website:
            website = self.find_website_fallback(name, city) or ""

        site_score = 0
        site_issues: list[str] = []
        email: str | None = None

        if website:
            analysis = self.analyze_site(website)
            site_score = analysis["site_score"]
            site_issues = analysis["site_issues"]
            # Filtro: sitio demasiado bueno -> descartar
            if len(site_issues) < 2 and site_score > 75:
                logger.info("Descartado %s: sitio demasiado bueno", name)
                return None
            email = self.extract_email(analysis.get("base_url", website),
                                        analysis.get("html", ""))
        else:
            site_issues = ["no tiene sitio web"]

        score = self.score_lead(bool(website), site_score, phone,
                                 rating, reviews, email)
        if score < 40:
            logger.info("Descartado %s: score=%d", name, score)
            return None

        has_email = bool(email)
        subject = body = ""
        lead_data = {
            "business_name": name, "phone": phone, "sector": niche,
            "city": city, "country": city_info["country"],
            "lang": city_info["lang"], "website": website or None,
            "email": email, "has_email": has_email,
            "site_score": site_score, "site_issues": site_issues,
            "rating": rating, "reviews": reviews, "score": score,
        }

        if has_email and score >= 40:
            try:
                gen = self.generate_email(lead_data)
                subject = gen.get("subject", "")
                body = gen.get("body", "")
            except Exception as e:
                logger.warning("Error generando email para %s: %s", name, e)

        # Insertar en DB
        notes_payload = json.dumps({
            "subject": subject, "body": body,
            "address": details.get("formatted_address", ""),
        }, ensure_ascii=False)
        try:
            row = get_db().fetchone(
                """INSERT INTO leads
                   (business_name, phone, sector, city, country, source, notes,
                    score, status, email, website, has_email, site_issues,
                    site_score, lang, email_subject, email_body)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                           %s::jsonb, %s, %s, %s, %s)
                   RETURNING *""",
                (name, phone, niche, city, city_info["country"],
                 "google_places_intl", notes_payload, score,
                 "pending_approval", email, website or None, has_email,
                 json.dumps(site_issues, ensure_ascii=False),
                 site_score, city_info["lang"], subject, body)
            )
            self.log("lead_processed", {
                "name": name, "city": city, "score": score,
                "has_email": has_email, "site_score": site_score,
            })
            return row
        except Exception as e:
            logger.error("Error guardando lead %s: %s", name, e)
            return None

    # ── Pipeline diario ───────────────────────────────────────────────────

    def run_daily(self) -> dict:
        """Pipeline completo: busca + analiza + guarda + notifica."""
        niche, city_info = self.get_today_target()
        city = city_info["city"]
        self.write_event("working", f"{niche} en {city}")
        logger.info("Pipeline diario: %s en %s", niche, city)

        try:
            places = self.search_places(niche, city, city_info["lang"])
            saved: list[dict] = []
            for place in places:
                try:
                    lead = self.process_business(place, niche, city_info)
                    if lead:
                        saved.append(lead)
                except Exception as e:
                    logger.error("Error procesando %s: %s",
                                 place.get("name", "?"), e)

            con_email = sum(1 for l in saved if l.get("has_email"))
            sin_email = len(saved) - con_email

            top3 = sorted(saved, key=lambda l: l.get("score", 0),
                          reverse=True)[:3]
            top3_lines = []
            for l in top3:
                issues = l.get("site_issues") or []
                problem = issues[0] if issues else "sin web"
                top3_lines.append(f"• {l['business_name']} — {problem}")

            msg = (
                f"🔍 Prospector terminó\n"
                f"📍 {city} — {niche}\n"
                f"✅ {len(saved)} leads nuevos\n"
                f"📧 {con_email} con email listos para aprobar\n"
                f"📵 {sin_email} sin email (contacto manual)\n\n"
                f"Top 3:\n" + ("\n".join(top3_lines) if top3_lines else "—") +
                "\n\nPanel: https://office.vydre.me"
            )
            try:
                self.send_whatsapp("59891722750", msg)
            except Exception as e:
                logger.warning("WhatsApp notify error: %s", e)

            self.write_event("done", f"{len(saved)} leads en {city}")
            return {"total": len(saved), "con_email": con_email,
                    "sin_email": sin_email, "city": city, "niche": niche}
        except Exception as e:
            self.write_event("error", str(e)[:120])
            logger.exception("Pipeline diario falló")
            try:
                self.send_whatsapp("59891722750",
                                    f"❌ Email Prospector falló: {e}")
            except Exception:
                pass
            return {"total": 0, "error": str(e)}

    # ── Envío de mail (llamado desde panel) ───────────────────────────────

    def emails_sent_today(self) -> int:
        """Cuenta emails enviados hoy (UTC)."""
        try:
            row = get_db().fetchone(
                """SELECT COUNT(*) AS c FROM leads
                   WHERE email_sent = TRUE
                     AND email_sent_at::date = CURRENT_DATE"""
            )
            return int(row["c"]) if row else 0
        except Exception as e:
            logger.error("Error contando emails: %s", e)
            return DAILY_EMAIL_LIMIT  # safe-fail

    def send_email(self, lead_id: int) -> bool:
        """Envía email SMTP via spacemail. Respeta límite diario."""
        if not self.smtp_user or not self.smtp_pass:
            logger.error("SMTP_USER/SMTP_PASS no configurados")
            return False

        if self.emails_sent_today() >= DAILY_EMAIL_LIMIT:
            logger.warning("Límite diario de %d emails alcanzado",
                            DAILY_EMAIL_LIMIT)
            return False

        lead = get_db().fetchone("SELECT * FROM leads WHERE id = %s",
                                  (lead_id,))
        if not lead:
            logger.error("Lead %s no encontrado", lead_id)
            return False
        if not lead.get("email"):
            logger.error("Lead %s sin email", lead_id)
            return False
        if lead.get("email_sent"):
            logger.warning("Lead %s ya tiene email enviado", lead_id)
            return False

        subject = lead.get("email_subject") or ""
        body = lead.get("email_body") or ""
        if not subject or not body:
            logger.error("Lead %s sin subject/body generado", lead_id)
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = f"PulsarMoon <{self.smtp_user}>"
            msg["To"] = lead["email"]
            msg["Subject"] = subject
            msg["List-Unsubscribe"] = (
                "<mailto:contacto@pulsarmoon.com?subject=unsubscribe>"
            )
            msg["X-Mailer"] = "PulsarMoon-Prospector/1.0"
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP("smtp.spacemail.com", 587, timeout=20) as s:
                s.starttls()
                s.login(self.smtp_user, self.smtp_pass)
                s.send_message(msg)

            get_db().execute(
                """UPDATE leads
                   SET email_sent = TRUE, email_sent_at = NOW(),
                       status = 'contacted', updated_at = NOW()
                   WHERE id = %s""", (lead_id,)
            )
            self.log("email_sent", {"lead_id": lead_id, "to": lead["email"]})
            return True
        except Exception as e:
            logger.error("Error SMTP enviando a lead %s: %s", lead_id, e)
            self.log("email_error", {"lead_id": lead_id, "error": str(e)})
            return False


# Instancia global lazy
_agent: EmailProspectorAgent | None = None


def get_agent() -> EmailProspectorAgent:
    global _agent
    if _agent is None:
        _agent = EmailProspectorAgent()
    return _agent


def run_daily() -> dict:
    return get_agent().run_daily()
