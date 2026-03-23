"""
Templates de reportes internos — sin gastar LLM.
"""

# Resumen diario de actividad
DAILY_SUMMARY = """📋 Resumen diario — {fecha}
Leads nuevos: {leads_nuevos}
Contactados hoy: {contactados}
Contenido generado: {contenido}
Pagos pendientes: {pagos_pendientes}
Sitios monitoreados: {sitios_ok}/{sitios_total}
"""

# Alerta de lead caliente
HOT_LEAD = """🔥 Lead caliente detectado
Negocio: {negocio}
Ciudad: {ciudad}
Sector: {sector}
Score: {score}/100
Acción sugerida: {accion}
"""

# Reporte de contenido generado
CONTENT_REPORT = """📝 Contenido generado
Keyword: {keyword} (score: {score})
Blog: {blog_chars} caracteres
Instagram: {ig_chars} caracteres
Facebook: {fb_chars} caracteres
Imagen: {imagen_status}
Estado: pendiente de revisión
"""
