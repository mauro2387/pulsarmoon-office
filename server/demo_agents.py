"""
Simulador de actividad de agentes demo para Fase 1.
Escribe eventos JSON periódicos en agents/events/ para que la oficina se vea viva.
"""
import asyncio
import json
import logging
import os
import random
import time
from pathlib import Path

logger = logging.getLogger(__name__)

DEMO_AGENTS = [
    {"agent_id": "dir-01",  "agent_name": "Director",   "department": "direccion"},
    {"agent_id": "dev-01",  "agent_name": "Arquitecto",  "department": "desarrollo"},
    {"agent_id": "dev-02",  "agent_name": "Desarrollador", "department": "desarrollo"},
    {"agent_id": "ux-01",   "agent_name": "Diseñador",   "department": "ux_ui"},
    {"agent_id": "qa-01",   "agent_name": "Tester",      "department": "qa"},
    {"agent_id": "mkt-01",  "agent_name": "Copywriter",  "department": "marketing"},
    {"agent_id": "cli-01",  "agent_name": "Soporte",     "department": "atencion"},
    {"agent_id": "opp-01",  "agent_name": "Prospector",  "department": "oportunidades"},
    {"agent_id": "adm-01",  "agent_name": "Admin",       "department": "administrativo"},
]

TASKS_BY_DEPT: dict[str, list[str]] = {
    "direccion":      [
        "Revisando métricas del mes",
        "Planificando sprint",
        "Coordinando equipo",
        "Revisando propuestas estratégicas",
        "Preparando presentación para inversores",
    ],
    "desarrollo":     [
        "Codificando API REST",
        "Revisando pull requests",
        "Refactorizando módulo de autenticación",
        "Solucionando bug crítico en producción",
        "Diseñando arquitectura de base de datos",
        "Integrando WebSocket server",
    ],
    "ux_ui":          [
        "Diseñando wireframes",
        "Creando mockups en Figma",
        "Revisando flujo de usuario",
        "Actualizando design system",
        "Prototipando nueva funcionalidad",
    ],
    "qa":             [
        "Ejecutando suite de tests",
        "Reportando bugs en Jira",
        "Automatizando casos de prueba",
        "Revisando regresiones del sprint",
        "Validando criterios de aceptación",
    ],
    "marketing":      [
        "Redactando copy para web",
        "Analizando métricas SEO",
        "Creando contenido para blog",
        "Planificando campaña de lanzamiento",
        "Revisando analytics de redes sociales",
    ],
    "atencion":       [
        "Respondiendo consultas de clientes",
        "Procesando tickets pendientes",
        "Actualizando base de conocimientos",
        "Siguiendo casos abiertos",
        "Escalando incidencia crítica",
    ],
    "oportunidades":  [
        "Investigando leads en LinkedIn",
        "Analizando mercado uruguayo",
        "Prospectando vía email",
        "Preparando propuesta comercial",
        "Calificando oportunidades del pipeline",
    ],
    "administrativo": [
        "Generando reporte semanal",
        "Actualizando KPIs del mes",
        "Archivando documentación contractual",
        "Preparando facturación de clientes",
        "Coordinando reunión de directorio",
    ],
}

# Probabilidades de estado: working 55%, idle 30%, waiting 10%, error 5%
STATUS_WEIGHTS = [0.55, 0.30, 0.10, 0.05]
STATUS_VALUES  = ["working", "idle", "waiting", "error"]


async def run_demo_agents(events_dir: str) -> None:
    """Escribe eventos periódicos para simular actividad de agentes."""
    os.makedirs(events_dir, exist_ok=True)
    logger.info(f"Demo agents iniciados — escribiendo en: {events_dir}")

    # Pequeño stagger inicial para que los agentes no arrangen todos igual
    await asyncio.sleep(0.5)

    while True:
        for agent in DEMO_AGENTS:
            try:
                status = random.choices(STATUS_VALUES, weights=STATUS_WEIGHTS)[0]
                dept = agent["department"]

                event: dict = {
                    **agent,
                    "status":    status,
                    "task":      random.choice(TASKS_BY_DEPT[dept]) if status == "working" else "",
                    "model":     "demo",
                    "timestamp": int(time.time()),
                    "metadata":  {},
                }

                _write_event_atomic(events_dir, agent["agent_id"], event)

            except Exception as e:
                logger.error(f"Error escribiendo evento demo para {agent['agent_id']}: {e}")

            # Pequeña pausa entre agentes para no saturar el watcher
            await asyncio.sleep(0.05)

        # Esperar intervalo aleatorio antes del próximo ciclo
        interval = random.uniform(3.0, 8.0)
        await asyncio.sleep(interval)


def _write_event_atomic(events_dir: str, agent_id: str, event: dict) -> None:
    """
    Escribe un evento JSON de forma atómica.
    Escribe a .tmp y luego os.replace() — evita lecturas parciales por el watcher.
    """
    filepath = os.path.join(events_dir, f"{agent_id}.json")
    tmp_path  = filepath + ".tmp"

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(event, f, ensure_ascii=False, indent=2)

    os.replace(tmp_path, filepath)
