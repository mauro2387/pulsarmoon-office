"""
Agente de Presupuestos de PulsarMoon.
Calcula presupuestos (Python puro), genera descripción (Sonnet),
genera PDF (reportlab). NADA sale al cliente sin aprobación humana.
"""
import json
import logging
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.base_agent import BaseAgent
from agents.presupuestos.prices import (
    CONDITIONS, DISCOUNT_PERCENT, DISCOUNT_THRESHOLD, PRICES,
)
from db.database import get_db
from db.leads import get_lead

logger = logging.getLogger(__name__)


class BudgetAgent(BaseAgent):
    """Genera presupuestos profesionales con aprobación humana."""

    def __init__(self):
        super().__init__(
            agent_id="budget-01",
            agent_name="Presupuestador",
            department="oportunidades",
            model="sonnet",
            company_id="pulsarmoon",
        )

    # ── Cálculo Python puro, sin LLM ──

    def calculate_budget(self, services: list[str],
                         client_name: str) -> dict:
        """Calcula totales desde prices.py. Sin LLM."""
        items = []
        for svc_key in services:
            svc = PRICES.get(svc_key)
            if not svc:
                logger.warning("Servicio desconocido: %s", svc_key)
                continue
            items.append({
                "key": svc_key,
                "name": svc["name"],
                "setup_uyu": svc["setup_uyu"],
                "setup_label": svc["setup_label"],
                "monthly_uyu": svc["monthly_uyu"],
                "desc": svc["desc"],
            })

        subtotal_setup = sum(i["setup_uyu"] for i in items)
        total_monthly = sum(i["monthly_uyu"] for i in items)

        # Descuento por múltiples servicios
        discount_pct = DISCOUNT_PERCENT if len(items) >= DISCOUNT_THRESHOLD else 0
        discount_amt = int(subtotal_setup * discount_pct / 100)
        total_setup = subtotal_setup - discount_amt

        now = datetime.now()
        return {
            "client_name": client_name,
            "items": items,
            "subtotal_setup": subtotal_setup,
            "discount_percent": discount_pct,
            "discount_amount": discount_amt,
            "total_setup": total_setup,
            "total_monthly": total_monthly,
            "conditions": CONDITIONS,
            "date": now.strftime("%d/%m/%Y"),
            "valid_until": (now + timedelta(days=15)).strftime("%d/%m/%Y"),
        }

    # ── Descripción personalizada, 1 llamada Sonnet ──

    def generate_description(self, client_name: str,
                             services_names: list[str],
                             notes: str = "") -> str:
        """Genera descripción profesional con Sonnet."""
        svc_list = ", ".join(services_names)
        prompt = (
            f"Redactá una descripción profesional y personalizada para "
            f"un presupuesto de PulsarMoon dirigido a {client_name}. "
            f"Servicios incluidos: {svc_list}. "
            f"Notas adicionales: {notes or 'ninguna'}. "
            f"Máximo 120 palabras. Tono formal y cercano. En español."
        )
        desc = self.call_llm(prompt, max_tokens=300)
        return desc or f"Presupuesto para {client_name} — {svc_list}."

    # ── Generador PDF, sin LLM ──

    def generate_pdf(self, budget_data: dict, description: str) -> str:
        """Genera PDF profesional con reportlab. Sin LLM."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )

        # Sanitizar nombre para filename
        safe_name = re.sub(r"[^\w\-]", "_", budget_data["client_name"])
        date_str = datetime.now().strftime("%Y%m%d")
        pdf_dir = Path(tempfile.gettempdir()) / "pulsarmoon_budgets"
        pdf_dir.mkdir(exist_ok=True)
        pdf_path = str(pdf_dir / f"presupuesto_{safe_name}_{date_str}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        elements = []

        # Colores corporativos
        blue = colors.HexColor("#1a237e")
        gray = colors.HexColor("#666666")
        light_bg = colors.HexColor("#f5f5f5")

        # ── Header ──
        h_style = ParagraphStyle("Header", fontSize=24, textColor=blue,
                                 fontName="Helvetica-Bold", spaceAfter=4)
        sub_style = ParagraphStyle("Sub", fontSize=10, textColor=gray,
                                   spaceAfter=2)
        elements.append(Paragraph("PulsarMoon", h_style))
        elements.append(Paragraph(
            "Desarrollo Web · Sistemas · Marketing Digital", sub_style))
        elements.append(Paragraph(
            "Punta del Este, Uruguay | pulsarmoon.com | +598 91 722 750",
            sub_style))
        elements.append(Spacer(1, 0.5*cm))

        # ── Título + datos ──
        title_style = ParagraphStyle("Title", fontSize=18, textColor=blue,
                                     fontName="Helvetica-Bold", spaceAfter=8)
        elements.append(Paragraph("PRESUPUESTO", title_style))
        info_style = ParagraphStyle("Info", fontSize=11, spaceAfter=4)
        elements.append(Paragraph(
            f"<b>Cliente:</b> {budget_data['client_name']}", info_style))
        elements.append(Paragraph(
            f"<b>Fecha:</b> {budget_data['date']}", info_style))
        elements.append(Paragraph(
            f"<b>Válido hasta:</b> {budget_data['valid_until']}", info_style))
        elements.append(Spacer(1, 0.4*cm))

        # ── Descripción ──
        desc_style = ParagraphStyle("Desc", fontSize=10, leading=14,
                                    spaceAfter=12)
        elements.append(Paragraph(description, desc_style))
        elements.append(Spacer(1, 0.3*cm))

        # ── Tabla de servicios ──
        header = ["Servicio", "Setup", "Mensual"]
        data = [header]
        for item in budget_data["items"]:
            setup = item["setup_label"]
            monthly = f"${item['monthly_uyu']:,}/mes" if item["monthly_uyu"] else "—"
            data.append([item["name"], setup, monthly])

        if budget_data["discount_percent"]:
            data.append([
                f"Descuento {budget_data['discount_percent']}%",
                f"-${budget_data['discount_amount']:,}", ""])

        data.append([
            "TOTAL",
            f"${budget_data['total_setup']:,}",
            f"${budget_data['total_monthly']:,}/mes"
                if budget_data["total_monthly"] else "—"])

        table = Table(data, colWidths=[9*cm, 4*cm, 4*cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), blue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, -1), (-1, -1), light_bg),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))

        # ── Condiciones ──
        cond_title = ParagraphStyle("CondT", fontSize=12, textColor=blue,
                                    fontName="Helvetica-Bold", spaceAfter=6)
        cond_style = ParagraphStyle("Cond", fontSize=9, leading=13,
                                    leftIndent=10)
        elements.append(Paragraph("Condiciones", cond_title))
        for val in budget_data["conditions"].values():
            elements.append(Paragraph(f"• {val}", cond_style))
        elements.append(Spacer(1, 1*cm))

        # ── Footer ──
        foot_style = ParagraphStyle("Foot", fontSize=8, textColor=gray,
                                    alignment=1)
        elements.append(Paragraph(
            "Este presupuesto fue generado por PulsarMoon", foot_style))
        elements.append(Paragraph(
            "Para aceptar o consultar: +598 91 722 750 | pulsarmoon.com",
            foot_style))

        doc.build(elements)
        logger.info("PDF generado: %s", pdf_path)
        return pdf_path

    # ── Pipeline completo ──

    def create_budget(self, lead_id: int, services: list[str],
                      notes: str = "") -> dict:
        """Crea presupuesto completo. NO envía nada sin aprobación."""
        self.write_event("working", "Generando presupuesto...")

        lead = get_lead(lead_id)
        if not lead:
            self.write_event("error", "Lead no encontrado")
            return {"error": "Lead no encontrado"}

        client_name = lead["business_name"]
        budget_data = self.calculate_budget(services, client_name)
        svc_names = [i["name"] for i in budget_data["items"]]
        description = self.generate_description(client_name, svc_names, notes)
        pdf_path = self.generate_pdf(budget_data, description)

        # Guardar en PostgreSQL
        db = get_db()
        row = db.fetchone(
            "INSERT INTO budgets "
            "(lead_id, client_name, services, total_setup, total_monthly, "
            "pdf_path, description, notes) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *",
            (lead_id, client_name, json.dumps(services),
             budget_data["total_setup"], budget_data["total_monthly"],
             pdf_path, description, notes))

        self.write_event("waiting", "Presupuesto listo — esperando aprobación")
        self.log("budget_created", {
            "lead": client_name,
            "total_setup": budget_data["total_setup"],
            "total_monthly": budget_data["total_monthly"],
        })

        return {
            "budget_id": row["id"] if row else None,
            "pdf_path": pdf_path,
            "budget_data": budget_data,
            "description": description,
            "status": "pending_approval",
        }


# Instancia global
_agent = BudgetAgent()
