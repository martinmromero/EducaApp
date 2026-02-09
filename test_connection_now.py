#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test de conexión al servidor Ollama"""

from material.local_ai_client import local_ai

print("🔍 Verificando servidor Ollama...")
print("=" * 50)

# Check connection
is_connected = local_ai.check_connection()
print(f"✓ Conectado: {is_connected}")

if is_connected:
    status = local_ai.get_status()
    print(f"✓ URL: {status['url']}")
    print(f"✓ Modelos disponibles: {status['models_count']}")
    print(f"✓ Modelo seleccionado: {status['selected_model']}")
    print(f"✓ Tokens ilimitados: {status['unlimited_tokens']}")
else:
    print("❌ Servidor NO disponible")
    print("Posibles causas:")
    print("  1. VPN no conectada")
    print("  2. Servidor apagado")
    print("  3. Problemas de red")

print("=" * 50)
