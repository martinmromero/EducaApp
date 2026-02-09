"""
Ejemplo de uso del modelo llama3.1:8b para análisis de documentos educativos
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'educaapp.settings')
import django
django.setup()

from material.local_ai_client import local_ai

# Ejemplo de texto de un libro
EJEMPLO_LIBRO = """
UNIDAD 3: FUNDAMENTOS DE BASES DE DATOS

Las bases de datos son sistemas organizados para almacenar y gestionar información.
En esta unidad aprenderemos los conceptos fundamentales.

3.1 ¿Qué es una Base de Datos?
Una base de datos es una colección organizada de datos estructurados.
Permite almacenar, consultar y modificar información de manera eficiente.

3.2 Modelos de Datos
- Modelo Relacional: organiza datos en tablas con filas y columnas
- Modelo NoSQL: almacena datos en documentos JSON
- Modelo Jerárquico: datos en estructura de árbol

3.3 SQL - Lenguaje de Consultas
SQL (Structured Query Language) es el lenguaje estándar para gestionar bases de datos.
Comandos principales:
- SELECT: consultar datos
- INSERT: agregar datos
- UPDATE: modificar datos
- DELETE: eliminar datos
"""

def ejemplo_1_estructura():
    """Ejemplo 1: Analizar estructura del documento"""
    print("\n" + "="*70)
    print("EJEMPLO 1: ANALIZAR ESTRUCTURA DEL DOCUMENTO")
    print("="*70)
    
    prompt = f"""Analiza el siguiente texto educativo y devuelve SOLO un JSON con esta estructura:
{{
  "unidad": "número y título",
  "secciones": [
    {{"numero": "...", "titulo": "...", "conceptos_clave": ["...", "..."]}}
  ]
}}

TEXTO:
{EJEMPLO_LIBRO}

Responde SOLO con el JSON, sin explicaciones adicionales."""

    print(f"\n📝 Modelo activo: {local_ai.get_current_model()}")
    print(f"⏱️  Generando...")
    
    resultado = local_ai.generate(
        prompt=prompt,
        temperature=0.3,  # Baja para respuestas más precisas
        max_tokens=400
    )
    
    if resultado['success']:
        print(f"\n✅ Generado en {resultado['duration_ms']/1000:.1f}s")
        print(f"📊 Tokens: {resultado['tokens']}")
        print(f"\n📄 RESULTADO:")
        print("-" * 70)
        print(resultado['text'])
        print("-" * 70)
    else:
        print(f"\n❌ Error: {resultado['error']}")

def ejemplo_2_preguntas():
    """Ejemplo 2: Generar preguntas automáticas"""
    print("\n" + "="*70)
    print("EJEMPLO 2: GENERAR PREGUNTAS AUTOMÁTICAS")
    print("="*70)
    
    prompt = f"""Basándote en el siguiente texto educativo, genera 3 preguntas de opción múltiple.

TEXTO:
{EJEMPLO_LIBRO}

Devuelve SOLO un JSON con este formato:
{{
  "preguntas": [
    {{
      "pregunta": "¿Qué es...?",
      "opciones": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "respuesta_correcta": "A",
      "explicacion": "..."
    }}
  ]
}}

Responde SOLO con el JSON."""

    print(f"\n📝 Modelo activo: {local_ai.get_current_model()}")
    print(f"⏱️  Generando...")
    
    resultado = local_ai.generate(
        prompt=prompt,
        temperature=0.5,  # Un poco más de creatividad para preguntas variadas
        max_tokens=600
    )
    
    if resultado['success']:
        print(f"\n✅ Generado en {resultado['duration_ms']/1000:.1f}s")
        print(f"📊 Tokens: {resultado['tokens']}")
        print(f"\n📄 RESULTADO:")
        print("-" * 70)
        print(resultado['text'])
        print("-" * 70)
    else:
        print(f"\n❌ Error: {resultado['error']}")

def ejemplo_3_resumen():
    """Ejemplo 3: Generar resumen ejecutivo"""
    print("\n" + "="*70)
    print("EJEMPLO 3: GENERAR RESUMEN EJECUTIVO")
    print("="*70)
    
    prompt = f"""Resume el siguiente texto educativo en máximo 3 puntos clave.

TEXTO:
{EJEMPLO_LIBRO}

Formato de respuesta:
1. [punto clave 1]
2. [punto clave 2]
3. [punto clave 3]"""

    print(f"\n📝 Modelo activo: {local_ai.get_current_model()}")
    print(f"⏱️  Generando...")
    
    resultado = local_ai.generate(
        prompt=prompt,
        temperature=0.4,
        max_tokens=200
    )
    
    if resultado['success']:
        print(f"\n✅ Generado en {resultado['duration_ms']/1000:.1f}s")
        print(f"📊 Tokens: {resultado['tokens']}")
        print(f"\n📄 RESULTADO:")
        print("-" * 70)
        print(resultado['text'])
        print("-" * 70)
    else:
        print(f"\n❌ Error: {resultado['error']}")

def ejemplo_4_cambiar_modelo():
    """Ejemplo 4: Cambiar a otro modelo"""
    print("\n" + "="*70)
    print("EJEMPLO 4: CAMBIAR MODELO ACTIVO")
    print("="*70)
    
    print(f"\n📝 Modelo actual: {local_ai.get_current_model()}")
    print(f"\n💡 Modelos disponibles:")
    
    modelos = local_ai.get_models()
    for i, modelo in enumerate(modelos[:5], 1):
        print(f"   {i}. {modelo['name']}")
    
    # Intentar cambiar a command-r7b si está disponible
    nuevo_modelo = 'command-r7b:latest'
    print(f"\n🔄 Intentando cambiar a: {nuevo_modelo}")
    
    if local_ai.set_model(nuevo_modelo):
        print(f"✅ Modelo cambiado exitosamente")
        print(f"📝 Nuevo modelo activo: {local_ai.get_current_model()}")
        
        # Restaurar al default
        print(f"\n🔄 Restaurando modelo por defecto...")
        local_ai.set_model('llama3.1:8b')
        print(f"✅ Restaurado: {local_ai.get_current_model()}")
    else:
        print(f"❌ No se pudo cambiar el modelo (probablemente no está disponible)")

def main():
    print("\n" + "="*70)
    print("  EJEMPLOS DE USO: LLAMA3.1:8b PARA ANÁLISIS DE DOCUMENTOS")
    print("="*70)
    
    if not local_ai.is_available():
        print("\n❌ Servidor Ollama no disponible")
        print("   Verifica la conexión VPN")
        return
    
    print(f"\n✅ Conectado a: {local_ai.base_url}")
    print(f"📝 Modelo por defecto: {local_ai.default_model}")
    print(f"🎯 Modelo actual: {local_ai.get_current_model()}")
    
    # Ejecutar ejemplos
    try:
        ejemplo_1_estructura()
        input("\n👉 Presiona ENTER para continuar con el siguiente ejemplo...")
        
        ejemplo_2_preguntas()
        input("\n👉 Presiona ENTER para continuar con el siguiente ejemplo...")
        
        ejemplo_3_resumen()
        input("\n👉 Presiona ENTER para continuar con el siguiente ejemplo...")
        
        ejemplo_4_cambiar_modelo()
        
    except KeyboardInterrupt:
        print("\n\n⏸️  Ejemplos interrumpidos por el usuario")
    
    print("\n" + "="*70)
    print("  ✅ EJEMPLOS COMPLETADOS")
    print("="*70)
    print("\n💡 Ahora puedes usar estas técnicas en tu aplicación:")
    print("   - Procesar documentos PDF/DOCX automáticamente")
    print("   - Generar preguntas desde contenidos")
    print("   - Crear resúmenes y análisis")
    print("\n")

if __name__ == '__main__':
    main()
