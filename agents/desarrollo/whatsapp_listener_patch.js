/**
 * PATCH para ~/whatsapp/index.js en el server-apps.
 * Agregar este bloque dentro de client.on('message', async msg => { ... })
 * DESPUÉS de los handlers existentes.
 * 
 * Mauro: copiar este código al index.js del server-apps manualmente.
 */

// ─── Detección de solicitudes de desarrollo (solo Mauro) ──────────────

const MAURO_NUMBERS = ['59891722750@c.us', '266924315422936@lid'];
const DEV_KEYWORDS = [
    'nueva web', 'nuevo sistema', 'nueva app', 'nueva landing',
    'hay que hacer', 'necesito una web', 'necesito un sistema',
    'necesito una app', 'necesito una landing',
];

// Agregar dentro de client.on('message', async msg => { ... }):
if (MAURO_NUMBERS.includes(msg.from)) {
    const msgLower = msg.body.toLowerCase();
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
    }

    // Detectar aprobación/rechazo de proyectos PM
    const pmApproveMatch = msg.body.match(/^APROBAR\s+(PM-\d{4}-\d{3})$/i);
    const pmRejectMatch = msg.body.match(/^RECHAZAR\s+(PM-\d{4}-\d{3})$/i);

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
    }

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
    }

    // Detectar solicitud de link al roadmap
    const pmRoadmapMatch = msg.body.match(/^roadmap\s+(PM-\d{4}-\d{3})$/i);
    if (pmRoadmapMatch) {
        const projectId = pmRoadmapMatch[1].toUpperCase();
        await client.sendMessage(msg.from,
            `🗺️ Roadmap: https://api.vydre.me/pm/roadmap/${projectId}`
        );
    }

    // Detectar pedido de roadmap directo
    // Formato: "pm [cliente]: [descripción]"
    // Ejemplo: "pm Clínica Sol: web con agenda online y galería"
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
            // El roadmap llega por WhatsApp automáticamente via notify_mauro()
        } catch (err) {
            console.error('[PM] Error creando proyecto directo:', err.message);
            await client.sendMessage(msg.from, '❌ Error generando roadmap. Server no responde.');
        }
    }
}
