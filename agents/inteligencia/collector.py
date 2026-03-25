"""
Colector de señales de mercado — Python puro, CERO llamadas a LLM.
Fuentes: Google Trends UY, RSS/noticias, MercadoLibre, scraping.
"""
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup
from pytrends.request import TrendReq

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.database import get_db

logger = logging.getLogger(__name__)

# Categorías de Google Trends relevantes para negocios
_TREND_CATEGORIES = {
    12: "Business & Industrial",
    784: "Real Estate",
    533: "Health",
    122: "Food & Drink",
    179: "Travel & Tourism",
    67: "Beauty & Fitness",
    958: "Restaurants",
}

# Feeds RSS + Google News Uruguay
_RSS_FEEDS = {
    "El Observador Economía": "https://www.elobservador.com.uy/rss/economia-y-empresas.xml",
    "El Observador Negocios": "https://www.elobservador.com.uy/rss/cafe-y-negocios.xml",
    "Montevideo Portal": "https://www.montevideo.com.uy/anxml.aspx?728",
    "Google News Negocios UY": "https://news.google.com/rss/search?q=negocios+Uruguay&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News PDE": "https://news.google.com/rss/search?q=empresas+Punta+del+Este&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News Maldonado": "https://news.google.com/rss/search?q=nuevo+negocio+Maldonado&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News Comercio": "https://news.google.com/rss/search?q=apertura+comercio+Uruguay&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News Emprendimientos": "https://news.google.com/rss/search?q=emprendimiento+Uruguay+2026&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News Inversión": "https://news.google.com/rss/search?q=inversion+empresa+Uruguay&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News Restaurants": "https://news.google.com/rss/search?q=abre+restaurant+Punta+del+Este&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News Clínicas": "https://news.google.com/rss/search?q=clinica+privada+Uruguay&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News Hoteles": "https://news.google.com/rss/search?q=hotel+Punta+del+Este&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News Inmobiliarias": "https://news.google.com/rss/search?q=inmobiliaria+Maldonado&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News Tech UY": "https://news.google.com/rss/search?q=tecnologia+empresas+Uruguay&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News Startups": "https://news.google.com/rss/search?q=startup+Uruguay&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News Turismo": "https://news.google.com/rss/search?q=turismo+Uruguay+temporada&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News E-commerce": "https://news.google.com/rss/search?q=comercio+electronico+Uruguay&hl=es-419&gl=UY&ceid=UY:es-419",
    "Google News Gastronomía": "https://news.google.com/rss/search?q=gastronomia+Punta+del+Este&hl=es-419&gl=UY&ceid=UY:es-419",
}

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PulsarMoon/1.0)"}


def collect_google_trends() -> list[dict]:
    """Recolecta trending searches de Uruguay. Sin LLM."""
    signals = []

    # 1. Top 100 trending searches generales Uruguay
    try:
        pt = TrendReq(hl="es-419", tz=180)
        trending = pt.trending_searches(pn="uruguay")
        for _, row in trending.head(100).iterrows():
            signals.append({
                "source": "trends_trending",
                "title": str(row[0]),
                "content": "trending search uruguay",
            })
    except Exception as e:
        logger.warning("Error trending searches: %s", e)

    # 2. Búsquedas relacionadas a nuestros sectores objetivo
    SECTOR_KEYWORDS = [
        "restaurante", "clinica", "hotel", "gimnasio",
        "inmobiliaria", "spa", "odontologia", "farmacia",
        "arquitecto", "contador", "abogado", "veterinaria"
    ]
    try:
        pt = TrendReq(hl="es-419", tz=180)
        # pytrends acepta hasta 5 keywords por llamada
        for i in range(0, len(SECTOR_KEYWORDS), 5):
            batch = SECTOR_KEYWORDS[i:i+5]
            try:
                pt.build_payload(kw_list=batch, timeframe="now 7-d",
                                 geo="UY")
                related = pt.related_queries()
                for kw, kw_data in related.items():
                    if (kw_data and "top" in kw_data
                            and kw_data["top"] is not None):
                        for _, row in kw_data["top"].head(10).iterrows():
                            query = str(
                                row.get("query", "")).strip()
                            if query:
                                signals.append({
                                    "source": f"trends_sector_{kw}",
                                    "title": query,
                                    "content": str(
                                        row.get("value", "")),
                                })
            except Exception as e:
                logger.warning("Error sector trends %s: %s",
                               batch, e)
            import time
            time.sleep(2)  # Evitar rate limiting de Google
    except Exception as e:
        logger.warning("Error sector keywords trends: %s", e)

    logger.info("Google Trends: %d señales", len(signals))
    return signals


def collect_rss_feeds() -> list[dict]:
    """Recolecta noticias de RSS + scraping. Sin LLM."""
    signals = []

    # RSS feeds estándar
    for name, url in _RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                title = entry.get("title", "").strip()
                if not title:
                    continue
                signals.append({
                    "source": name,
                    "title": title,
                    "url": entry.get("link", ""),
                    "content": entry.get("summary", "")[:300],
                })
        except Exception as e:
            logger.warning("Error feed %s: %s", name, e)

    # Scraping InfoNegocios
    signals.extend(_scrape_infonegocios())
    # Scraping Uruguay XXI
    signals.extend(_scrape_uruguayxxi())

    logger.info("RSS/scraping: %d señales", len(signals))
    return signals


def _scrape_infonegocios() -> list[dict]:
    """Extrae títulos de InfoNegocios. Sin LLM."""
    results = []
    try:
        resp = requests.get("https://infonegocios.biz/",
                            headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup.find_all(["h2", "h3"])[:20]:
            text = tag.get_text(strip=True)
            if len(text) > 10:
                results.append({
                    "source": "InfoNegocios",
                    "title": text,
                    "url": "https://infonegocios.biz/",
                    "content": "",
                })
    except Exception as e:
        logger.warning("Error scraping InfoNegocios: %s", e)
    return results


def _scrape_uruguayxxi() -> list[dict]:
    """Extrae títulos de Uruguay XXI noticias. Sin LLM."""
    results = []
    try:
        resp = requests.get("https://www.uruguayxxi.gub.uy/es/noticias/",
                            headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup.find_all(["h2", "h3", "h4"])[:15]:
            text = tag.get_text(strip=True)
            if len(text) > 10:
                results.append({
                    "source": "Uruguay XXI",
                    "title": text,
                    "url": "https://www.uruguayxxi.gub.uy/es/noticias/",
                    "content": "",
                })
    except Exception as e:
        logger.warning("Error scraping Uruguay XXI: %s", e)
    return results


def collect_impo_signals() -> list[dict]:
    """Detecta empresas nuevas en el Diario Oficial (IMPO). Sin LLM."""
    signals = []
    KEYWORDS = ["S.R.L", "S.A.S", " S.A.", "sociedad",
                "se constituye", "constitución", "objeto social"]

    urls_to_try = [
        "https://www.impo.com.uy/diariooficial/avisos?json=true",
        "https://www.impo.com.uy/bases/aviso?json=true",
    ]

    headers = {"User-Agent": "Mozilla/5.0 (compatible; PulsarMoon/1.0)"}

    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue

            try:
                data = resp.json()
                items = (data if isinstance(data, list)
                         else data.get("avisos", data.get("items", [])))
                for item in items[:50]:
                    title = str(item.get(
                        "titulo", item.get("title", ""))).strip()
                    content = str(item.get(
                        "contenido", item.get("content", ""))).strip()
                    combined = (title + " " + content).upper()
                    if any(kw.upper() in combined for kw in KEYWORDS):
                        signals.append({
                            "source": "impo_empresas_nuevas",
                            "title": title[:200],
                            "url": item.get(
                                "url", "https://www.impo.com.uy"),
                            "content": content[:300],
                        })
                if signals:
                    break
            except Exception:
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup.find_all(["h2", "h3", "p"])[:50]:
                    text = tag.get_text(strip=True)
                    if any(kw.upper() in text.upper()
                           for kw in KEYWORDS):
                        signals.append({
                            "source": "impo_empresas_nuevas",
                            "title": text[:200],
                            "url": url,
                            "content": "",
                        })
        except Exception as e:
            logger.warning("Error IMPO %s: %s", url, e)

    logger.info("IMPO empresas nuevas: %d señales", len(signals))
    return signals


def save_raw_signals(signals: list[dict]) -> int:
    """Guarda señales en raw_intelligence evitando duplicados. Sin LLM."""
    now = datetime.now()
    week = now.isocalendar()[1]
    year = now.year
    saved = 0
    db = get_db()

    for s in signals:
        title = s.get("title", "").strip()
        if not title:
            continue
        try:
            # Evitar duplicados por title + semana
            existing = db.fetchone(
                "SELECT id FROM raw_intelligence "
                "WHERE title = %s AND week_number = %s AND year = %s",
                (title, week, year))
            if existing:
                continue
            db.execute(
                "INSERT INTO raw_intelligence "
                "(source, title, url, content, week_number, year) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (s.get("source", ""), title,
                 s.get("url", ""), s.get("content", ""),
                 week, year))
            saved += 1
        except Exception as e:
            logger.warning("Error guardando señal '%s': %s", title[:30], e)

    logger.info("Guardadas %d/%d señales (semana %d/%d)",
                saved, len(signals), week, year)
    return saved
