# 📦 Kit de Integración Ollama - Listo para Exportar

**Esta carpeta es completamente independiente y lista para copiar a cualquier proyecto.**

✅ Todo lo necesario para integrar IA (Ollama) en tus aplicaciones  
✅ Ejemplos en Node.js, Python y HTML  
✅ Documentación completa  
✅ Sin dependencias del proyecto original

---

## 🚀 Inicio Rápido (3 opciones)

### Opción 1: Copiar toda la carpeta
```bash
# Copiar esta carpeta completa a tu proyecto
cp -r ejemplos-integracion /tu/nuevo/proyecto/ollama-integration
cd /tu/nuevo/proyecto/ollama-integration
```

### Opción 2: Solo el cliente
```bash
# Copiar solo cliente-ollama-nodejs.js o cliente-ollama-python.py
npm install axios  # Para Node.js
# o
pip install requests  # Para Python
```

### Opción 3: Backend completo
```bash
npm install
cp .env.example .env
node backend-express-minimo.js
```

---

## 📁 Contenido

### 1. **cliente-ollama-nodejs.js**
Cliente completo en Node.js para interactuar con Ollama.

**Uso:**
```bash
npm install axios
node cliente-ollama-nodejs.js
```

**Características:**
- ✅ Generación de texto
- ✅ Chat con contexto
- ✅ Listar modelos
- ✅ Health check
- ✅ Información de modelos

---

### 2. **cliente-ollama-python.py**
Cliente completo en Python para interactuar con Ollama.

**Uso:**
```bash
pip install requests
python cliente-ollama-python.py
```

**Características:**
- ✅ Generación de texto
- ✅ Chat con contexto
- ✅ Listar modelos
- ✅ Health check
- ✅ Type hints completos

---

### 3. **backend-express-minimo.js**
Backend Express completo con múltiples endpoints para IA.

**Instalación:**
```bash
npm install express axios cors dotenv
```

**Configuración (.env):**
```env
PORT=3000
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=llama3.1:8b
```

**Ejecutar:**
```bash
node backend-express-minimo.js
```

**Endpoints:**
- `GET /health` - Health check del backend
- `GET /api/ia/health` - Verificar conexión con Ollama
- `GET /api/models` - Listar modelos disponibles
- `POST /api/chat` - Chat simple
- `POST /api/chat-context` - Chat con contexto
- `POST /api/generate` - Generación avanzada con prompt personalizado

---

### 4. **frontend-html-minimo.html**
Interfaz web completa lista para usar.

**Características:**
- ✅ Chat interfaz moderna
- ✅ Selección de modelo
- ✅ Indicador de estado
- ✅ Historial de conversación
- ✅ Metadata de respuestas (tokens, tiempo)
- ✅ Diseño responsive

**Uso:**
1. Abrir el archivo HTML en un navegador
2. Configurar URL del backend
3. Seleccionar modelo
4. ¡Empezar a chatear!

---

## 🚀 Inicio Rápido

### Opción 1: Todo Local

```bash
# 1. Instalar Ollama
curl https://ollama.ai/install.sh | sh

# 2. Descargar un modelo
ollama pull llama3.1:8b

# 3. Ejecutar backend
cd ejemplos-integracion
npm install express axios cors dotenv
node backend-express-minimo.js

# 4. Abrir frontend
# Hacer doble clic en frontend-html-minimo.html
```

### Opción 2: Usar Cliente Directo (Sin Backend)

**JavaScript:**
```javascript
const OllamaClient = require('./cliente-ollama-nodejs');
const ollama = new OllamaClient('localhost', 11434);

const result = await ollama.generate('Hola, ¿cómo estás?');
console.log(result.text);
```

**Python:**
```python
from cliente_ollama_python import OllamaClient

ollama = OllamaClient('localhost', 11434)
result = ollama.generate('Hola, ¿cómo estás?')
print(result['text'])
```

---

## 📖 Documentación Completa

Para más información, ver:
- **[GUIA_INTEGRACION_IA.md](../GUIA_INTEGRACION_IA.md)** - Documentación completa
- **[Ollama API Docs](https://github.com/ollama/ollama/blob/main/docs/api.md)** - Documentación oficial

---

## 🔧 Configuración

### Variables de Entorno

Crear archivo `.env`:

```env
# Backend
PORT=3000

# Ollama
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=llama3.1:8b

# Parámetros IA
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=150
AI_TOP_P=0.9
```

### Modelos Recomendados

| Modelo | Tamaño | Uso | RAM Necesaria |
|--------|--------|-----|---------------|
| `llama3.1:8b` | 4.7 GB | General | 8 GB |
| `gemma3:4b` | 2.5 GB | General (ligero) | 4 GB |
| `medgemma-4b-it-Q6_K` | 3.0 GB | Medicina | 6 GB |
| `mistral:7b` | 4.1 GB | General | 8 GB |

---

## 🧪 Testing

### Probar Conexión Ollama

```bash
curl http://localhost:11434/api/tags
```

### Probar Backend

```bash
# Health check
curl http://localhost:3000/health

# Chat simple
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola"}'
```

---

## 🐛 Troubleshooting

### Error: ECONNREFUSED
**Solución:** Verificar que Ollama esté corriendo
```bash
ollama serve
```

### Error: Model not found
**Solución:** Descargar el modelo
```bash
ollama pull llama3.1:8b
```

### Error: CORS
**Solución:** Agregar middleware CORS en backend
```javascript
app.use(cors());
```

---

## 📝 Ejemplos de Peticiones

### Chat Simple
```javascript
fetch('http://localhost:3000/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: '¿Qué es JavaScript?',
    model: 'llama3.1:8b',
    temperature: 0.7
  })
})
.then(res => res.json())
.then(data => console.log(data.reply));
```

### Chat con Contexto
```javascript
fetch('http://localhost:3000/api/chat-context', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    messages: [
      { role: 'user', content: 'Hola' },
      { role: 'assistant', content: 'Hola, ¿en qué puedo ayudarte?' },
      { role: 'user', content: '¿De qué hablamos antes?' }
    ]
  })
})
.then(res => res.json())
.then(data => console.log(data.reply));
```

---

## 🎯 Casos de Uso

1. **Chatbot de atención al cliente**
2. **Asistente de programación**
3. **Tutor educativo**
4. **Generación de contenido**
5. **Análisis de texto**
6. **Simulador de pacientes (como esta app)**

---

## 📚 Recursos Adicionales

- [Ollama GitHub](https://github.com/ollama/ollama)
- [Ollama Models Library](https://ollama.ai/library)
- [Express.js Docs](https://expressjs.com/)
- [Axios Docs](https://axios-http.com/)

---

**¿Necesitas ayuda?** Todos estos ejemplos están probados y listos para usar. Solo ajusta las configuraciones a tu entorno.
