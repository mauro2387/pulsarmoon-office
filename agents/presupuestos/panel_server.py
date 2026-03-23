"""
Panel de aprobación de presupuestos — Flask en puerto 8769.
NADA sale al cliente sin aprobación humana desde este panel.
"""
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS
from dotenv import load_dotenv

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


def _json_response(data, status=200):
    """Respuesta JSON con soporte para datetime."""
    body = json.dumps(data, default=str, ensure_ascii=False)
    return Response(body, status=status, mimetype="application/json")


# ── HTML del panel ──
_PANEL_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<title>PulsarMoon — Presupuestos</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#0d1117;color:#e6edf3}
.top{background:#161b22;padding:16px 24px;border-bottom:1px solid #30363d}
.top h1{font-size:18px;color:#58a6ff}
.container{max-width:900px;margin:24px auto;padding:0 16px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:12px}
.card h3{color:#58a6ff;margin-bottom:8px;font-size:15px}
.card .meta{color:#8b949e;font-size:13px;margin-bottom:8px}
.card .totals{display:flex;gap:20px;margin:8px 0}
.card .totals span{font-size:14px;font-weight:600}
.card .totals .setup{color:#3fb950}
.card .totals .monthly{color:#d29922}
.btns{display:flex;gap:8px;margin-top:10px}
.btns button{padding:6px 14px;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600}
.btn-view{background:#1f6feb;color:#fff}
.btn-approve{background:#238636;color:#fff}
.btn-reject{background:#da3633;color:#fff}
.btn-edit{background:#30363d;color:#e6edf3;border:1px solid #484f58!important}
.empty{text-align:center;color:#8b949e;padding:40px;font-size:15px}
#create-form{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px}
#create-form h2{color:#58a6ff;font-size:16px;margin-bottom:12px}
#create-form label{display:block;color:#8b949e;font-size:13px;margin:8px 0 4px}
#create-form input,#create-form textarea,#create-form select{width:100%;padding:8px;
background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:6px;font-size:13px}
#create-form select{height:120px}
#create-form button{margin-top:12px;padding:8px 20px;background:#238636;color:#fff;
border:none;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer}
.status{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.status-pending{background:#d292221a;color:#d29922;border:1px solid #d29922}
.status-approved{background:#2386361a;color:#3fb950;border:1px solid #3fb950}
.status-rejected{background:#da36331a;color:#f85149;border:1px solid #f85149}
</style>
</head>
<body>
<div class="top"><h1>📋 PulsarMoon — Panel de Presupuestos</h1></div>
<div class="container">
<div id="create-form">
<h2>Crear Presupuesto</h2>
<label>Lead ID</label><input type="number" id="lead_id" placeholder="ID del lead">
<label>Servicios (Ctrl+click para seleccionar varios)</label>
<select id="services" multiple></select>
<label>Notas adicionales</label>
<textarea id="notes" rows="2" placeholder="Opcional..."></textarea>
<button onclick="createBudget()">Generar Presupuesto</button>
</div>
<div id="list"></div>
</div>
<script>
const API = location.origin;
const PRICES = %PRICES%;

// Llenar select de servicios
const sel = document.getElementById('services');
Object.entries(PRICES).forEach(([k,v]) => {
  const opt = document.createElement('option');
  opt.value = k;
  opt.textContent = `${v.name} — Setup: ${v.setup_label} | Mensual: $${v.monthly_uyu.toLocaleString()}/mes`;
  sel.appendChild(opt);
});

async function loadBudgets() {
  const res = await fetch(API + '/budgets');
  const data = await res.json();
  const list = document.getElementById('list');
  if (!data.length) { list.innerHTML = '<div class="empty">Sin presupuestos aún</div>'; return; }
  list.innerHTML = data.map(b => {
    const sc = b.status === 'approved' ? 'approved' : b.status === 'rejected' ? 'rejected' : 'pending';
    const svcs = JSON.parse(b.services || '[]').map(s => PRICES[s]?.name || s).join(', ');
    return `<div class="card">
      <h3>${b.client_name} <span class="status status-${sc}">${b.status}</span></h3>
      <div class="meta">ID: ${b.id} | ${svcs}</div>
      <div class="totals">
        <span class="setup">Setup: $${(b.total_setup||0).toLocaleString()}</span>
        <span class="monthly">Mensual: $${(b.total_monthly||0).toLocaleString()}/mes</span>
      </div>
      <div class="btns">
        <button class="btn-view" onclick="viewPdf(${b.id})">👁 Ver PDF</button>
        ${b.status==='pending_approval'?`
        <button class="btn-approve" onclick="approve(${b.id})">✅ Aprobar y Enviar</button>
        <button class="btn-reject" onclick="reject(${b.id})">❌ Rechazar</button>`:''}
      </div>
    </div>`;
  }).join('');
}

async function createBudget() {
  const lead_id = document.getElementById('lead_id').value;
  const sel = document.getElementById('services');
  const services = Array.from(sel.selectedOptions).map(o => o.value);
  const notes = document.getElementById('notes').value;
  if (!lead_id || !services.length) { alert('Completá lead ID y servicios'); return; }
  const res = await fetch(API + '/budgets/create', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({lead_id: parseInt(lead_id), services, notes})
  });
  const data = await res.json();
  if (data.error) { alert(data.error); return; }
  alert('Presupuesto creado — pendiente de aprobación');
  loadBudgets();
}

function viewPdf(id) { window.open(API + '/budgets/' + id + '/pdf', '_blank'); }

async function approve(id) {
  if (!confirm('¿Aprobar y enviar por WhatsApp?')) return;
  await fetch(API + '/budgets/' + id + '/approve', {method:'POST'});
  loadBudgets();
}

async function reject(id) {
  if (!confirm('¿Rechazar este presupuesto?')) return;
  await fetch(API + '/budgets/' + id + '/reject', {method:'POST'});
  loadBudgets();
}

loadBudgets();
</script>
</body>
</html>"""


@app.route("/")
def panel():
    """Panel HTML de aprobación de presupuestos."""
    from agents.presupuestos.prices import PRICES
    import json as _json
    html = _PANEL_HTML.replace("%PRICES%", _json.dumps(PRICES, ensure_ascii=False))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/budgets")
def list_budgets():
    """Lista todos los presupuestos."""
    from db.database import get_db
    rows = get_db().fetchall(
        "SELECT * FROM budgets ORDER BY created_at DESC")
    return _json_response(rows)


@app.route("/budgets/<int:budget_id>")
def get_budget(budget_id: int):
    """Detalle de un presupuesto."""
    from db.database import get_db
    row = get_db().fetchone("SELECT * FROM budgets WHERE id = %s",
                            (budget_id,))
    if not row:
        return jsonify({"error": "No encontrado"}), 404
    return _json_response(row)


@app.route("/budgets/<int:budget_id>/pdf")
def get_pdf(budget_id: int):
    """Sirve el PDF para preview."""
    from db.database import get_db
    row = get_db().fetchone("SELECT pdf_path FROM budgets WHERE id = %s",
                            (budget_id,))
    if not row or not row.get("pdf_path"):
        return jsonify({"error": "PDF no encontrado"}), 404
    path = row["pdf_path"]
    if not Path(path).exists():
        return jsonify({"error": "Archivo no existe"}), 404
    return send_file(path, mimetype="application/pdf")


@app.route("/budgets/create", methods=["POST"])
def create_budget():
    """Crea presupuesto — queda en pending_approval."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON requerido"}), 400
    lead_id = data.get("lead_id")
    services = data.get("services", [])
    notes = data.get("notes", "")
    if not lead_id or not services:
        return jsonify({"error": "lead_id y services son requeridos"}), 400

    from agents.presupuestos.budget_agent import _agent
    result = _agent.create_budget(lead_id, services, notes)
    return _json_response(result)


@app.route("/budgets/<int:budget_id>/approve", methods=["POST"])
def approve_budget(budget_id: int):
    """Aprueba y envía WhatsApp — ÚNICO punto de envío al cliente."""
    from db.database import get_db
    from db.leads import get_lead
    db = get_db()
    row = db.fetchone("SELECT * FROM budgets WHERE id = %s", (budget_id,))
    if not row:
        return jsonify({"error": "No encontrado"}), 404

    db.execute(
        "UPDATE budgets SET status = 'approved' WHERE id = %s",
        (budget_id,))

    # Enviar WhatsApp si el lead tiene teléfono
    lead = get_lead(row["lead_id"])
    wa_sent = False
    if lead and lead.get("phone"):
        from agents.presupuestos.budget_agent import _agent
        msg = (f"Hola {row['client_name']}! 👋 "
               f"Te preparamos un presupuesto personalizado de PulsarMoon. "
               f"¿Te parece si coordinamos para revisarlo juntos? 📋")
        wa_sent = _agent.send_whatsapp(lead["phone"], msg)

    return jsonify({"ok": True, "whatsapp_sent": wa_sent})


@app.route("/budgets/<int:budget_id>/reject", methods=["POST"])
def reject_budget(budget_id: int):
    """Rechaza un presupuesto."""
    from db.database import get_db
    get_db().execute(
        "UPDATE budgets SET status = 'rejected' WHERE id = %s",
        (budget_id,))
    return jsonify({"ok": True})


@app.route("/budgets/<int:budget_id>/edit", methods=["POST"])
def edit_budget(budget_id: int):
    """Regenera presupuesto con nuevos servicios/notas."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON requerido"}), 400

    from db.database import get_db
    db = get_db()
    row = db.fetchone("SELECT * FROM budgets WHERE id = %s", (budget_id,))
    if not row:
        return jsonify({"error": "No encontrado"}), 404

    services = data.get("services", json.loads(row["services"]))
    notes = data.get("notes", row.get("notes", ""))

    from agents.presupuestos.budget_agent import _agent
    result = _agent.create_budget(row["lead_id"], services, notes)

    # Marcar el viejo como reemplazado
    db.execute(
        "UPDATE budgets SET status = 'replaced' WHERE id = %s",
        (budget_id,))

    return _json_response(result)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "agent": "budget-01"})


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    app.run(host="0.0.0.0", port=8769)
