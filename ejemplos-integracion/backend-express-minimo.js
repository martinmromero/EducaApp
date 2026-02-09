/**
 * Backend Express Mínimo con Integración Ollama
 * 
 * Instalación:
 * npm install express axios cors dotenv
 * 
 * Uso:
 * node backend-express-minimo.js
 */

require('dotenv').config();
const express = require('express');
const axios = require('axios');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;

// Configuración de Ollama
const OLLAMA_HOST = process.env.OLLAMA_HOST || 'localhost';
const OLLAMA_PORT = process.env.OLLAMA_PORT || '11434';
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || 'llama3.1:8b';
const OLLAMA_URL = `http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/generate`;

// Middleware
app.use(cors());
app.use(express.json());

// Función para llamar a Ollama
async function llamarOllama(prompt, opciones = {}) {
  try {
    const response = await axios.post(
      OLLAMA_URL,
      {
        model: opciones.model || OLLAMA_MODEL,
        prompt: prompt,
        stream: false,
        options: {
          temperature: opciones.temperature || 0.7,
          num_predict: opciones.maxTokens || 150,
          top_p: opciones.topP || 0.9,
          stop: opciones.stopSequences || []
        }
      },
      {
        timeout: 30000,
        headers: { 'Content-Type': 'application/json' }
      }
    );

    return {
      success: true,
      text: response.data.response.trim(),
      tokens: response.data.eval_count || 0,
      duration_ms: response.data.total_duration 
        ? Math.round(response.data.total_duration / 1000000)
        : 0
    };

  } catch (error) {
    console.error('[Ollama] Error:', error.message);
    return {
      success: false,
      error: error.message,
      text: null
    };
  }
}

// ENDPOINTS

// 1. Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString() 
  });
});

// 2. Verificar conexión con Ollama
app.get('/api/ia/health', async (req, res) => {
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
      ollama_url: `${OLLAMA_HOST}:${OLLAMA_PORT}`,
      error: error.message
    });
  }
});

// 3. Endpoint simple de chat
app.post('/api/chat', async (req, res) => {
  try {
    const { message, model, temperature, maxTokens } = req.body;

    if (!message) {
      return res.status(400).json({ error: 'Mensaje requerido' });
    }

    const resultado = await llamarOllama(message, {
      model,
      temperature,
      maxTokens
    });

    if (resultado.success) {
      res.json({
        reply: resultado.text,
        metadata: {
          tokens: resultado.tokens,
          duration_ms: resultado.duration_ms,
          model: model || OLLAMA_MODEL
        }
      });
    } else {
      res.status(500).json({
        error: 'Error al generar respuesta',
        details: resultado.error
      });
    }

  } catch (error) {
    console.error('Error en /api/chat:', error);
    res.status(500).json({ error: error.message });
  }
});

// 4. Endpoint con contexto conversacional
app.post('/api/chat-context', async (req, res) => {
  try {
    const { messages, model } = req.body;

    if (!Array.isArray(messages) || messages.length === 0) {
      return res.status(400).json({ 
        error: 'Array de mensajes requerido' 
      });
    }

    // Construir prompt con contexto
    let prompt = '';
    messages.forEach(msg => {
      const role = msg.role === 'user' ? 'Usuario' : 'Asistente';
      prompt += `${role}: ${msg.content}\n`;
    });
    prompt += 'Asistente:';

    const resultado = await llamarOllama(prompt, { model });

    if (resultado.success) {
      res.json({
        reply: resultado.text,
        metadata: {
          tokens: resultado.tokens,
          duration_ms: resultado.duration_ms
        }
      });
    } else {
      res.status(500).json({
        error: 'Error al generar respuesta',
        details: resultado.error
      });
    }

  } catch (error) {
    console.error('Error en /api/chat-context:', error);
    res.status(500).json({ error: error.message });
  }
});

// 5. Endpoint avanzado con prompt personalizado
app.post('/api/generate', async (req, res) => {
  try {
    const { 
      prompt, 
      systemContext,
      model,
      temperature,
      maxTokens,
      stopSequences 
    } = req.body;

    if (!prompt) {
      return res.status(400).json({ error: 'Prompt requerido' });
    }

    // Construir prompt completo con contexto del sistema
    let fullPrompt = '';
    if (systemContext) {
      fullPrompt = `${systemContext}\n\n${prompt}`;
    } else {
      fullPrompt = prompt;
    }

    const resultado = await llamarOllama(fullPrompt, {
      model,
      temperature,
      maxTokens,
      stopSequences
    });

    if (resultado.success) {
      res.json({
        text: resultado.text,
        tokens: resultado.tokens,
        duration_ms: resultado.duration_ms,
        model: model || OLLAMA_MODEL
      });
    } else {
      res.status(500).json({
        error: 'Error al generar respuesta',
        details: resultado.error
      });
    }

  } catch (error) {
    console.error('Error en /api/generate:', error);
    res.status(500).json({ error: error.message });
  }
});

// 6. Listar modelos disponibles
app.get('/api/models', async (req, res) => {
  try {
    const response = await axios.get(
      `http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags`,
      { timeout: 5000 }
    );

    res.json({
      models: response.data.models || [],
      count: (response.data.models || []).length
    });

  } catch (error) {
    res.status(500).json({ 
      error: 'Error obteniendo modelos',
      details: error.message 
    });
  }
});

// Manejo de errores global
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ 
    error: 'Error interno del servidor',
    message: err.message 
  });
});

// Iniciar servidor
app.listen(PORT, () => {
  console.log(`🚀 Backend corriendo en http://localhost:${PORT}`);
  console.log(`🤖 Ollama configurado en ${OLLAMA_HOST}:${OLLAMA_PORT}`);
  console.log(`📦 Modelo por defecto: ${OLLAMA_MODEL}`);
  console.log(`\nEndpoints disponibles:`);
  console.log(`  GET  /health`);
  console.log(`  GET  /api/ia/health`);
  console.log(`  GET  /api/models`);
  console.log(`  POST /api/chat`);
  console.log(`  POST /api/chat-context`);
  console.log(`  POST /api/generate`);
});

module.exports = app;
