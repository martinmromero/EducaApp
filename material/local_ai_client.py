"""
Cliente para servidor local de IA (Ollama)
=========================================================
Conexión al servidor intranet para procesamiento de documentos sin límite de tokens.
Basado en ejemplos de integración del proyecto.
"""

import requests
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LocalAIClient:
    """Cliente para servidor local de IA (Ollama)"""
    
    def __init__(self, host: str = "192.168.12.236", port: int = 11434):
        self.base_url = f"http://{host}:{port}"
        self.timeout = 5  # segundos
        self._last_check = None
        self._is_available = False
        self.default_model = 'llama3.1:8b'
        self.selected_model = 'llama3.1:8b'  # Modelo actualmente seleccionado
        
    def check_connection(self) -> bool:
        """
        Verifica si el servidor Ollama está disponible.
        
        Returns:
            bool: True si está conectado
        """
        try:
            # Usar el endpoint de tags de Ollama
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=self.timeout
            )
            self._is_available = response.status_code == 200
            self._last_check = datetime.now()
            return self._is_available
        except Exception as e:
            logger.debug(f"Servidor Ollama no disponible: {e}")
            self._is_available = False
            self._last_check = datetime.now()
            return False
    
    def get_models(self) -> List[Dict[str, any]]:
        """
        Obtiene lista de modelos disponibles en Ollama.
        
        Returns:
            Lista de modelos con sus detalles
        """
        if not self.is_available():
            return []
        
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                
                return [
                    {
                        'name': model.get('name', ''),
                        'model': model.get('model', model.get('name', '')),
                        'size': model.get('size', 0),
                        'modified_at': model.get('modified_at', ''),
                        'details': model.get('details', {}),
                        'digest': model.get('digest', '')
                    }
                    for model in models
                ]
            
            return []
            
        except Exception as e:
            logger.error(f"Error al obtener modelos: {e}")
            return []
    
    def is_available(self) -> bool:
        """
        Verifica estado de disponibilidad (con cache de 30 segundos).
        
        Returns:
            bool: True si está disponible
        """
        # Si no se ha verificado nunca o pasaron más de 30 segundos
        if (self._last_check is None or 
            (datetime.now() - self._last_check).total_seconds() > 30):
            self.check_connection()
        
        return self._is_available
    
    def get_status(self) -> Dict[str, any]:
        """
        Obtiene estado completo del servidor.
        
        Returns:
            Dict con información de estado
        """
        is_connected = self.is_available()
        
        status = {
            'connected': is_connected,
            'url': self.base_url,
            'last_check': self._last_check.isoformat() if self._last_check else None,
            'models_count': 0,
            'unlimited_tokens': is_connected,  # Si está conectado, tokens ilimitados
            'selected_model': self.selected_model,
            'default_model': self.default_model
        }
        
        if is_connected:
            models = self.get_models()
            status['models_count'] = len(models)
            status['models'] = models
        
        return status
    
    def set_model(self, model_name: str) -> bool:
        """
        Cambia el modelo seleccionado.
        
        Args:
            model_name: Nombre del modelo a usar
        
        Returns:
            True si el modelo existe y se cambió exitosamente
        """
        if not self.is_available():
            return False
        
        # Verificar que el modelo exista
        available_models = [m['name'] for m in self.get_models()]
        if model_name in available_models:
            self.selected_model = model_name
            logger.info(f"Modelo cambiado a: {model_name}")
            return True
        else:
            logger.warning(f"Modelo {model_name} no encontrado")
            return False
    
    def get_current_model(self) -> str:
        """
        Obtiene el modelo actualmente seleccionado.
        
        Returns:
            Nombre del modelo actual
        """
        return self.selected_model
    
    def generate(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 150,
        top_p: float = 0.9,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Genera respuesta desde Ollama.
        
        Args:
            prompt: El prompt a enviar
            model: Modelo a usar (opcional, usa default si no se especifica)
            temperature: Creatividad (0.0 - 1.0)
            max_tokens: Máximo de tokens a generar
            top_p: Nucleus sampling
            stream: Si usar streaming o no
        
        Returns:
            Dict con texto, tokens y metadata
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'Servidor no disponible',
                'text': None
            }
        
        try:
            payload = {
                'model': model or self.selected_model,  # Usar modelo seleccionado si no se especifica
                'prompt': prompt,
                'stream': stream,
                'options': {
                    'temperature': temperature,
                    'num_predict': max_tokens,
                    'top_p': top_p
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120  # Timeout extendido para generaciones complejas
            )
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'success': True,
                'text': data.get('response', '').strip(),
                'tokens': data.get('eval_count', 0),
                'duration_ms': data.get('total_duration', 0) // 1_000_000,
                'model': model or self.default_model
            }
            
        except Exception as e:
            logger.error(f"Error al generar respuesta: {e}")
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
        Genera respuesta con contexto conversacional.
        
        Args:
            messages: Lista de mensajes [{'role': 'user'|'assistant', 'content': '...'}]
            model: Modelo a usar
            **kwargs: Parámetros adicionales
        
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


# Instancia global del cliente
local_ai = LocalAIClient()
