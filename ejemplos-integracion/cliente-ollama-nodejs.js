/**
 * Cliente Ollama para Node.js
 * Ejemplo listo para usar en cualquier aplicación
 * 
 * Instalación:
 * npm install axios
 * 
 * Uso:
 * const OllamaClient = require('./cliente-ollama-nodejs');
 * const ollama = new OllamaClient('192.168.12.236', 11434);
 */

const axios = require('axios');

class OllamaClient {
  /**
   * @param {string} host - IP o hostname del servidor Ollama
   * @param {number} port - Puerto de Ollama (default: 11434)
   */
  constructor(host = 'localhost', port = 11434) {
    this.baseURL = `http://${host}:${port}`;
    this.defaultModel = 'llama3.1:8b';
    this.timeout = 30000; // 30 segundos
  }

  /**
   * Generar respuesta desde Ollama
   * @param {string} prompt - El prompt a enviar
   * @param {string} model - Modelo a usar (opcional)
   * @param {Object} options - Opciones de generación
   * @returns {Promise<Object>} - Respuesta con texto, tokens y metadata
   */
  async generate(prompt, model = null, options = {}) {
    try {
      const response = await axios.post(
        `${this.baseURL}/api/generate`,
        {
          model: model || this.defaultModel,
          prompt: prompt,
          stream: false,
          options: {
            temperature: options.temperature || 0.7,
            num_predict: options.maxTokens || 150,
            top_p: options.topP || 0.9,
            stop: options.stopSequences || []
          }
        },
        { 
          timeout: this.timeout,
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      return {
        success: true,
        text: response.data.response.trim(),
        tokens: response.data.eval_count || 0,
        duration_ms: response.data.total_duration 
          ? Math.round(response.data.total_duration / 1000000)
          : 0,
        model: model || this.defaultModel
      };

    } catch (error) {
      console.error('[OllamaClient] Error:', error.message);
      return {
        success: false,
        error: error.message,
        text: null
      };
    }
  }

  /**
   * Generar respuesta con contexto conversacional
   * @param {Array} messages - Array de mensajes [{role: 'user'|'assistant', content: '...'}]
   * @param {string} model - Modelo a usar
   * @returns {Promise<Object>}
   */
  async chat(messages, model = null) {
    // Convertir mensajes a formato de prompt
    let prompt = '';
    messages.forEach(msg => {
      const role = msg.role === 'user' ? 'Usuario' : 'Asistente';
      prompt += `${role}: ${msg.content}\n`;
    });
    prompt += 'Asistente:';

    return this.generate(prompt, model);
  }

  /**
   * Listar modelos disponibles en el servidor
   * @returns {Promise<Array>} - Lista de modelos
   */
  async listModels() {
    try {
      const response = await axios.get(`${this.baseURL}/api/tags`, {
        timeout: 5000
      });

      return {
        success: true,
        models: response.data.models || [],
        count: (response.data.models || []).length
      };

    } catch (error) {
      return {
        success: false,
        error: error.message,
        models: []
      };
    }
  }

  /**
   * Verificar si el servidor está disponible
   * @returns {Promise<boolean>}
   */
  async checkHealth() {
    try {
      await axios.get(`${this.baseURL}/api/tags`, { timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Obtener información detallada de un modelo
   * @param {string} modelName - Nombre del modelo
   * @returns {Promise<Object>}
   */
  async getModelInfo(modelName) {
    try {
      const response = await axios.post(
        `${this.baseURL}/api/show`,
        { name: modelName },
        { timeout: 5000 }
      );

      return {
        success: true,
        info: response.data
      };

    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }
}

// Ejemplo de uso
async function ejemploUso() {
  const ollama = new OllamaClient('192.168.12.236', 11434);

  // 1. Verificar conexión
  console.log('🔍 Verificando conexión...');
  const isOnline = await ollama.checkHealth();
  console.log('   Ollama online:', isOnline);

  if (!isOnline) {
    console.error('❌ No se pudo conectar al servidor Ollama');
    return;
  }

  // 2. Listar modelos
  console.log('\n📚 Modelos disponibles:');
  const { models } = await ollama.listModels();
  models.forEach(m => {
    console.log(`   - ${m.name} (${(m.size / 1024 / 1024 / 1024).toFixed(2)} GB)`);
  });

  // 3. Generar respuesta simple
  console.log('\n💬 Generando respuesta...');
  const result = await ollama.generate(
    '¿Qué es la inteligencia artificial? Responde en español brevemente.',
    'llama3.1:8b',
    { temperature: 0.7, maxTokens: 100 }
  );

  if (result.success) {
    console.log('   Respuesta:', result.text);
    console.log('   Tokens:', result.tokens);
    console.log('   Tiempo:', result.duration_ms + 'ms');
  } else {
    console.error('   Error:', result.error);
  }

  // 4. Chat con contexto
  console.log('\n🗣️  Chat con contexto...');
  const chatResult = await ollama.chat([
    { role: 'user', content: 'Hola, ¿cómo te llamas?' },
    { role: 'assistant', content: 'Hola, soy un asistente de IA.' },
    { role: 'user', content: '¿En qué puedes ayudarme?' }
  ]);

  if (chatResult.success) {
    console.log('   Respuesta:', chatResult.text);
  }
}

// Ejecutar ejemplo si se corre directamente
if (require.main === module) {
  ejemploUso().catch(console.error);
}

module.exports = OllamaClient;
