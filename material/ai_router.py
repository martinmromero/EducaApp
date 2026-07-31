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
import time
from datetime import timedelta
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
        # Gemini OpenAI-compatible endpoint usa el nombre del modelo SIN prefijo "models/"
        default_model = {
            'gemini': 'gemini-2.5-flash-lite',
            'anthropic': 'claude-3-haiku-20240307',
            'groq': 'llama-3.1-8b-instant',
            'mistral': 'mistral-small-latest',
            'openrouter': 'openai/gpt-4o-mini',
            'openai': 'gpt-4o-mini',
            'together': 'meta-llama/Llama-3.1-8B-Instruct-Turbo',
            'openai_compatible': 'gpt-4o-mini',
        }.get(provider, 'gpt-4o-mini')
        raw_model = model or default_model
        # Si el usuario ingresó el prefijo "models/" por error, quitarlo
        if provider == 'gemini' and raw_model and raw_model.startswith('models/'):
            raw_model = raw_model[len('models/'):]
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
        payload = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                r = requests.post(
                    f'{self.base_url}/chat/completions',
                    headers=self._headers(),
                    json=payload,
                    timeout=120,
                )
                rate_limit = self._parse_rate_limit_headers(r.headers)
                if r.status_code == 429 and attempt < max_retries:
                    retry_after = r.headers.get('Retry-After')
                    wait = int(retry_after) if retry_after and retry_after.isdigit() else 8 * (attempt + 1)
                    logger.warning(
                        f'{self.provider} rate limit (429) en intento {attempt + 1}/{max_retries + 1}, '
                        f'reintentando en {wait}s...'
                    )
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                data = r.json()
                text = data['choices'][0]['message']['content'].strip()
                usage = data.get('usage', {})
                return {
                    'success': True,
                    'text': text,
                    'tokens': usage.get('total_tokens', 0),
                    'model': self.model,
                    'rate_limit': rate_limit,
                }
            except Exception as e:
                logger.error(f'OpenAI-compatible backend error: {e}')
                return {'success': False, 'error': str(e), 'text': None}
        return {'success': False, 'error': f'Límite de solicitudes de {self.provider} alcanzado (429) tras reintentar.', 'text': None}

    @staticmethod
    def _parse_rate_limit_headers(headers) -> Optional[Dict[str, Any]]:
        """Extrae cupo restante de los headers estilo x-ratelimit-* (Groq, OpenAI,
        compatibles). En Groq, remaining/limit-requests son por día (RPD) y
        remaining/limit-tokens son por minuto (TPM) — ver console.groq.com/docs/rate-limits.
        Devuelve None si el proveedor no manda estos headers."""
        def _num(key):
            val = headers.get(key)
            if val is None:
                return None
            try:
                return int(float(val))
            except (TypeError, ValueError):
                return None

        remaining_requests = _num('x-ratelimit-remaining-requests')
        limit_requests = _num('x-ratelimit-limit-requests')
        if remaining_requests is None and limit_requests is None:
            return None
        return {
            'remaining_requests': remaining_requests,
            'limit_requests': limit_requests,
            'reset_requests_raw': headers.get('x-ratelimit-reset-requests'),
            'remaining_tokens': _num('x-ratelimit-remaining-tokens'),
            'limit_tokens': _num('x-ratelimit-limit-tokens'),
            'reset_tokens_raw': headers.get('x-ratelimit-reset-tokens'),
        }

    def get_status(self) -> Dict[str, Any]:
        ready = self.connected_and_ready()
        return {
            'backend': 'openai_compatible',
            'connected': self.is_available(),
            'ready_for_generation': ready,
            'provider': self.provider,
            'model': self.model,
            'base_url': self.base_url,
        }

    def connected_and_ready(self) -> bool:
        if not self.is_available():
            return False
        return bool(self.model)


# ---------------------------------------------------------------------------
# Backend: Gemini nativo
# ---------------------------------------------------------------------------
class GeminiBackend:
    """API nativa de Google Gemini para evitar falsos 404 del endpoint OpenAI-compatible."""

    BASE_URL = 'https://generativelanguage.googleapis.com/v1beta'

    def __init__(self, api_key: str, model: str = 'gemini-2.5-flash-lite'):
        self.api_key = api_key
        self.model = (model or 'gemini-2.5-flash-lite').strip()
        self._last_error = ''
        if self.model.startswith('models/'):
            self.model = self.model[len('models/'):]
        if not self.model.startswith('gemini-'):
            self.model = 'gemini-2.5-flash-lite'

    def _params(self):
        return {'key': self.api_key}

    def _list_models(self):
        try:
            r = requests.get(
                f'{self.BASE_URL}/models',
                params=self._params(),
                timeout=8,
            )
            if r.status_code != 200:
                self._last_error = f'HTTP {r.status_code} al listar modelos de Gemini'
                return False, []
            data = r.json()
            models = data.get('models', []) or []
            names = []
            for m in models:
                name = (m.get('name') or '').strip()
                if name.startswith('models/'):
                    name = name[len('models/'):]
                if name:
                    names.append(name)
            self._last_error = ''
            return True, names
        except Exception as e:
            self._last_error = str(e)
            return False, []

    def _model_ready(self):
        ok, model_names = self._list_models()
        if not ok:
            return False
        if not model_names:
            self._last_error = 'No se pudieron obtener modelos desde Gemini'
            return False
        if self.model in model_names:
            self._last_error = ''
            return True

        # Aceptar alias/versiones frecuentes (ej: gemini-2.5-flash vs gemini-2.5-flash-latest)
        wanted = self.model.lower().strip()
        normalized = [m.lower().strip() for m in model_names]
        if any(m.startswith(wanted) or wanted.startswith(m) for m in normalized):
            self._last_error = ''
            return True

        # Fallback adicional para variantes '-latest'
        alt_wanted = wanted.replace('-latest', '')
        if any(m.replace('-latest', '').startswith(alt_wanted) for m in normalized):
            self._last_error = ''
            return True

        self._last_error = f'Modelo no disponible en Gemini: {self.model}'
        return False

    def is_available(self) -> bool:
        ok, _ = self._list_models()
        return ok

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7,
                 thinking_budget: int = 0, **kwargs) -> Dict[str, Any]:
        generation_config = {
            'temperature': temperature,
            'maxOutputTokens': max_tokens,
        }
        # Los modelos 2.x+ (2.5, 3.x) tienen "thinking" activado por defecto, y esos
        # tokens de razonamiento SALEN del mismo presupuesto que maxOutputTokens —
        # con thinking prendido, el modelo puede gastar 90%+ del presupuesto
        # "pensando" antes de escribir la respuesta visible, dejando muy poco (a
        # veces nada) para el texto real. Para extracción estructurada como esta
        # (generar preguntas de un texto ya dado) no hace falta razonamiento, así
        # que lo desactivamos por default para no perder presupuesto de salida.
        # gemini-1.x no soporta thinkingConfig — no mandarlo para esos modelos.
        model_major = self.model.replace('gemini-', '').split('-')[0].split('.')[0]
        if model_major.isdigit() and int(model_major) >= 2:
            generation_config['thinkingConfig'] = {'thinkingBudget': thinking_budget}

        payload = {
            'contents': [
                {
                    'role': 'user',
                    'parts': [{'text': prompt}],
                }
            ],
            'generationConfig': generation_config,
        }

        # El free tier de Gemini es estricto en requests por minuto (10-15 según
        # modelo): un chunk de documento que falla por 429 no debería perderse sin
        # más — reintentamos un par de veces respetando Retry-After si viene.
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                r = requests.post(
                    f'{self.BASE_URL}/models/{self.model}:generateContent',
                    params=self._params(),
                    json=payload,
                    timeout=120,
                )
                if r.status_code == 429 and attempt < max_retries:
                    wait = self._retry_wait_seconds(r, attempt)
                    logger.warning(
                        f'Gemini rate limit (429) en intento {attempt + 1}/{max_retries + 1}, '
                        f'reintentando en {wait}s...'
                    )
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                data = r.json()
                candidates = data.get('candidates') or []
                text_parts = []
                finish_reason = ''
                if candidates:
                    finish_reason = candidates[0].get('finishReason', '') or ''
                    content = candidates[0].get('content', {}) or {}
                    for part in content.get('parts', []) or []:
                        if isinstance(part, dict) and part.get('text'):
                            text_parts.append(part['text'])
                text = ''.join(text_parts).strip()
                usage = data.get('usageMetadata', {})
                if finish_reason == 'MAX_TOKENS':
                    logger.warning(
                        f'Gemini cortó la respuesta por MAX_TOKENS (max_tokens={max_tokens}, '
                        f'thinking_tokens={usage.get("thoughtsTokenCount", 0)}, model={self.model}). '
                        'El texto puede venir incompleto.'
                    )
                return {
                    'success': True,
                    'text': text,
                    'tokens': usage.get('totalTokenCount', 0),
                    'model': self.model,
                    'truncated': finish_reason == 'MAX_TOKENS',
                }
            except Exception as e:
                logger.error(f'Gemini backend error: {e}')
                return {'success': False, 'error': str(e), 'text': None}
        return {'success': False, 'error': 'Límite de solicitudes de Gemini alcanzado (429) tras reintentar.', 'text': None}

    @staticmethod
    def _retry_wait_seconds(response, attempt, default_base=8):
        retry_after = response.headers.get('Retry-After')
        if retry_after and retry_after.isdigit():
            return int(retry_after)
        return default_base * (attempt + 1)

    def get_status(self) -> Dict[str, Any]:
        connected = self.is_available()
        ready = connected and self._model_ready()
        return {
            'backend': 'gemini',
            'connected': connected,
            'ready_for_generation': ready,
            'error': self._last_error,
            'provider': 'gemini',
            'model': self.model,
            'base_url': self.BASE_URL,
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
# Listado dinámico de modelos disponibles por proveedor
# ---------------------------------------------------------------------------
def list_models_for_provider(provider: str, api_key: str, base_url: Optional[str] = None):
    """
    Consulta al proveedor la lista de modelos disponibles para esa API key,
    para no depender de una lista estática que queda obsoleta.
    Devuelve (success: bool, models: list[str], error: str).
    """
    if not api_key:
        return False, [], 'Ingresá una API Key para poder listar los modelos.'

    try:
        if provider == 'gemini':
            r = requests.get(
                f'{GeminiBackend.BASE_URL}/models',
                params={'key': api_key},
                timeout=10,
            )
            if r.status_code != 200:
                return False, [], f'El proveedor respondió con error HTTP {r.status_code}.'
            data = r.json()
            models = []
            for m in data.get('models', []) or []:
                methods = m.get('supportedGenerationMethods') or []
                if methods and 'generateContent' not in methods:
                    continue
                name = (m.get('name') or '').strip()
                if name.startswith('models/'):
                    name = name[len('models/'):]
                if name:
                    models.append(name)
            return True, sorted(set(models)), ''

        if provider == 'anthropic':
            r = requests.get(
                f'{AnthropicBackend.BASE_URL}/models',
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': AnthropicBackend.API_VERSION,
                },
                timeout=10,
            )
            if r.status_code != 200:
                return False, [], f'El proveedor respondió con error HTTP {r.status_code}.'
            data = r.json()
            models = [m.get('id') for m in data.get('data', []) or [] if m.get('id')]
            return True, models, ''

        # OpenAI y compatibles (Groq, Mistral, OpenRouter, Together, endpoints propios)
        preset = OpenAICompatibleBackend.PRESET_URLS.get(provider)
        resolved_base_url = (base_url or preset or 'https://api.openai.com/v1').rstrip('/')
        r = requests.get(
            f'{resolved_base_url}/models',
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=10,
        )
        if r.status_code != 200:
            return False, [], f'El proveedor respondió con error HTTP {r.status_code}.'
        data = r.json()
        entries = data.get('data', data if isinstance(data, list) else []) or []
        models = [m.get('id') for m in entries if isinstance(m, dict) and m.get('id')]
        return True, sorted(set(models)), ''

    except Exception as e:
        logger.error(f'Error listando modelos de {provider}: {e}')
        return False, [], 'No se pudo conectar con el proveedor. Verificá la API Key e intentá de nuevo.'


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _build_external_backend(provider: str, api_key: str, model: str, base_url: Optional[str]):
    """Construye el backend correcto para un proveedor externo."""
    if provider == 'gemini':
        return GeminiBackend(api_key=api_key, model=model)
    if provider == 'anthropic':
        return AnthropicBackend(api_key=api_key, model=model)
    return OpenAICompatibleBackend(
        api_key=api_key,
        model=model,
        base_url=base_url,
        provider=provider,
    )


def _parse_duration_to_seconds(raw: Optional[str]) -> Optional[float]:
    """Parsea duraciones estilo Groq ("2m59.56s", "7.66s", "1h2m3s") a segundos."""
    if not raw:
        return None
    import re
    match = re.match(r'^(?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?$', raw.strip())
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    total = 0.0
    if hours:
        total += int(hours) * 3600
    if minutes:
        total += int(minutes) * 60
    if seconds:
        total += float(seconds)
    return total if (hours or minutes or seconds) else None


class GlobalFallbackBackend:
    """Envuelve el backend real del fallback de demo (GlobalAIConfig) para
    registrar, después de cada llamada de generación real, el cupo restante que
    haya informado el proveedor (hoy solo Groq expone RPD/TPM en los headers de
    respuesta). No cambia el comportamiento del backend, solo lo observa.
    """
    def __init__(self, inner, config_id):
        self._inner = inner
        self._config_id = config_id

    def is_available(self):
        return self._inner.is_available()

    def get_status(self):
        return self._inner.get_status()

    def generate(self, *args, **kwargs):
        result = self._inner.generate(*args, **kwargs)
        rate_limit = result.get('rate_limit') if isinstance(result, dict) else None
        if rate_limit:
            self._save_quota_snapshot(rate_limit)
        return result

    def refresh_quota(self):
        """Pide un mínimo indispensable (1 token de salida, prompt de una letra)
        solo para leer los headers de cupo de la respuesta — no genera preguntas.
        Sigue consumiendo 1 request contra el RPD del proveedor (no hay forma de
        conocer el cupo sin gastar una llamada), pero el gasto de TPM es
        despreciable. Pensado para llamarse como mucho una vez cada varios
        minutos (ver `ensure_fresh_demo_quota`), no en cada carga de página.
        """
        try:
            self.generate(prompt='.', max_tokens=1, temperature=0)
        except Exception as e:
            logger.warning(f'No se pudo refrescar el cupo del fallback global: {e}')

    def _save_quota_snapshot(self, rate_limit):
        try:
            from django.utils import timezone
            from .models import GlobalAIConfig
            now = timezone.now()
            reset_seconds = _parse_duration_to_seconds(rate_limit.get('reset_requests_raw'))
            GlobalAIConfig.objects.filter(pk=self._config_id).update(
                quota_checked_at=now,
                quota_remaining_requests=rate_limit.get('remaining_requests'),
                quota_limit_requests=rate_limit.get('limit_requests'),
                quota_requests_reset_at=(now + timedelta(seconds=reset_seconds)) if reset_seconds else None,
                quota_remaining_tokens=rate_limit.get('remaining_tokens'),
                quota_limit_tokens=rate_limit.get('limit_tokens'),
            )
        except Exception as e:
            logger.warning(f'No se pudo guardar el snapshot de cupo del fallback global: {e}')


def _global_demo_backend():
    """
    Devuelve el backend construido a partir de GlobalAIConfig (fallback de
    demo, editable solo desde Django Admin) si hay uno activo y con key,
    o None si no está configurado.
    """
    try:
        from .models import GlobalAIConfig
        cfg = GlobalAIConfig.objects.filter(is_active=True).first()
    except Exception:
        return None
    if cfg is None or not cfg.api_key_encrypted:
        return None
    model = cfg.model or ('gemini-2.5-flash-lite' if cfg.provider == 'gemini' else 'gpt-4o-mini')
    try:
        backend = _build_external_backend(
            provider=cfg.provider or 'gemini',
            api_key=cfg.api_key,
            model=model,
            base_url=None,
        )
        return GlobalFallbackBackend(backend, cfg.id)
    except Exception:
        return None


def get_global_demo_quota():
    """Último cupo conocido del fallback de demo (GlobalAIConfig activo), tomado
    de la última llamada real (generación de preguntas o ping de refresco vía
    `ensure_fresh_demo_quota`) que se haya hecho con esa key.
    Devuelve None si no hay fallback activo o todavía no se registró ningún cupo."""
    try:
        from .models import GlobalAIConfig
        cfg = GlobalAIConfig.objects.filter(is_active=True).first()
    except Exception:
        return None
    if cfg is None or cfg.quota_checked_at is None:
        return None
    return {
        'provider': cfg.provider,
        'checked_at': cfg.quota_checked_at,
        'remaining_requests': cfg.quota_remaining_requests,
        'limit_requests': cfg.quota_limit_requests,
        'requests_reset_at': cfg.quota_requests_reset_at,
        'remaining_tokens': cfg.quota_remaining_tokens,
        'limit_tokens': cfg.quota_limit_tokens,
    }


def ensure_fresh_demo_quota(max_age_seconds=300):
    """Si el fallback global está activo y el último cupo conocido tiene más de
    `max_age_seconds` (o nunca se registró ninguno), hace un ping mínimo
    (`GlobalFallbackBackend.refresh_quota`) para refrescarlo antes de leerlo.

    El throttle es a propósito: `GlobalAIConfig` es una única fila compartida
    por todos los usuarios, así que sin este límite, cada carga de pantalla de
    cada docente dispararía un ping — con este chequeo, como mucho se gasta
    una request extra cada `max_age_seconds`, sin importar cuánta gente esté
    mirando la pantalla al mismo tiempo. Llamar antes de `get_global_demo_quota()`
    en cualquier vista que muestre el cupo.
    """
    try:
        from django.utils import timezone
        from .models import GlobalAIConfig
        cfg = GlobalAIConfig.objects.filter(is_active=True).first()
    except Exception:
        return
    if cfg is None or not cfg.api_key_encrypted:
        return
    if cfg.quota_checked_at is not None:
        age = (timezone.now() - cfg.quota_checked_at).total_seconds()
        if age < max_age_seconds:
            return
    backend = _global_demo_backend()
    if backend is not None:
        backend.refresh_quota()


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

    if source == 'shared_demo':
        fallback = _global_demo_backend()
        if fallback is not None:
            return fallback
        logger.warning('shared_demo seleccionado pero no hay GlobalAIConfig activa con key. Usando Ollama.')
        return OllamaBackend()

    if source == 'ollama_local':
        ollama = OllamaBackend(ollama_url=config.ollama_url or None)
        if ollama.is_available():
            return ollama
        fallback = _global_demo_backend()
        if fallback is not None:
            logger.info('Ollama no disponible, usando fallback de demo global.')
            return fallback
        return ollama

    if source == 'byok':
        if not config.api_key_encrypted:
            logger.warning('BYOK seleccionado pero sin API key. Usando Ollama.')
            return OllamaBackend()
        provider_defaults = {
            'gemini': 'gemini-2.5-flash-lite',
            'anthropic': 'claude-3-haiku-20240307',
            'groq': 'llama-3.1-8b-instant',
            'mistral': 'mistral-small-latest',
            'openrouter': 'openai/gpt-4o-mini',
            'openai': 'gpt-4o-mini',
            'openai_compatible': 'gpt-4o-mini',
        }
        model = config.model or provider_defaults.get(config.provider or 'openai', 'gpt-4o-mini')
        if config.provider == 'gemini' and not model.startswith('gemini-'):
            model = 'gemini-2.5-flash-lite'
        return _build_external_backend(
            provider=config.provider or 'openai',
            api_key=config.api_key,
            model=model,
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
        inst_model = inst_cfg.model or {
            'openai': 'gpt-4o-mini',
            'anthropic': 'claude-3-haiku-20240307',
            'openai_compatible': 'gpt-4o-mini',
        }.get(inst_cfg.provider, 'gpt-4o-mini')
        return _build_external_backend(
            provider=inst_cfg.provider,
            api_key=inst_cfg.api_key,
            model=inst_model,
            base_url=inst_cfg.base_url or None,
        )

    return OllamaBackend()
