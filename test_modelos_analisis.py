"""
Prueba de modelos para análisis de estructura de documentos
Compara diferentes modelos para determinar el mejor para tareas educativas
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'educaapp.settings')
import django
django.setup()

from material.local_ai_client import local_ai

# Texto de ejemplo: extracto de un libro educativo
TEXTO_EJEMPLO = """
CAPÍTULO 1: INTRODUCCIÓN A LA PROGRAMACIÓN

La programación es el proceso de crear instrucciones que una computadora puede ejecutar. 
Los lenguajes de programación son herramientas que permiten a los humanos comunicarse con las máquinas.

1.1 Conceptos Básicos
- Variables: contenedores de datos
- Operadores: símbolos que realizan operaciones
- Estructuras de control: if, while, for

1.2 Primeros Pasos
El primer programa que todo programador escribe es "Hola Mundo". Este programa simple
demuestra la sintaxis básica del lenguaje.

CAPÍTULO 2: ESTRUCTURAS DE DATOS

Las estructuras de datos son formas de organizar información en la memoria.
- Listas: colecciones ordenadas
- Diccionarios: pares clave-valor
- Conjuntos: colecciones únicas
"""

PROMPT_ANALISIS = f"""Analiza el siguiente texto educativo y responde en formato JSON:

TEXTO:
{TEXTO_EJEMPLO}

Tu tarea:
1. Identifica los capítulos principales
2. Lista los subtemas de cada capítulo
3. Genera 2 preguntas de comprensión con sus respuestas

Responde SOLO con JSON válido en este formato:
{{
  "capitulos": [
    {{
      "numero": 1,
      "titulo": "...",
      "subtemas": ["...", "..."],
      "preguntas": [
        {{"pregunta": "...", "respuesta": "..."}}
      ]
    }}
  ]
}}"""

# Modelos recomendados para tareas educativas/analíticas
MODELOS_A_PROBAR = [
    {
        'name': 'deepseek-r1:8b',
        'description': 'DeepSeek R1 - Especializado en razonamiento',
        'recommended': True
    },
    {
        'name': 'llama3.1:8b',
        'description': 'Llama 3.1 - Modelo general confiable y rápido',
        'recommended': True
    },
    {
        'name': 'command-r7b:latest',
        'description': 'Command R - Optimizado para seguir instrucciones',
        'recommended': True
    },
    {
        'name': 'qwen3:8b',
        'description': 'Qwen 3 - Excelente para tareas generales',
        'recommended': False
    },
    {
        'name': 'gemma3:12b',
        'description': 'Gemma 3 12B - Más grande, mejor razonamiento (más lento)',
        'recommended': False
    },
]

def probar_modelo(modelo_info):
    """Prueba un modelo con el prompt de análisis"""
    print(f"\n{'='*70}")
    print(f"🧪 Probando: {modelo_info['name']}")
    print(f"   {modelo_info['description']}")
    if modelo_info['recommended']:
        print(f"   ⭐ RECOMENDADO para tareas educativas")
    print(f"{'='*70}")
    
    inicio = time.time()
    
    resultado = local_ai.generate(
        prompt=PROMPT_ANALISIS,
        model=modelo_info['name'],
        temperature=0.3,  # Baja temperatura para respuestas más precisas
        max_tokens=800,
        top_p=0.9
    )
    
    duracion = time.time() - inicio
    
    if resultado['success']:
        print(f"\n✅ ÉXITO - Tiempo: {duracion:.1f}s")
        print(f"📊 Tokens generados: {resultado['tokens']}")
        print(f"\n📝 RESPUESTA ({len(resultado['text'])} caracteres):")
        print("-" * 70)
        # Mostrar solo los primeros 500 caracteres
        preview = resultado['text'][:500]
        print(preview)
        if len(resultado['text']) > 500:
            print(f"\n... (+ {len(resultado['text']) - 500} caracteres más)")
        print("-" * 70)
        
        # Intentar validar si es JSON
        import json
        try:
            json.loads(resultado['text'])
            print("✅ Respuesta válida en formato JSON")
        except:
            print("⚠️  Respuesta NO es JSON válido")
        
        return {
            'modelo': modelo_info['name'],
            'exito': True,
            'duracion': duracion,
            'tokens': resultado['tokens'],
            'longitud': len(resultado['text'])
        }
    else:
        print(f"\n❌ ERROR: {resultado.get('error')}")
        return {
            'modelo': modelo_info['name'],
            'exito': False,
            'error': resultado.get('error')
        }

def main():
    print("\n" + "="*70)
    print("  PRUEBA DE MODELOS PARA ANÁLISIS DE ESTRUCTURA DE DOCUMENTOS")
    print("="*70)
    
    # Verificar conexión
    if not local_ai.is_available():
        print("\n❌ Servidor Ollama no disponible")
        print("   Verifica la conexión VPN y que el servidor esté corriendo")
        return
    
    print(f"\n✅ Conectado a: {local_ai.base_url}")
    
    # Obtener modelos disponibles
    modelos_disponibles = [m['name'] for m in local_ai.get_models()]
    
    print(f"\n🎯 Se probarán los siguientes modelos:")
    modelos_a_ejecutar = []
    
    for modelo in MODELOS_A_PROBAR:
        if modelo['name'] in modelos_disponibles:
            print(f"   ✓ {modelo['name']} - {modelo['description']}")
            modelos_a_ejecutar.append(modelo)
        else:
            print(f"   ✗ {modelo['name']} - NO DISPONIBLE")
    
    if not modelos_a_ejecutar:
        print("\n❌ Ningún modelo recomendado está disponible")
        return
    
    # Preguntar si continuar
    input(f"\n👉 Presiona ENTER para comenzar las pruebas (tardará ~30-60s por modelo)...")
    
    # Ejecutar pruebas
    resultados = []
    for modelo in modelos_a_ejecutar:
        resultado = probar_modelo(modelo)
        resultados.append(resultado)
        time.sleep(1)  # Pausa entre pruebas
    
    # Resumen
    print("\n\n" + "="*70)
    print("  📊 RESUMEN DE RESULTADOS")
    print("="*70)
    
    exitosos = [r for r in resultados if r['exito']]
    
    if exitosos:
        print(f"\n✅ {len(exitosos)}/{len(resultados)} modelos completaron con éxito\n")
        
        # Ordenar por velocidad
        exitosos.sort(key=lambda x: x['duracion'])
        
        print("🏆 RANKING POR VELOCIDAD:")
        for i, r in enumerate(exitosos, 1):
            print(f"   {i}. {r['modelo']:<25} {r['duracion']:>6.1f}s  ({r['tokens']} tokens)")
        
        print("\n\n🎯 RECOMENDACIÓN:")
        print("-" * 70)
        mejor = exitosos[0]
        print(f"\n✨ Mejor opción: {mejor['modelo']}")
        print(f"   • Velocidad: {mejor['duracion']:.1f} segundos")
        print(f"   • Tokens generados: {mejor['tokens']}")
        print(f"\n💡 Este modelo es ideal para:")
        print(f"   - Analizar estructura de documentos educativos")
        print(f"   - Identificar capítulos y secciones")
        print(f"   - Generar preguntas y respuestas automáticas")
        print("-" * 70)
    else:
        print("\n❌ Ningún modelo completó exitosamente")

if __name__ == '__main__':
    main()
