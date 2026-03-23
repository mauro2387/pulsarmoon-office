# Reglas de uso de LLM — PulsarMoon Office

## NUNCA usar LLM para:
- Verificar si un sitio web está online → requests.get()
- Calcular si venció un pago → SQL + Python datetime
- Decidir a quién contactar → SQL query con filtros
- Formatear números de teléfono → Python regex
- Generar recordatorios simples → templates en whatsapp.py
- Buscar empresas → Google Maps API / scraping Python
- Verificar si una empresa tiene web → requests.get()
- Calcular scores simples → Python reglas numéricas

## SIEMPRE usar LLM para:
- Generar el mensaje personalizado de primer contacto
- Responder preguntas de clientes que requieren contexto
- Redactar la descripción de un presupuesto
- Generar contenido creativo (blog, captions)
- Sintetizar información compleja en lenguaje natural
- Analizar sentimiento de respuestas de clientes

## Modelo por tarea:
- Haiku: mensajes cortos, decisiones simples, clasificaciones
- Sonnet: contenido largo, conversaciones, presupuestos
- Opus: NUNCA en producción automática

## Cache:
- context.md SIEMPRE con cache_control ephemeral
- System prompts repetitivos SIEMPRE cacheados
