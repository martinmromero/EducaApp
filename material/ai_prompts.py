"""
Prompt de generación de preguntas con IA — valor por default y helpers.

El texto real usado en cada llamada vive en QuestionGenerationConfig
(un singleton editable desde Administración → "Prompt de generación IA",
sin pasar por Django Admin). Este módulo solo define el default de
fábrica (usado para poblar la fila la primera vez, y como fallback si el
template guardado tiene un placeholder roto) y la lista de placeholders
válidos, documentada acá para que la UI de administración la muestre.
"""

# Placeholders que el template puede usar — se completan con
# str.format(**contexto) en cada llamada. Documentado para la UI de admin.
PROMPT_PLACEHOLDERS = {
    'num_questions': 'Cantidad de preguntas a generar en este fragmento.',
    'chapter_title': 'Título del capítulo/sección que se está procesando.',
    'context_note': 'Aviso de "(parte X de Y)" cuando el capítulo se dividió en varios fragmentos — vacío si no aplica.',
    'images_note': 'Aviso sobre imágenes adjuntas (si el usuario activó "Incluir imágenes del documento") — vacío si no aplica.',
    'content': 'El texto del fragmento a partir del cual se generan las preguntas.',
    'enabled_descriptions': 'Lista de tipos de pregunta habilitados, con su descripción.',
    'existing_block': 'Preguntas ya generadas para este documento, para no repetirlas — vacío si es la primera tanda.',
    'bloom_desc': 'Descripción de los niveles de la taxonomía de Bloom, para el campo bloom_nivel.',
}

DEFAULT_TEMPERATURE = 0.2

DEFAULT_PROMPT_TEMPLATE = """Analizá el siguiente texto educativo del capítulo "{chapter_title}" {context_note} y generá exactamente {num_questions} preguntas variadas.
{images_note}
TEXTO:
{content}

TIPOS DE PREGUNTAS HABILITADOS:
{enabled_descriptions}
{existing_block}
REGLAS:
- Generá exactamente {num_questions} preguntas basándote ÚNICAMENTE en el texto anterior.
- No inventes datos, cifras, nombres, fechas ni conceptos que no estén explícitamente en el TEXTO. Si no estás seguro de que algo esté en el texto, no lo uses.
- Antes de responder, verificá mentalmente que cada afirmación de cada pregunta, opción y respuesta sea verificable palabra por palabra en el TEXTO dado.
- Si el texto no alcanza para armar una pregunta de calidad sobre un aspecto puntual, elegí otro aspecto mejor cubierto en el texto en vez de completar con información inventada.
- El bloque "Formato JSON requerido" de más abajo es solo un ejemplo de ESTRUCTURA: su contenido de ejemplo es ficticio, no forma parte del TEXTO, y nunca debe copiarse, parafrasearse ni reutilizarse como si fuera una pregunta real.
- Distribuí los tipos de manera relativamente pareja entre los tipos habilitados.
- Variá la dificultad: dificultad 1-2 (fácil), 3 (media), 4-5 (difícil).
- Para "opcion_multiple": siempre 4 opciones con prefijo A), B), C), D). Los distractores (opciones incorrectas) deben ser plausibles pero verificablemente falsos según el TEXTO — no los inventes con datos de fuera del texto.
- Para "completar_blank": escribí la pregunta con [___] donde va la respuesta.
- Para "verdadero_falso": la respuesta debe ser exactamente "Verdadero" o "Falso".
- Para "desarrollo": la respuesta es la respuesta de referencia del docente (no del alumno).
- No incluyas referencias a páginas, títulos de sección ni numeración.
- Respondé SOLO con JSON válido, sin bloques de código markdown.

Formato JSON requerido:
{{
  "preguntas": [
    {{
      "pregunta": "texto de la pregunta",
      "tipo": "opcion_multiple",
      "opciones": ["A) opción 1", "B) opción 2", "C) opción 3", "D) opción 4"],
      "respuesta_correcta_index": 0,
      "respuesta": "A) texto de la opción correcta",
      "explicacion": "breve explicación de por qué es correcta",
      "dificultad": 2,
      "bloom_nivel": 1
    }},
    {{
      "pregunta": "Afirmación concreta. ¿Verdadero o Falso?",
      "tipo": "verdadero_falso",
      "respuesta": "Verdadero",
      "explicacion": "...",
      "dificultad": 1,
      "bloom_nivel": 1
    }},
    {{
      "pregunta": "texto de la pregunta con [___] donde va la respuesta",
      "tipo": "completar_blank",
      "respuesta": "texto exacto que completa el espacio, tomado del TEXTO",
      "explicacion": "breve explicación de por qué es correcta",
      "dificultad": 2,
      "bloom_nivel": 1
    }},
    {{
      "pregunta": "Explicá cómo ocurre el proceso X.",
      "tipo": "desarrollo",
      "respuesta": "Respuesta de referencia: El proceso X ocurre cuando...",
      "explicacion": "Evalúa comprensión profunda del proceso.",
      "dificultad": 4,
      "bloom_nivel": 3
    }}
  ]
}}

Nota sobre bloom_nivel: {bloom_desc}"""
