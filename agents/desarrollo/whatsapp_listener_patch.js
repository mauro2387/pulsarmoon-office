/**
 * PATCH para ~/whatsapp/index.js en el server-apps.
 * Agregar este bloque dentro de client.on('message', async msg => { ... })
 * DESPUÉS de los handlers existentes.
 * 
 * Mauro: copiar este código al index.js del server-apps manualmente.
 */

// ─── Detección de solicitudes de desarrollo (solo Mauro) ──────────────

const MAURO_NUMBER = '59891722750@c.us';
const DEV_KEYWORDS = [
    'nueva web', 'nuevo sistema', 'nueva app', 'nueva landing',
    'hay que hacer', 'necesito una web', 'necesito un sistema',
    'necesito una app', 'necesito una landing',
];

// Agregar dentro de client.on('message', async msg => { ... }):
if (msg.from === MAURO_NUMBER) {
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

            await client.sendMessage(MAURO_NUMBER,
                `✅ Nuevo proyecto detectado!\n\n` +
                `Completá el brief en menos de 1 minuto:\n${data.url}\n\n` +
                `_El link expira en 24hs_`
            );
            console.log('[DEV] Sesión creada:', data.token);
        } catch (err) {
            console.error('[DEV] Error creando sesión:', err.message);
            await client.sendMessage(MAURO_NUMBER,
                '❌ Error creando sesión de desarrollo. Revisá el server.'
            );
        }
    }
}
