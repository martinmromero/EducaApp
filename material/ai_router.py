"""
AI Router — Enrutador de proveedores de IA para EducaApp
=========================================================
Selecciona el cliente correcto según la configuración del usuario:

  - ollama_local   → servidor Ollama en la red interna (LocalAIClient)
  - byok           → API key propia del usuario (OpenAI, Anthropic, compatible)
  - institutional  → configuración compartida de la institución (BYOK institucional)

Interfaz común de todos los backends:
    backend.is_available() -> bool
    backend.generate(prompt, max_tokens, temperature, **kwargs) -> dict
    backend.get_status() -> dict
"""

import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Backend: Ollama local
# ---------------------------------------------------------------------------
class OllamaBackend:
    """Delega en la instancia global de LocalAIClient, con soporte para URL personalizada."""

    def __init__(self, ollama_url: Optional[str] = None):
        from .local_ai_client import local_ai, LocalAIClient
        if ollama_url:
            from urllib.parse import urlparse
            parsed = urlparse(ollama_url)
            host = parsed.hostname or '192.168.12.236'
            port = parsed.port or 11434
            self._client = LocalAIClient(host=host, port=port)
        else:
            self._client = local_ai

    def is_available(self) -> bool:
        return self._client.is_available()

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        return self._client.generate(prompt, **kwargs)

    def get_status(self) -> Dict[str, Any]:
        status = self._client.get_status()
        status['backend'] = 'ollama_local'
        return status


# ---------------------------------------------------------------------------
# Backend: OpenAI y compatibles (Groq, Mistral, OpenRouter, vLLM, LM Studio…)
# ---------------------------------------------------------------------------
class OpenAICompatibleBackend:
    """Cualquier endpoint que siga la API de Chat Completions de OpenAI."""

    PRESET_URLS = {
        'openai': 'https://api.openai.com/v1',
        'gemini': 'https://generativelanguage.googleapis.com/v1beta/openai',
        'groq': 'https://api.groq.com/openai/v1',
        'mistral': 'https://api.mistral.ai/v1',
        'openrouter': 'https://openrouter.ai/api/v1',
        'together': 'https://api.together.xyz/v1',
        'openai_compatible': None,  # requiere base_url explícita
    }

    def __init__(self, api_key: str, model: str, base_url: Optional[str], provider: str):
        self.api_key = api_key
        preset = self.PRESET_URLS.get(provider)
        self.base_url = (base_url or preset or 'https://api.openai.com/v1').rstrip('/')
        self.provider = provider
        # Gemini requiere el prefijo "models/" en el nombre del modelo
        raw_model = model or ('models/gemini-flash-lite-latest' if provider == 'gemini' else 'gpt-4o-mini')
        if provider == 'gemini' and raw_model and not raw_model.startswith('models/'):
            raw_model = f'models/{raw_model}'
        self.model = raw_model

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    def is_available(self) -> bool:
        try:
            r = requests.get(f'{self.base_url}/models', headers=self._headers(), timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, **kwargs) -> Dict[str, Any]:
        try:
            payload = {
                'model': self.model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': max_tokens,
                'temperature': temperature,
            }
            r = requests.post(
                f'{self.base_url}/chat/completions',
                headers=self._headers(),
                json=payload,
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
            text = data['choices'][0]['message']['content'].strip()
            usage = data.get('usage', {})
            return {
                'success': True,
                'text': text,
                'tokens': usage.get('total_tokens', 0),
                'model': self.model,
            }
        except Exception as e:
            logger.error(f'OpenAI-compatible backend error: {e}')
            return {'success': False, 'error': str(e), 'text': None}

    def get_status(self) -> Dict[str, Any]:
        return {
            'backend': 'openai_compatible',
            'connected': self.is_available(),
            'provider': self.provider,
            'model': self.model,
            'base_url': self.base_url,
        }


# ---------------------------------------------------------------------------
# Backend: Anthropic (Claude)
# ---------------------------------------------------------------------------
class AnthropicBackend:
    """API de Anthropic Messages (Claude 3 y posteriores)."""

    BASE_URL = 'https://api.anthropic.com/v1'
    API_VERSION = '2023-06-01'

    def __init__(self, api_key: str, model: str = 'claude-3-haiku-20240307'):
        self.api_key = api_key
        self.model = model or 'claude-3-haiku-20240307'

    def _headers(self):
        return {
            'x-api-key': self.api_key,
            'anthropic-version': self.API_VERSION,
            'Content-Type': 'application/json',
        }

    def is_available(self) -> bool:
        # GET /models existe en la API v1; un 401 indicaría key inválida
        try:
            r = requests.get(f'{self.BASE_URL}/models', headers=self._headers(), timeout=5)
            return r.status_code in (200, 404)  # 404 = autenticado pero endpoint inexistente en versión antigua
        except Exception:
            return False

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, **kwargs) -> Dict[str, Any]:
        try:
            payload = {
                'model': self.model,
                'max_tokens': max_tokens,
                'temperature': temperature,
                'messages': [{'role': 'user', 'content': prompt}],
            }
            r = requests.post(
                f'{self.BASE_URL}/messages',
                headers=self._headers(),
                json=payload,
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
            text = data['content'][0]['text'].strip()
            usage = data.get('usage', {})
            return {
                'success': True,
                'text': text,
                'tokens': usage.get('input_tokens', 0) + usage.get('output_tokens', 0),
                'model': self.model,
            }
        except Exception as e:
            logger.error(f'Anthropic backend error: {e}')
            return {'success': False, 'error': str(e), 'text': None}

    def get_status(self) -> Dict[str, Any]:
        return {
            'backend': 'anthropic',
            'connected': self.is_available(),
            'provider': 'anthropic',
            'model': self.model,
        }


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _build_external_backend(provider: str, api_key: str, model: str, base_url: Optional[str]):
    """Construye el backend correcto para un proveedor externo."""
    if provider == 'anthropic':
        return AnthropicBackend(api_key=api_key, model=model)
    return OpenAICompatibleBackend(
        api_key=api_key,
        model=model,
        base_url=base_url,
        provider=provider,
    )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def get_backend_for_user(user) -> 'OllamaBackend | OpenAICompatibleBackend | AnthropicBackend':
    """
    Devuelve el backend de IA configurado para el usuario.
    Si no tiene configuración o la configuración está incompleta,
    cae de vuelta a OllamaBackend.
    """
    try:
        from .models import UserAIConfig
        config, _ = UserAIConfig.objects.get_or_create(user=user)
    except Exception:
        return OllamaBackend()

    source = config.source

    if source == 'ollama_local':
        return OllamaBackend(ollama_url=config.ollama_url or None)

    if source == 'byok':
        if not config.api_key_encrypted:
            logger.warning('BYOK seleccionado pero sin API key. Usando Ollama.')
            return OllamaBackend()
        return _build_external_backend(
            provider=config.provider or 'openai',
            api_key=config.api_key,
            model=config.model or 'gpt-4o-mini',
            base_url=config.base_url or None,
        )

    if source == 'institutional':
        institution = config.institution
        if institution is None:
            logger.warning('Configuración institucional seleccionada pero sin institución asignada.')
            return OllamaBackend()
        try:
            inst_cfg = institution.ai_config
        except Exception:
            logger.warning(f'Institución {institution.name} sin configuración IA. Usando Ollama.')
            return OllamaBackend()
        if not inst_cfg.is_active or not inst_cfg.api_key_encrypted:
            logger.warning(f'Configuración institucional de {institution.name} inactiva o sin key.')
            return OllamaBackend()
        return _build_external_backend(
            provider=inst_cfg.provider,
            api_key=inst_cfg.api_key,
            model=inst_cfg.model or 'gpt-4o-mini',
            base_url=inst_cfg.base_url or None,
        )

    return OllamaBackend()
