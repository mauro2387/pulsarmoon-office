"""
Panel de aprobación de follow-ups — Flask en puerto 8770.
NADA sale al cliente sin aprobación de Mauro desde este panel.
"""
import json
import logging
import sys
from pathlib import Path

from flask import Flask, Response, jsonify, request
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


_PANEL_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<title>PulsarMoon — Seguimiento</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#0d1117;color:#e6edf3}
.top{background:#161b22;padding:16px 24px;border-bottom:1px solid #30363d}
.top h1{font-size:18px;color:#58a6ff}
.container{max-width:900px;margin:24px auto;padding:0 16px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:12px}
.card h3{color:#58a6ff;margin-bottom:4px;font-size:15px}
.card .meta{color:#8b949e;font-size:13px;margin-bottom:6px}
.card .msg{background:#0d1117;border:1px solid #30363d;border-radius:6px;
padding:10px;margin:8px 0;font-size:13px;line-height:1.5;white-space:pre-wrap}
.btns{display:flex;gap:8px;margin-top:10px}
.btns button{padding:6px 14px;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600}
.btn-approve{background:#238636;color:#fff}
.btn-reject{background:#da3633;color:#fff}
.btn-edit{background:#30363d;color:#e6edf3;border:1px solid #484f58!important}
.empty{text-align:center;color:#8b949e;padding:40px;font-size:15px}
.fu-num{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.fu-1{background:#1f6feb22;color:#58a6ff;border:1px solid #1f6feb}
.fu-2{background:#d292221a;color:#d29922;border:1px solid #d29922}
.status{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;margin-left:6px}
.status-sent{background:#2386361a;color:#3fb950;border:1px solid #3fb950}
.status-rejected{background:#da36331a;color:#f85149;border:1px solid #f85149}
dialog{background:#161b22;border:1px solid #30363d;border-radius:8px;color:#e6edf3;
padding:20px;max-width:500px;width:90%}
dialog::backdrop{background:rgba(0,0,0,.6)}
dialog textarea{width:100%;height:100px;background:#0d1117;color:#e6edf3;
border:1px solid #30363d;border-radius:6px;padding:8px;font-size:13px;margin:10px 0}
dialog button{padding:6px 16px;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600}
</style>
</head>
<body>
<div class="top"><h1>📞 PulsarMoon — Panel de Seguimiento</h1></div>
<div class="container"><div id="list"></div></div>
<dialog id="editDialog">
<h3 id="editTitle">Editar mensaje</h3>
<textarea id="editMsg"></textarea>
<div style="display:flex;gap:8px;justify-content:flex-end">
<button style="background:#30363d;color:#e6edf3" onclick="editDialog.close()">Cancelar</button>
<button style="background:#238636;color:#fff" onclick="saveEdit()">Guardar</button>
</div>
</dialog>
<script>
const API = location.origin;
let editId = null;
const editDialog = document.getElementById('editDialog');

async function load() {
  const res = await fetch(API + '/followups');
  const data = await res.json();
  const list = document.getElementById('list');
  if (!data.length) { list.innerHTML = '<div class="empty">Sin follow-ups pendientes 🎉</div>'; return; }
  list.innerHTML = data.map(f => {
    const fuClass = f.followup_number === 1 ? 'fu-1' : 'fu-2';
    const isPending = f.status === 'pending_approval';
    let statusHtml = '';
    if (f.status === 'sent') statusHtml = '<span class="status status-sent">Enviado</span>';
    else if (f.status === 'rejected') statusHtml = '<span class="status status-rejected">Descartado</span>';
    const days = f.days_since_contact ? f.days_since_contact + ' días desde contacto' : '';
    return `<div class="card">
      <h3>${f.business_name}
        <span class="fu-num ${fuClass}">Follow-up #${f.followup_number}</span>
        ${statusHtml}
      </h3>
      <div class="meta">📱 ${f.phone} | ${days}</div>
      <div class="msg">${f.message}</div>
      ${isPending ? `<div class="btns">
        <button class="btn-approve" onclick="approve(${f.id})">✅ Aprobar y Enviar</button>
        <button class="btn-edit" onclick="openEdit(${f.id},'${f.business_name}',\`${f.message.replace(/`/g,'\\`')}\`)">✏️ Editar mensaje</button>
        <button class="btn-reject" onclick="reject(${f.id})">❌ Descartar</button>
      </div>` : ''}
    </div>`;
  }).join('');
}

function approve(id) {
  if (!confirm('¿Enviar WhatsApp a este lead?')) return;
  fetch(API+'/followups/'+id+'/approve',{method:'POST'}).then(()=>load());
}
function reject(id) {
  if (!confirm('¿Descartar este follow-up?')) return;
  fetch(API+'/followups/'+id+'/reject',{method:'POST'}).then(()=>load());
}
function openEdit(id, name, msg) {
  editId = id;
  document.getElementById('editTitle').textContent = 'Editar: ' + name;
  document.getElementById('editMsg').value = msg;
  editDialog.showModal();
}
function saveEdit() {
  const msg = document.getElementById('editMsg').value;
  fetch(API+'/followups/'+editId+'/edit',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:msg})
  }).then(()=>{editDialog.close();load();});
}
load();
</script>
</body>
</html>"""


@app.route("/")
def panel():
    """Panel HTML de aprobación de follow-ups."""
    return _PANEL_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/followups")
def list_followups():
    """Lista follow-ups con días desde contacto."""
    from db.database import get_db
    rows = get_db().fetchall("""
        SELECT fq.*,
               EXTRACT(DAY FROM NOW() - l.updated_at)::int
                   AS days_since_contact
        FROM followup_queue fq
        JOIN leads l ON l.id = fq.lead_id
        ORDER BY
            CASE fq.status
                WHEN 'pending_approval' THEN 0
                ELSE 1
            END,
            fq.created_at DESC
    """)
    return _json_response(rows)


@app.route("/followups/<int:fid>/approve", methods=["POST"])
def approve_followup(fid: int):
    """Aprueba y envía WhatsApp."""
    from agents.seguimiento.followup_agent import _agent
    result = _agent.send_approved_followup(fid)
    return _json_response(result)


@app.route("/followups/<int:fid>/reject", methods=["POST"])
def reject_followup(fid: int):
    """Descarta follow-up y marca lead como cold."""
    from db.database import get_db
    db = get_db()
    fu = db.fetchone("SELECT * FROM followup_queue WHERE id = %s", (fid,))
    if not fu:
        return jsonify({"error": "No encontrado"}), 404

    db.execute(
        "UPDATE followup_queue SET status = 'rejected' WHERE id = %s",
        (fid,))
    db.execute(
        "UPDATE leads SET status = 'cold' WHERE id = %s",
        (fu["lead_id"],))
    return jsonify({"ok": True})


@app.route("/followups/<int:fid>/edit", methods=["POST"])
def edit_followup(fid: int):
    """Actualiza el mensaje de un follow-up pendiente."""
    data = request.get_json()
    if not data or not data.get("message"):
        return jsonify({"error": "message requerido"}), 400

    from db.database import get_db
    get_db().execute(
        """UPDATE followup_queue
           SET message = %s, status = 'pending_approval'
           WHERE id = %s""",
        (data["message"], fid))
    return jsonify({"ok": True})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "agent": "followup-01"})


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    app.run(host="0.0.0.0", port=8770)
