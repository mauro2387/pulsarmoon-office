"""
Templates de mensajes WhatsApp — sin gastar LLM.
Usar con BaseAgent.format_message(TEMPLATE, nombre="...", ...)
"""

# Primer contacto con prospecto
PRIMER_CONTACTO = (
    "Hola {nombre}! 👋 Vi que {negocio} en {ciudad} todavía no tiene "
    "presencia web profesional. En PulsarMoon ayudamos a negocios como "
    "el tuyo a crecer online con sitios a medida y marketing digital. "
    "¿Te gustaría que te cuente cómo podemos ayudarte?"
)

# Seguimiento después de primer contacto (3 días)
FOLLOW_UP_1 = (
    "Hola {nombre}, hace unos días te escribí sobre cómo podemos "
    "ayudar a {negocio} con su presencia digital. ¿Tuviste chance de "
    "pensarlo? Estoy a disposición para charlar sin compromiso 😊"
)

# Segundo seguimiento (7 días)
FOLLOW_UP_2 = (
    "Última consulta {nombre}, ¿te interesa que hablemos sobre cómo "
    "hacer crecer {negocio} online? Si no es el momento, no hay drama. "
    "Quedamos en contacto para cuando lo necesites 🙌"
)

# Presupuesto enviado
PRESUPUESTO_ENVIADO = (
    "Hola {nombre}! Te envié el presupuesto para {proyecto}. "
    "Cualquier duda o ajuste que necesites, escribime sin problema. "
    "Estoy para ayudarte 💪"
)

# Recordatorio de pago vencido
PAGO_VENCIDO = (
    "Hola {nombre}, te recordamos que el pago de {monto} venció "
    "el {fecha}. ¿Pudiste procesarlo? Si necesitás algún ajuste "
    "avisanos y lo coordinamos 🙏"
)

# Alerta de sitio caído
SITIO_CAIDO = (
    "⚠️ {cliente}, detectamos que {url} no responde desde las {hora}. "
    "Nuestro equipo ya está revisando el problema. Te avisamos apenas "
    "se resuelva."
)

# Reporte mensual listo
REPORTE_LISTO = (
    "📊 Hola {nombre}! Tu reporte mensual de {mes} está listo. "
    "Incluye métricas de tráfico, rendimiento y recomendaciones. "
    "¿Querés que lo revisemos juntos?"
)
