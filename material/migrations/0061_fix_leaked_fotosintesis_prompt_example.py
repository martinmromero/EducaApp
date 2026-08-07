from django.db import migrations

# Bloque de ejemplo original (con dato real y concreto) que se filtraba al
# contenido generado — ver [[project_ai_generation_limits]] /
# material/ai_prompts.py. Se busca por coincidencia exacta: si el admin ya
# editó este bloque puntual a mano, no se toca (se prefiere no pisar una
# edición manual antes que forzar el reemplazo).
OLD_EXAMPLE_BLOCK = '''    {{
      "pregunta": "El proceso por el cual las plantas obtienen energía se llama [___].",
      "tipo": "completar_blank",
      "respuesta": "fotosíntesis",
      "explicacion": "...",
      "dificultad": 2,
      "bloom_nivel": 1
    }},'''

NEW_EXAMPLE_BLOCK = '''    {{
      "pregunta": "texto de la pregunta con [___] donde va la respuesta",
      "tipo": "completar_blank",
      "respuesta": "texto exacto que completa el espacio, tomado del TEXTO",
      "explicacion": "breve explicación de por qué es correcta",
      "dificultad": 2,
      "bloom_nivel": 1
    }},'''

OLD_RULE_ANCHOR = '''- Si el texto no alcanza para armar una pregunta de calidad sobre un aspecto puntual, elegí otro aspecto mejor cubierto en el texto en vez de completar con información inventada.
- Distribuí los tipos de manera relativamente pareja entre los tipos habilitados.'''

NEW_RULE_BLOCK = '''- Si el texto no alcanza para armar una pregunta de calidad sobre un aspecto puntual, elegí otro aspecto mejor cubierto en el texto en vez de completar con información inventada.
- El bloque "Formato JSON requerido" de más abajo es solo un ejemplo de ESTRUCTURA: su contenido de ejemplo es ficticio, no forma parte del TEXTO, y nunca debe copiarse, parafrasearse ni reutilizarse como si fuera una pregunta real.
- Distribuí los tipos de manera relativamente pareja entre los tipos habilitados.'''


def fix_leaked_example(apps, schema_editor):
    QuestionGenerationConfig = apps.get_model('material', 'QuestionGenerationConfig')
    for cfg in QuestionGenerationConfig.objects.all():
        text = cfg.prompt_template or ''
        changed = False
        if OLD_EXAMPLE_BLOCK in text:
            text = text.replace(OLD_EXAMPLE_BLOCK, NEW_EXAMPLE_BLOCK)
            changed = True
        if OLD_RULE_ANCHOR in text and 'solo un ejemplo de ESTRUCTURA' not in text:
            text = text.replace(OLD_RULE_ANCHOR, NEW_RULE_BLOCK)
            changed = True
        if changed:
            cfg.prompt_template = text
            cfg.save(update_fields=['prompt_template'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0060_profile_security_answer_profile_security_question'),
    ]

    operations = [
        migrations.RunPython(fix_leaked_example, noop_reverse),
    ]
