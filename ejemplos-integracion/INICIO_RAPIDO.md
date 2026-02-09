# 🚀 Guía de Inicio Rápido - Integración Ollama

## ⏱️ Setup en 5 Minutos

### 1. Instalar Ollama (2 min)

**Windows:**
```bash
# Descargar desde https://ollama.ai/download
# O usar winget:
winget install Ollama.Ollama
```

**Linux/Mac:**
```bash
curl https://ollama.ai/install.sh | sh
```

### 2. Descargar un Modelo (2 min)

```bash
# Modelo recomendado: Llama 3.1 8B (4.7 GB)
ollama pull llama3.1:8b

# O modelo más ligero: Gemma 3 4B (2.5 GB)
ollama pull gemma3:4b
```

### 3. Verificar Instalación (30 seg)

```bash
# Listar modelos instalados
ollama list

# Probar el modelo
ollama run llama3.1:8b "Hola, ¿cómo estás?"
```

### 4. Iniciar Servidor (30 seg)

```bash
# Ollama inicia automáticamente
# Verificar que esté corriendo:
curl http://localhost:11434/api/tags
```

---

## 🎯 Opción A: Usar Cliente Directo (Sin Backend)

### Node.js en 3 Comandos

```bash
# 1. Instalar axios
npm install axios

# 2. Copiar cliente
wget https://raw.githubusercontent.com/.../cliente-ollama-nodejs.js

# 3. Ejecutar ejemplo
node cliente-ollama-nodejs.js
```

**Tu código:**
```javascript
const OllamaClient = require('./cliente-ollama-nodejs');
const ollama = new OllamaClient('localhost', 11434);

(async () => {
  const result = await ollama.generate('Explica qué es Node.js');
  console.log(result.text);
})();
```

### Python en 3 Comandos

```bash
# 1. Instalar requests
pip install requests

# 2. Copiar cliente
wget https://raw.githubusercontent.com/.../cliente-ollama-python.py

# 3. Ejecutar ejemplo
python cliente-ollama-python.py
```

**Tu código:**
```python
from cliente_ollama_python import OllamaClient

ollama = OllamaClient('localhost', 11434)
result = ollama.generate('Explica qué es Python')
print(result['text'])
```

---

## 🎯 Opción B: Backend + Frontend Completo

### 1. Clonar Ejemplos

```bash
# Copiar carpeta ejemplos-integracion/
cd ejemplos-integracion
```

### 2. Configurar Backend

```bash
# Instalar dependencias
npm install

# Configurar variables
cp .env.example .env
# Editar .env con tus valores

# Iniciar backend
npm start
```

### 3. Abrir Frontend

```bash
# Simplemente abrir en navegador:
# frontend-html-minimo.html
```

### 4. Probar Integración

```bash
# Ejecutar script de prueba
node test-integracion.js
```

---

## 📱 Integración en Diferentes Frameworks

### React

```javascript
// hooks/useOllama.js
import { useState } from 'react';

export function useOllama() {
  const [loading, setLoading] = useState(false);
  
  const generate = async (message) => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:3000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });
      const data = await response.json();
      return data.reply;
    } finally {
      setLoading(false);
    }
  };
  
  return { generate, loading };
}

// Uso en componente
function ChatComponent() {
  const { generate, loading } = useOllama();
  
  const handleSend = async (message) => {
    const reply = await generate(message);
    console.log(reply);
  };
  
  return <button onClick={() => handleSend('Hola')}>Enviar</button>;
}
```

### Vue.js

```javascript
// composables/useOllama.js
import { ref } from 'vue';

export function useOllama() {
  const loading = ref(false);
  
  const generate = async (message) => {
    loading.value = true;
    try {
      const response = await fetch('http://localhost:3000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });
      const data = await response.json();
      return data.reply;
    } finally {
      loading.value = false;
    }
  };
  
  return { generate, loading };
}

// Uso en componente
<script setup>
import { useOllama } from './composables/useOllama';

const { generate, loading } = useOllama();

const handleSend = async () => {
  const reply = await generate('Hola');
  console.log(reply);
};
</script>
```

### Next.js (API Route)

```javascript
// pages/api/chat.js
import axios from 'axios';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  const { message } = req.body;
  
  try {
    const response = await axios.post('http://localhost:11434/api/generate', {
      model: 'llama3.1:8b',
      prompt: message,
      stream: false
    });
    
    res.status(200).json({ reply: response.data.response });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}

// Uso desde cliente
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: 'Hola' })
});
const data = await response.json();
```

### Angular (Service)

```typescript
// services/ollama.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class OllamaService {
  private apiUrl = 'http://localhost:3000/api';
  
  constructor(private http: HttpClient) {}
  
  generate(message: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/chat`, { message });
  }
}

// Uso en componente
export class ChatComponent {
  constructor(private ollama: OllamaService) {}
  
  sendMessage(message: string) {
    this.ollama.generate(message).subscribe(
      response => console.log(response.reply)
    );
  }
}
```

### Flask (Python Backend)

```python
# app.py
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
OLLAMA_URL = 'http://localhost:11434/api/generate'

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message')
    
    response = requests.post(OLLAMA_URL, json={
        'model': 'llama3.1:8b',
        'prompt': message,
        'stream': False
    })
    
    result = response.json()
    return jsonify({'reply': result['response']})

if __name__ == '__main__':
    app.run(port=3000)
```

### FastAPI (Python Backend Async)

```python
# main.py
from fastapi import FastAPI
from pydantic import BaseModel
import httpx

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.post('/api/chat')
async def chat(request: ChatRequest):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'llama3.1:8b',
                'prompt': request.message,
                'stream': False
            }
        )
        result = response.json()
        return {'reply': result['response']}

# Ejecutar: uvicorn main:app --reload
```

---

## 🧪 Testing Rápido

### Curl

```bash
# Probar Ollama directamente
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "prompt": "Hola",
    "stream": false
  }'

# Probar backend
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola"}'
```

### Postman/Thunder Client

```json
POST http://localhost:3000/api/chat
Content-Type: application/json

{
  "message": "¿Qué es la inteligencia artificial?",
  "model": "llama3.1:8b",
  "temperature": 0.7
}
```

---

## ⚡ Optimizaciones

### 1. Mejorar Velocidad

```javascript
// Reducir tokens generados
const result = await ollama.generate(prompt, 'llama3.1:8b', {
  maxTokens: 50  // En vez de 150
});

// Usar modelo más pequeño
const result = await ollama.generate(prompt, 'gemma3:4b');

// Aumentar timeout si es necesario
axios.defaults.timeout = 60000; // 60 segundos
```

### 2. Usar GPU (Si disponible)

```bash
# Verificar que Ollama use GPU
ollama run llama3.1:8b --verbose

# Debería mostrar: "Using GPU"
```

### 3. Streaming (Respuestas en tiempo real)

```javascript
// Backend con streaming
app.post('/api/chat-stream', async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  
  const response = await axios.post(
    'http://localhost:11434/api/generate',
    { ...req.body, stream: true },
    { responseType: 'stream' }
  );
  
  response.data.on('data', chunk => {
    res.write(chunk);
  });
  
  response.data.on('end', () => {
    res.end();
  });
});
```

---

## 🐛 Problemas Comunes

| Problema | Solución |
|----------|----------|
| `ECONNREFUSED` | `ollama serve` |
| `Model not found` | `ollama pull llama3.1:8b` |
| Muy lento | Usar modelo más pequeño o GPU |
| CORS error | Agregar `app.use(cors())` |
| Timeout | Aumentar `axios.defaults.timeout` |

---

## 📚 Recursos

- [Documentación Completa](GUIA_INTEGRACION_IA.md)
- [Ejemplos de Código](ejemplos-integracion/)
- [Ollama API Docs](https://github.com/ollama/ollama/blob/main/docs/api.md)

---

**¡Listo para empezar!** En menos de 5 minutos puedes tener tu propia aplicación de IA funcionando. 🚀
