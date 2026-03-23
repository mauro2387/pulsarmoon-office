"""
Precios de PulsarMoon — archivo editable directamente.
Cambiar valores acá sin tocar lógica del agente.
"""

PRICES = {
    "landing_page": {
        "name": "Landing Page Profesional",
        "setup_uyu": 6500,
        "setup_label": "desde $6.500",
        "monthly_uyu": 0,
        "desc": "Landing page moderna, mobile-first, con formulario de contacto",
    },
    "web_corporativa": {
        "name": "Sitio Web Corporativo",
        "setup_uyu": 19350,
        "setup_label": "desde $19.350",
        "monthly_uyu": 12000,
        "desc": "Sitio web completo con hasta 6 páginas, panel de administración",
    },
    "ecommerce": {
        "name": "Tienda Online (E-commerce)",
        "setup_uyu": 32680,
        "setup_label": "desde $32.680",
        "monthly_uyu": 20000,
        "desc": "Tienda online completa con carrito, pagos y panel de gestión",
    },
    "sistema_simple": {
        "name": "Sistema Web Simple",
        "setup_uyu": 34400,
        "setup_label": "$34.400",
        "monthly_uyu": 15000,
        "desc": "Sistema web a medida con base de datos y panel de administración",
    },
    "sistema_complejo": {
        "name": "Sistema Web Complejo",
        "setup_uyu": 68800,
        "setup_label": "desde $68.800",
        "monthly_uyu": 35000,
        "desc": "Sistema complejo con múltiples módulos, integraciones y panel avanzado",
    },
    "app_movil": {
        "name": "Aplicación Móvil",
        "setup_uyu": 51600,
        "setup_label": "$51.600",
        "monthly_uyu": 25000,
        "desc": "App iOS y Android a medida con panel de administración web",
    },
    "marketing_basico": {
        "name": "Marketing Digital Básico",
        "setup_uyu": 0,
        "setup_label": "$0",
        "monthly_uyu": 12000,
        "desc": "Gestión de redes sociales, 3 posts semanales, reportes mensuales",
    },
    "marketing_completo": {
        "name": "Marketing 360°",
        "setup_uyu": 0,
        "setup_label": "$0",
        "monthly_uyu": 25000,
        "desc": "Marketing completo: redes, SEO, campañas pagas, reportes avanzados",
    },
    "mantenimiento": {
        "name": "Mantenimiento y Soporte",
        "setup_uyu": 0,
        "setup_label": "$0",
        "monthly_uyu": 8000,
        "desc": "Soporte técnico, actualizaciones, backups y monitoreo mensual",
    },
    "mensualidad_especial": {
        "name": "Mensualidad Especial (Cliente VIP)",
        "setup_uyu": 0,
        "setup_label": "$0",
        "monthly_uyu": 35000,
        "desc": "Acceso completo a todos los servicios por una mensualidad fija. "
                "Incluye web, marketing, soporte y más.",
    },
    "a_discutir": {
        "name": "Proyecto Especial / A Discutir",
        "setup_uyu": 0,
        "setup_label": "A discutir",
        "monthly_uyu": 0,
        "desc": "Proyecto personalizado. Los valores se definen en reunión con el cliente.",
    },
}

CONDITIONS = {
    "payment": "40% al inicio del proyecto, 60% al finalizar",
    "validity": "Validez del presupuesto: 15 días",
    "support": "Incluye 3 meses de soporte técnico post-lanzamiento",
    "revisions": "Hasta 3 rondas de revisiones incluidas",
}

# Descuento por contratar múltiples servicios
DISCOUNT_THRESHOLD = 2
DISCOUNT_PERCENT = 10
