/**
 * WhatsApp Bot — PulsarMoon
 * Server-apps (192.168.1.11) — /root/whatsapp/index.js
 * WWebJS + Express, puerto 3000
 *
 * Comandos Mauro:
 *   "nueva web", "necesito una app", etc → crea sesión dev
 *   "pm Cliente: descripción"            → genera roadmap con Gemini
 *   "APROBAR PM-2026-001"                → aprueba proyecto
 *   "RECHAZAR PM-2026-001"               → rechaza proyecto
 *   "roadmap PM-2026-001"                → link al roadmap web
 *
 * Endpoint:
 *   POST /send  → { number, message }
 *
 * Deploy: sudo tee /root/whatsapp/index.js < index.js && pm2 restart whatsapp
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode-terminal');

const app = express();
app.use(express.json());

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
    },
});

// ─── QR y conexión ────────────────────────────────────────────────────────────

client.on('qr', (qr) => {
    qrcode.generate(qr, { small: true });
    console.log('[WA] QR generado — escaneá con WhatsApp');
});

client.on('ready', () => {
    console.log('[WA] Cliente conectado y listo');
});

client.on('disconnected', (reason) => {
    console.log('[WA] Desconectado:', reason);
});

// ─── Números de Mauro (c.us + LID) ───────────────────────────────────────────

const MAURO_NUMBERS = ['59891722750@c.us', '266924315422936@lid'];

const DEV_KEYWORDS = [
    'nueva web', 'nuevo sistema', 'nueva app', 'nueva landing',
    'hay que hacer', 'necesito una web', 'necesito un sistema',
    'necesito una app', 'necesito una landing',
];

// ─── Handler de mensajes ──────────────────────────────────────────────────────

client.on('message', async (msg) => {
    if (!MAURO_NUMBERS.includes(msg.from)) return;

    const msgLower = msg.body.toLowerCase();

    // ── 1. Detección de solicitudes de desarrollo ─────────────────────────
    const isDevRequest = DEV_KEYWORDS.some(kw => msgLower.includes(kw));
    if (isDevRequest) {
        try {
            const response = await fetch('https://api.vydre.me/dev/session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone: '59891722750' }),
            });
            const data = await response.json();
            await client.sendMessage(msg.from,
                `✅ Nuevo proyecto detectado!\n\n` +
                `Completá el brief en menos de 1 minuto:\n${data.url}\n\n` +
                `_El link expira en 24hs_`
            );
            console.log('[DEV] Sesión creada:', data.token);
        } catch (err) {
            console.error('[DEV] Error creando sesión:', err.message);
            await client.sendMessage(msg.from,
                '❌ Error creando sesión de desarrollo. Revisá el server.'
            );
        }
        return;
    }

    // ── 2. Aprobación de proyectos PM ─────────────────────────────────────
    const pmApproveMatch = msg.body.match(/^APROBAR\s+(PM-\d{4}-\d{3})$/i);
    if (pmApproveMatch) {
        const projectId = pmApproveMatch[1].toUpperCase();
        try {
            const response = await fetch(`https://api.vydre.me/pm/approve/${projectId}`, {
                method: 'POST'
            });
            if (response.ok) {
                await client.sendMessage(msg.from, `✅ Proyecto ${projectId} aprobado y activado.`);
            } else {
                await client.sendMessage(msg.from, `❌ Error aprobando ${projectId}. Verificá el ID.`);
            }
        } catch (err) {
            console.error('[PM] Error aprobando proyecto:', err.message);
            await client.sendMessage(msg.from, `❌ Error aprobando ${projectId}. Server no responde.`);
        }
        return;
    }

    // ── 3. Rechazo de proyectos PM ────────────────────────────────────────
    const pmRejectMatch = msg.body.match(/^RECHAZAR\s+(PM-\d{4}-\d{3})$/i);
    if (pmRejectMatch) {
        const projectId = pmRejectMatch[1].toUpperCase();
        try {
            const response = await fetch(`https://api.vydre.me/pm/reject/${projectId}`, {
                method: 'POST'
            });
            if (response.ok) {
                await client.sendMessage(msg.from, `🚫 Proyecto ${projectId} rechazado.`);
            } else {
                await client.sendMessage(msg.from, `❌ Error rechazando ${projectId}.`);
            }
        } catch (err) {
            console.error('[PM] Error rechazando proyecto:', err.message);
            await client.sendMessage(msg.from, `❌ Error rechazando ${projectId}. Server no responde.`);
        }
        return;
    }

    // ── 4. Solicitar link al roadmap ──────────────────────────────────────
    const pmRoadmapMatch = msg.body.match(/^roadmap\s+(PM-\d{4}-\d{3})$/i);
    if (pmRoadmapMatch) {
        const projectId = pmRoadmapMatch[1].toUpperCase();
        await client.sendMessage(msg.from,
            `🗺️ Roadmap: https://api.vydre.me/pm/roadmap/${projectId}`
        );
        return;
    }

    // ── 5. Crear proyecto directo via PM ──────────────────────────────────
    // Formato: "pm [cliente]: [descripción]"
    const pmDirectMatch = msg.body.match(/^pm\s+(.+?):\s+(.+)$/i);
    if (pmDirectMatch) {
        const pmClient = pmDirectMatch[1].trim();
        const pmDescription = pmDirectMatch[2].trim();
        await client.sendMessage(msg.from,
            `🧠 Generando roadmap para *${pmClient}*...`);
        try {
            const response = await fetch('https://api.vydre.me/pm/create-direct', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    description: pmDescription,
                    client: pmClient,
                    plazo: 'normal'
                })
            });
            if (!response.ok) {
                await client.sendMessage(msg.from, '❌ Error generando roadmap.');
            }
        } catch (err) {
            console.error('[PM] Error creando proyecto directo:', err.message);
            await client.sendMessage(msg.from, '❌ Error generando roadmap. Server no responde.');
        }
        return;
    }
});

// ─── Endpoint para enviar mensajes ────────────────────────────────────────────

app.post('/send', async (req, res) => {
    const { number, message } = req.body;
    if (!number || !message) {
        return res.status(400).json({ error: 'number y message requeridos' });
    }
    try {
        const chatId = number.includes('@') ? number : `${number}@c.us`;
        await client.sendMessage(chatId, message);
        res.json({ status: 'sent' });
    } catch (err) {
        console.error('[WA] Error enviando:', err.message);
        res.status(500).json({ error: err.message });
    }
});

app.get('/health', (req, res) => {
    const state = client.info ? 'connected' : 'disconnected';
    res.json({ status: state });
});

// ─── Iniciar ──────────────────────────────────────────────────────────────────

client.initialize();
app.listen(3000, () => {
    console.log('[WA] API escuchando en http://0.0.0.0:3000');
});
