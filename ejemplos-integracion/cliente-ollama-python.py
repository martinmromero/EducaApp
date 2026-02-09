"""
Cliente Ollama para Python
Ejemplo listo para usar en cualquier aplicación

Instalación:
pip install requests

Uso:
from cliente_ollama_python import OllamaClient
ollama = OllamaClient('192.168.12.236', 11434)
"""

import requests
import json
from typing import List, Dict, Optional, Any


class OllamaClient:
    """Cliente para interactuar con servidor Ollama"""
    
    def __init__(self, host: str = 'localhost', port: int = 11434):
        """
        Inicializar cliente Ollama
        
        Args:
            host: IP o hostname del servidor Ollama
            port: Puerto de Ollama (default: 11434)
        """
        self.base_url = f'http://{host}:{port}'
        self.default_model = 'llama3.1:8b'
        self.timeout = 30
    
    def generate(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 150,
        top_p: float = 0.9,
        stop_sequences: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generar respuesta desde Ollama
        
        Args:
            prompt: El prompt a enviar
            model: Modelo a usar (opcional)
            temperature: Creatividad (0.0 - 1.0)
            max_tokens: Máximo de tokens a generar
            top_p: Nucleus sampling
            stop_sequences: Secuencias donde detener la generación
            
        Returns:
            Dict con texto, tokens y metadata
        """
        url = f'{self.base_url}/api/generate'
        
        payload = {
            'model': model or self.default_model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
                'top_p': top_p
            }
        }
        
        if stop_sequences:
            payload['options']['stop'] = stop_sequences
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'success': True,
                'text': data['response'].strip(),
                'tokens': data.get('eval_count', 0),
                'duration_ms': data.get('total_duration', 0) // 1_000_000,
                'model': model or self.default_model
            }
            
        except requests.exceptions.RequestException as e:
            print(f'[OllamaClient] Error: {e}')
            return {
                'success': False,
                'error': str(e),
                'text': None
            }
    
    def chat(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generar respuesta con contexto conversacional
        
        Args:
            messages: Lista de mensajes [{'role': 'user'|'assistant', 'content': '...'}]
            model: Modelo a usar
            **kwargs: Parámetros adicionales para generate()
            
        Returns:
            Dict con respuesta
        """
        # Convertir mensajes a formato de prompt
        prompt = ''
        for msg in messages:
            role = 'Usuario' if msg['role'] == 'user' else 'Asistente'
            prompt += f"{role}: {msg['content']}\n"
        prompt += 'Asistente:'
        
        return self.generate(prompt, model, **kwargs)
    
    def list_models(self) -> Dict[str, Any]:
        """
        Listar modelos disponibles en el servidor
        
        Returns:
            Dict con lista de modelos
        """
        try:
            response = requests.get(
                f'{self.base_url}/api/tags',
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            models = data.get('models', [])
            
            return {
                'success': True,
                'models': models,
                'count': len(models)
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'models': []
            }
    
    def check_health(self) -> bool:
        """
        Verificar si el servidor está disponible
        
        Returns:
            True si está online, False si no
        """
        try:
            response = requests.get(
                f'{self.base_url}/api/tags',
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Obtener información detallada de un modelo
        
        Args:
            model_name: Nombre del modelo
            
        Returns:
            Dict con información del modelo
        """
        try:
            response = requests.post(
                f'{self.base_url}/api/show',
                json={'name': model_name},
                timeout=5
            )
            response.raise_for_status()
            
            return {
                'success': True,
                'info': response.json()
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }


def ejemplo_uso():
    """Ejemplo de cómo usar el cliente"""
    
    ollama = OllamaClient('192.168.12.236', 11434)
    
    # 1. Verificar conexión
    print('🔍 Verificando conexión...')
    is_online = ollama.check_health()
    print(f'   Ollama online: {is_online}')
    
    if not is_online:
        print('❌ No se pudo conectar al servidor Ollama')
        return
    
    # 2. Listar modelos
    print('\n📚 Modelos disponibles:')
    result = ollama.list_models()
    if result['success']:
        for model in result['models']:
            size_gb = model['size'] / 1024 / 1024 / 1024
            print(f"   - {model['name']} ({size_gb:.2f} GB)")
    
    # 3. Generar respuesta simple
    print('\n💬 Generando respuesta...')
    result = ollama.generate(
        '¿Qué es la inteligencia artificial? Responde en español brevemente.',
        model='llama3.1:8b',
        temperature=0.7,
        max_tokens=100
    )
    
    if result['success']:
        print(f"   Respuesta: {result['text']}")
        print(f"   Tokens: {result['tokens']}")
        print(f"   Tiempo: {result['duration_ms']}ms")
    else:
        print(f"   Error: {result['error']}")
    
    # 4. Chat con contexto
    print('\n🗣️  Chat con contexto...')
    chat_result = ollama.chat([
        {'role': 'user', 'content': 'Hola, ¿cómo te llamas?'},
        {'role': 'assistant', 'content': 'Hola, soy un asistente de IA.'},
        {'role': 'user', 'content': '¿En qué puedes ayudarme?'}
    ])
    
    if chat_result['success']:
        print(f"   Respuesta: {chat_result['text']}")


if __name__ == '__main__':
    ejemplo_uso()
