"""
Script de prueba para verificar la conexión al servidor local de IA
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'educaapp.settings')
import django
django.setup()

from material.local_ai_client import local_ai

print("=" * 60)
print("PRUEBA DE CONEXIÓN AL SERVIDOR OLLAMA")
print("=" * 60)
print()

# Verificar conexión
print("1. Verificando conexión a Ollama...")
is_connected = local_ai.check_connection()

if is_connected:
    print("   ✓ CONECTADO al servidor:", local_ai.base_url)
    print()
    
    # Obtener modelos
    print("2. Obteniendo lista de modelos...")
    models = local_ai.get_models()
    
    if models:
        print(f"   ✓ Se encontraron {len(models)} modelo(s):")
        print()
        for i, model in enumerate(models, 1):
            print(f"   {i}. {model.get('name', 'N/A')}")
            if model.get('size'):
                size_gb = model['size'] / 1024 / 1024 / 1024
                print(f"      Tamaño: {size_gb:.2f} GB")
            if model.get('modified_at'):
                print(f"      Modificado: {model['modified_at']}")
            print()
    else:
        print("   ⚠ No se encontraron modelos")
        
    # Obtener estado completo
    print("3. Estado completo del servidor:")
    status = local_ai.get_status()
    print(f"   - Conectado: {status['connected']}")
    print(f"   - URL: {status['url']}")
    print(f"   - Modelos disponibles: {status['models_count']}")
    print(f"   - Tokens ilimitados: {status['unlimited_tokens']}")
    
    # Prueba de generación simple
    if models:
        print()
        print("4. Prueba de generación de texto...")
        result = local_ai.generate(
            "Di solo 'Hola' en español",
            model=models[0]['name'],
            max_tokens=10
        )
        
        if result['success']:
            print(f"   ✓ Respuesta: {result['text']}")
            print(f"   - Tokens: {result['tokens']}")
            print(f"   - Tiempo: {result['duration_ms']}ms")
        else:
            print(f"   ✗ Error: {result.get('error')}")
    
else:
    print("   ✗ NO CONECTADO")
    print("   Verifica que:")
    print("   - El servidor Ollama esté corriendo en", local_ai.base_url)
    print("   - Estés conectado a la VPN")
    print("   - El firewall permita la conexión al puerto 11434")

print()
print("=" * 60)
