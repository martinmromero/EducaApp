# 🤖 Guía de Integración del Sistema de IA

## 📋 Índice
1. [Arquitectura General](#arquitectura-general)
2. [Componentes del Sistema](#componentes-del-sistema)
3. [Configuración](#configuración)
4. [API Endpoints](#api-endpoints)
5. [Integración Frontend](#integración-frontend)
6. [Integración Backend](#integración-backend)
7. [Ejemplos de Código](#ejemplos-de-código)
8. [Troubleshooting](#troubleshooting)

---

## 📐 Arquitectura General

```
┌─────────────┐      HTTP      ┌─────────────┐      HTTP      ┌─────────────┐
│             │────────────────▶│             │────────────────▶│             │
│  Frontend   │                 │   Backend   │                 │   Ollama    │
│  (Browser)  │◀────────────────│  (Node.js)  │◀────────────────│   Server    │
│             │   JSON API      │             │   JSON API      │             │
└─────────────┘                 └─────────────┘                 └─────────────┘
                                      │
                                      │ PostgreSQL
                                      ▼
                                ┌─────────────┐
                                │  Database   │
                                │ (Contexto + │
                                │  Historial) │
                                └─────────────┘
```

### Flujo de una petición:
1. **Usuario** escribe pregunta → Frontend
2. **Frontend** envía POST a `/api/ia/generar-respuesta`
3. **Backend** obtiene contexto de DB + historial
4. **Backend** construye prompt completo
5. **Backend** envía prompt a Ollama Server
6. **Ollama** genera respuesta usando LLM
7. **Backend** procesa respuesta y agrega metadata
8. **Frontend** recibe respuesta y la muestra

---

## 🔧 Componentes del Sistema

### 1. Frontend (JavaScript)
**Archivo**: `frontend/js/api.js`
- Genera peticiones HTTP al backend
- Maneja respuestas y errores
- No se conecta directamente a Ollama

### 2. Backend (Node.js/Express)
**Archivo**: `backend/routes/ia.js`
- Recibe peticiones del frontend
- Construye prompts contextualizados
- Se conecta a Ollama
- Gestiona fallback si Ollama falla

### 3. Ollama Server
- Servidor LLM externo (puede estar en red local o remoto)
- Ejecuta modelos como Llama, Gemma, Mistral, etc.
- API REST en puerto 11434 (por defecto)

---

## ⚙️ Configuración

### Variables de Entorno (Backend)

Crear archivo `backend/.env`:

```env
# Configuración de Ollama
OLLAMA_HOST=192.168.12.236    # IP del servidor Ollama
OLLAMA_PORT=11434              # Puerto de Ollama (default: 11434)
OLLAMA_MODEL=llama3.1:8b       # Modelo a utilizar

# Parámetros de generación
AI_TEMPERATURE=0.7             # Creatividad (0.0 - 1.0)
AI_MAX_TOKENS=150              # Máximo de tokens a generar
AI_TOP_P=0.9                   # Nucleus sampling

# Base de datos (para contexto)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=simulador_pacientes
DB_USER=postgres
DB_PASSWORD=tu_password
```

### Configuración Frontend

**Archivo**: `frontend/js/config.js`

```javascript
const CONFIG = {
  API_URL: 'http://localhost:3000/api',
  
  OLLAMA: {
    currentModel: 'llama3.1:8b',
    servers: {
      servidor: {
        host: '192.168.12.236',
        port: '11434'
      }
    }
  }
};
```

---

## 🌐 API Endpoints

### 1. Generar Respuesta de IA

**Endpoint**: `POST /api/ia/generar-respuesta`

**Request Body**:
```json
{
  "session_id": "uuid-de-la-sesion",
  "pregunta_estudiante": "¿Cómo te sientes hoy?",
  "caso_id": 1
}
```

**Response** (Exitosa):
```json
{
  "texto": "Me siento un poco nerviosa... no sé por qué.",
  "confianza": 0.9,
  "emociones": ["nerviosismo", "incertidumbre"],
  "metadata": {
    "modo": "ollama",
    "modelo": "llama3.1:8b",
    "tokens": 147,
    "tiempo_ms": 2340,
    "tiempo_total_ms": 2456
  }
}
```

**Response** (Fallback si Ollama no disponible):
```json
{
  "texto": "No sé… me cuesta hablar de eso.",
  "confianza": 0.5,
  "emociones": ["neutral"],
  "metadata": {
    "modo": "simulado_fallback",
    "error": "ECONNREFUSED",
    "modelo": "ninguno"
  }
}
```

### 2. Health Check (Verificar Conexión)

**Endpoint**: `GET /api/ia/health`

**Response**:
```json
{
  "status": "ok",
  "ollama_conectado": true,
  "ollama_url": "192.168.12.236:11434",
  "modelo_configurado": "llama3.1:8b",
  "modelos_disponibles": [
    {
      "name": "llama3.1:8b",
      "modified_at": "2024-01-15T10:30:00Z",
      "size": 4368582144
    },
    {
      "name": "medgemma-4b-it-Q6_K:latest",
      "modified_at": "2024-01-14T15:20:00Z",
      "size": 3221225472
    }
  ]
}
```

---

## 🎨 Integración Frontend

### Función para Generar Respuesta

```javascript
// frontend/js/api.js

const API = {
  async generateResponse(sessionId, question, caseId) {
    try {
      const response = await fetch(`${CONFIG.API_URL}/ia/generar-respuesta`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          pregunta_estudiante: question,
          caso_id: caseId
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      return data;
      
    } catch (error) {
      console.error('Error generando respuesta:', error);
      throw error;
    }
  },

  // Verificar conexión con Ollama
  async checkIAHealth() {
    try {
      const response = await fetch(`${CONFIG.API_URL}/ia/health`);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error verificando IA:', error);
      return { 
        status: 'error', 
        ollama_conectado: false,
        error: error.message 
      };
    }
  }
};
```

### Ejemplo de Uso en el Frontend

```javascript
// En tu aplicación
async function enviarPregunta() {
  const pregunta = document.getElementById('input-pregunta').value;
  const sessionId = getCurrentSessionId();
  const caseId = getCurrentCaseId();
  
  try {
    // Mostrar indicador de carga
    mostrarCargando(true);
    
    // Llamar a la API
    const respuesta = await API.generateResponse(sessionId, pregunta, caseId);
    
    // Mostrar respuesta
    mostrarRespuesta(respuesta.texto);
    
    // Opcional: mostrar metadata
    console.log('Modelo usado:', respuesta.metadata.modelo);
    console.log('Tiempo de respuesta:', respuesta.metadata.tiempo_ms + 'ms');
    console.log('Emociones detectadas:', respuesta.emociones);
    
  } catch (error) {
    mostrarError('No se pudo generar respuesta: ' + error.message);
  } finally {
    mostrarCargando(false);
  }
}
```

---

## ⚙️ Integración Backend

### 1. Instalación de Dependencias

```bash
npm install express axios dotenv pg
```

### 2. Código del Servidor (Simplificado)

```javascript
// backend/routes/ia.js

const express = require('express');
const router = express.Router();
const axios = require('axios');

// Configuración desde variables de entorno
const OLLAMA_HOST = process.env.OLLAMA_HOST || '192.168.12.236';
const OLLAMA_PORT = process.env.OLLAMA_PORT || '11434';
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || 'llama3.1:8b';
const OLLAMA_URL = `http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/generate`;

const AI_TEMPERATURE = parseFloat(process.env.AI_TEMPERATURE) || 0.7;
const AI_MAX_TOKENS = parseInt(process.env.AI_MAX_TOKENS) || 150;
const AI_TOP_P = parseFloat(process.env.AI_TOP_P) || 0.9;

// Función para llamar a Ollama
async function llamarOllama(prompt) {
  try {
    const response = await axios.post(
      OLLAMA_URL,
      {
        model: OLLAMA_MODEL,
        prompt: prompt,
        stream: false,
        options: {
          temperature: AI_TEMPERATURE,
          num_predict: AI_MAX_TOKENS,
          top_p: AI_TOP_P,
          stop: ["\nTerapeuta:", "\nEstudiante:", "\n\n"]
        }
      },
      {
        timeout: 30000,
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );

    return {
      texto: response.data.response.trim(),
      confianza: 0.9,
      metadata: {
        modo: 'ollama',
        modelo: OLLAMA_MODEL,
        tokens: response.data.eval_count || 0,
        tiempo_ms: response.data.total_duration 
          ? Math.round(response.data.total_duration / 1000000) 
          : 0
      }
    };
  } catch (error) {
    console.error('[IA] Error llamando a Ollama:', error.message);
    throw error;
  }
}

// Endpoint para generar respuestas
router.post('/generar-respuesta', async (req, res) => {
  try {
    const { session_id, pregunta_estudiante, caso_id } = req.body;
    
    // 1. Obtener contexto (desde DB u otra fuente)
    const contexto = await obtenerContexto(caso_id);
    
    // 2. Obtener historial de conversación
    const historial = await obtenerHistorial(session_id);
    
    // 3. Construir prompt completo
    const prompt = construirPrompt(contexto, historial, pregunta_estudiante);
    
    // 4. Llamar a Ollama
    let respuesta;
    try {
      const startTime = Date.now();
      respuesta = await llamarOllama(prompt);
      respuesta.metadata.tiempo_total_ms = Date.now() - startTime;
      
    } catch (ollamaError) {
      // Fallback a respuestas simuladas
      console.warn('[IA] Ollama no disponible, usando fallback');
      respuesta = {
        texto: "Prefiero no hablar de ese tema ahora.",
        confianza: 0.5,
        metadata: {
          modo: 'simulado_fallback',
          error: ollamaError.message
        }
      };
    }
    
    res.json(respuesta);
    
  } catch (err) {
    console.error('Error generando respuesta:', err);
    res.status(500).json({ error: 'Error al generar respuesta' });
  }
});

// Health check
router.get('/health', async (req, res) => {
  try {
    const response = await axios.get(
      `http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags`,
      { timeout: 5000 }
    );
    
    res.json({
      status: 'ok',
      ollama_conectado: true,
      ollama_url: `${OLLAMA_HOST}:${OLLAMA_PORT}`,
      modelo_configurado: OLLAMA_MODEL,
      modelos_disponibles: response.data.models || []
    });
  } catch (error) {
    res.json({
      status: 'warning',
      ollama_conectado: false,
      error: error.message
    });
  }
});

module.exports = router;
```

### 3. Construcción del Prompt

```javascript
function construirPrompt(contexto, historial, preguntaActual) {
  let prompt = `${contexto.sistema}\n\n`;
  prompt += `CONTEXTO:\n`;
  prompt += `${contexto.descripcion}\n\n`;
  
  prompt += `CONVERSACIÓN:\n`;
  historial.forEach(msg => {
    prompt += `${msg.rol}: ${msg.contenido}\n`;
  });
  
  prompt += `Usuario: ${preguntaActual}\n`;
  prompt += `Asistente:`;
  
  return prompt;
}
```

---

## 💻 Ejemplos de Código

### Ejemplo Completo: Cliente Simple de Node.js

```javascript
const axios = require('axios');

class OllamaClient {
  constructor(host = 'localhost', port = 11434) {
    this.baseURL = `http://${host}:${port}`;
  }

  async generate(prompt, model = 'llama3.1:8b', options = {}) {
    try {
      const response = await axios.post(
        `${this.baseURL}/api/generate`,
        {
          model: model,
          prompt: prompt,
          stream: false,
          options: {
            temperature: options.temperature || 0.7,
            num_predict: options.maxTokens || 150,
            top_p: options.topP || 0.9,
            stop: options.stopSequences || []
          }
        },
        { timeout: 30000 }
      );

      return {
        text: response.data.response.trim(),
        tokens: response.data.eval_count,
        duration_ms: Math.round(response.data.total_duration / 1000000)
      };
    } catch (error) {
      throw new Error(`Error en Ollama: ${error.message}`);
    }
  }

  async listModels() {
    const response = await axios.get(`${this.baseURL}/api/tags`);
    return response.data.models;
  }

  async checkHealth() {
    try {
      await axios.get(`${this.baseURL}/api/tags`, { timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }
}

// Uso
(async () => {
  const ollama = new OllamaClient('192.168.12.236', 11434);
  
  // Verificar conexión
  const isOnline = await ollama.checkHealth();
  console.log('Ollama online:', isOnline);
  
  // Listar modelos
  const models = await ollama.listModels();
  console.log('Modelos disponibles:', models.map(m => m.name));
  
  // Generar respuesta
  const result = await ollama.generate(
    'Explain machine learning in simple terms.',
    'llama3.1:8b',
    { temperature: 0.7, maxTokens: 100 }
  );
  
  console.log('Respuesta:', result.text);
  console.log('Tokens:', result.tokens);
  console.log('Tiempo:', result.duration_ms + 'ms');
})();
```

### Ejemplo: Cliente Python

```python
import requests
import json

class OllamaClient:
    def __init__(self, host='localhost', port=11434):
        self.base_url = f'http://{host}:{port}'
    
    def generate(self, prompt, model='llama3.1:8b', **options):
        url = f'{self.base_url}/api/generate'
        
        payload = {
            'model': model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': options.get('temperature', 0.7),
                'num_predict': options.get('max_tokens', 150),
                'top_p': options.get('top_p', 0.9)
            }
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return {
            'text': data['response'].strip(),
            'tokens': data.get('eval_count', 0),
            'duration_ms': data.get('total_duration', 0) // 1_000_000
        }
    
    def list_models(self):
        response = requests.get(f'{self.base_url}/api/tags')
        return response.json()['models']

# Uso
ollama = OllamaClient('192.168.12.236', 11434)
result = ollama.generate('Hello, how are you?')
print(result['text'])
```

### Ejemplo: Cliente con Fetch (JavaScript Puro)

```javascript
async function generarRespuestaIA(prompt, modelo = 'llama3.1:8b') {
  const OLLAMA_URL = 'http://192.168.12.236:11434/api/generate';
  
  const response = await fetch(OLLAMA_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: modelo,
      prompt: prompt,
      stream: false,
      options: {
        temperature: 0.7,
        num_predict: 150,
        top_p: 0.9
      }
    })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  
  const data = await response.json();
  return data.response.trim();
}

// Uso
generarRespuestaIA('¿Qué es la inteligencia artificial?')
  .then(respuesta => console.log(respuesta))
  .catch(error => console.error(error));
```

---

## 🔍 Troubleshooting

### Problema: "ECONNREFUSED"
**Causa**: No se puede conectar al servidor Ollama  
**Solución**:
1. Verificar que Ollama esté corriendo: `curl http://192.168.12.236:11434/api/tags`
2. Verificar firewall y que el puerto 11434 esté abierto
3. Verificar la IP en las variables de entorno

### Problema: "Model not found"
**Causa**: El modelo especificado no está instalado  
**Solución**:
```bash
# Listar modelos disponibles
curl http://192.168.12.236:11434/api/tags

# Descargar un modelo
ollama pull llama3.1:8b
```

### Problema: Respuestas muy lentas
**Causa**: Modelo muy grande para el hardware  
**Solución**:
- Usar modelo más pequeño (4B en vez de 8B)
- Reducir `AI_MAX_TOKENS`
- Verificar que GPU esté siendo utilizada

### Problema: Respuestas genéricas
**Causa**: Prompt poco específico o temperatura muy alta  
**Solución**:
- Mejorar el prompt con más contexto
- Reducir `AI_TEMPERATURE` a 0.5
- Agregar ejemplos en el prompt (few-shot learning)

---

## 📦 Resumen de Componentes Necesarios

### Para Frontend:
- ✅ Fetch API o Axios
- ✅ URL del backend (`http://localhost:3000/api`)
- ✅ Manejo de errores y timeouts

### Para Backend:
- ✅ Node.js + Express
- ✅ Axios (para llamar a Ollama)
- ✅ Variables de entorno (host, port, model)
- ✅ Sistema de fallback

### Para Ollama Server:
- ✅ Ollama instalado y corriendo
- ✅ Al menos un modelo descargado
- ✅ Puerto 11434 accesible
- ✅ GPU (opcional, mejora rendimiento)

---

## 🚀 Inicio Rápido en Nueva App

### 1. Instalar Ollama

```bash
# Windows/Linux/Mac
curl https://ollama.ai/install.sh | sh

# Descargar modelo
ollama pull llama3.1:8b

# Verificar
ollama list
```

### 2. Backend Mínimo (5 minutos)

```javascript
// server.js
const express = require('express');
const axios = require('axios');
const app = express();

app.use(express.json());

app.post('/api/chat', async (req, res) => {
  try {
    const response = await axios.post('http://localhost:11434/api/generate', {
      model: 'llama3.1:8b',
      prompt: req.body.message,
      stream: false
    });
    
    res.json({ reply: response.data.response });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(3000, () => console.log('Backend running on :3000'));
```

### 3. Frontend Mínimo (HTML)

```html
<!DOCTYPE html>
<html>
<body>
  <input id="input" type="text" placeholder="Escribe algo...">
  <button onclick="enviar()">Enviar</button>
  <div id="respuesta"></div>

  <script>
    async function enviar() {
      const mensaje = document.getElementById('input').value;
      const res = await fetch('http://localhost:3000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: mensaje })
      });
      const data = await res.json();
      document.getElementById('respuesta').innerText = data.reply;
    }
  </script>
</body>
</html>
```

---

## 📚 Referencias

- **Documentación Ollama**: https://github.com/ollama/ollama/blob/main/docs/api.md
- **Modelos disponibles**: https://ollama.ai/library
- **API Ollama**: `http://localhost:11434/api/generate` (POST)
- **List models**: `http://localhost:11434/api/tags` (GET)

---

**¿Preguntas?** Este sistema está diseñado para ser modular y reutilizable. Puedes integrar solo el cliente de Ollama en cualquier aplicación que necesites.
