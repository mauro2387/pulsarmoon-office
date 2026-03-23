// Panel de aprobación de contenido de marketing — PulsarMoon
const API = `http://localhost:8767`;
let allContent = [];
let currentItem = null;
let currentTab = 'blog';
let currentFilter = 'all';

// === Carga de datos ===
async function loadContent() {
  try {
    const url = currentFilter === 'all'
      ? `${API}/content`
      : `${API}/content?status=${currentFilter}`;
    const res = await fetch(url);
    allContent = await res.json();
    renderCards();
  } catch (e) {
    document.getElementById('content-list').innerHTML =
      '<p class="loading">Error conectando al servidor. ¿Está corriendo en puerto 8767?</p>';
  }
}

// === Render de cards ===
function renderCards() {
  const container = document.getElementById('content-list');
  if (!allContent.length) {
    container.innerHTML = '<p class="loading">No hay contenido generado aún.</p>';
    return;
  }

  container.innerHTML = allContent.map(item => `
    <div class="card" data-id="${item.id}">
      ${item.image_url
        ? `<img class="card-image" src="${esc(item.image_url)}" alt="Imagen generada">`
        : `<div class="card-img-placeholder">\ud83d\uddbc\ufe0f Sin imagen</div>`
      }
      <div class="card-header">
        <span class="card-keyword">${esc(item.trend_keyword)}</span>
        <span class="badge badge-${item.status}">${item.status}</span>
      </div>
      <div class="card-preview">${esc(item.blog_post.substring(0, 200))}...</div>
      <div class="card-meta">
        <span>Score: ${item.trend_score.toFixed(0)}</span>
        <span>${formatDate(item.created_at)}</span>
      </div>
    </div>
  `).join('');

  // Click handlers
  container.querySelectorAll('.card').forEach(card => {
    card.addEventListener('click', () => {
      const id = parseInt(card.dataset.id);
      openModal(allContent.find(c => c.id === id));
    });
  });
}

// === Modal ===
function openModal(item) {
  if (!item) return;
  currentItem = item;
  currentTab = 'blog';
  document.getElementById('modal').classList.remove('hidden');
  updateModalTabs();
  renderModalContent();
  // Ocultar acciones si ya fue revisado
  const actions = document.querySelector('.modal-actions');
  actions.style.display = item.status === 'pending' ? 'flex' : 'none';
}

function closeModal() {
  document.getElementById('modal').classList.add('hidden');
  currentItem = null;
}

function renderModalContent() {
  const body = document.getElementById('modal-body');
  if (!currentItem) return;

  // Imagen arriba del contenido
  const imgHtml = currentItem.image_url
    ? `<img class="modal-image" src="${currentItem.image_url}" alt="Imagen generada"><br>`
    : `<div class="modal-img-placeholder">\ud83d\uddbc\ufe0f Sin imagen generada</div>`;

  switch (currentTab) {
    case 'blog':
      body.innerHTML = imgHtml + formatMarkdown(currentItem.blog_post);
      break;
    case 'ig':
      body.innerHTML = imgHtml;
      body.appendChild(document.createTextNode(currentItem.caption_ig));
      break;
    case 'fb':
      body.innerHTML = imgHtml;
      body.appendChild(document.createTextNode(currentItem.caption_fb));
      break;
  }
}

function updateModalTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === currentTab);
  });
}

// === Acciones de aprobación ===
async function updateStatus(status) {
  if (!currentItem) return;
  try {
    const res = await fetch(`${API}/content/${currentItem.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    if (res.ok) {
      currentItem.status = status;
      closeModal();
      loadContent();
    }
  } catch (e) {
    console.error('Error actualizando estado:', e);
  }
}

// === Helpers ===
function esc(str) {
  const el = document.createElement('span');
  el.textContent = str;
  return el.innerHTML;
}

function formatDate(ts) {
  return new Date(ts * 1000).toLocaleString('es-UY', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
  });
}

function formatMarkdown(md) {
  // Conversión básica de Markdown a HTML
  return md
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^/, '<p>').replace(/$/, '</p>');
}

// === Event listeners ===
document.getElementById('modal-close').addEventListener('click', closeModal);
document.getElementById('modal').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeModal();
});
document.getElementById('btn-approve').addEventListener('click', () => updateStatus('approved'));
document.getElementById('btn-reject').addEventListener('click', () => updateStatus('rejected'));

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    currentTab = btn.dataset.tab;
    updateModalTabs();
    renderModalContent();
  });
});

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    currentFilter = btn.dataset.status;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadContent();
  });
});

// Escape para cerrar modal
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

// Cargar al iniciar
loadContent();
