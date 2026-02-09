#!/usr/bin/env node

/**
 * Script de prueba rápida para verificar integración con Ollama
 * 
 * Uso:
 * node test-integracion.js
 */

const axios = require('axios');

// Colores para la terminal
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

// Configuración
const OLLAMA_HOST = process.env.OLLAMA_HOST || 'localhost';
const OLLAMA_PORT = process.env.OLLAMA_PORT || '11434';
const BASE_URL = `http://${OLLAMA_HOST}:${OLLAMA_PORT}`;

console.log(`${colors.cyan}
╔═══════════════════════════════════════════════════════╗
║  🧪 Script de Prueba - Integración Ollama           ║
╚═══════════════════════════════════════════════════════╝
${colors.reset}`);

async function testConnection() {
  console.log(`\n${colors.blue}[1/5]${colors.reset} Probando conexión con Ollama...`);
  console.log(`      URL: ${BASE_URL}`);
  
  try {
    const response = await axios.get(`${BASE_URL}/api/tags`, { timeout: 5000 });
    console.log(`      ${colors.green}✓ Conexión exitosa${colors.reset}`);
    return response.data;
  } catch (error) {
    console.log(`      ${colors.red}✗ Error: ${error.message}${colors.reset}`);
    console.log(`\n${colors.yellow}Posibles soluciones:${colors.reset}`);
    console.log(`  1. Verificar que Ollama esté corriendo: ${colors.cyan}ollama serve${colors.reset}`);
    console.log(`  2. Verificar la IP: ${OLLAMA_HOST}`);
    console.log(`  3. Verificar el puerto: ${OLLAMA_PORT}`);
    process.exit(1);
  }
}

async function listModels(data) {
  console.log(`\n${colors.blue}[2/5]${colors.reset} Modelos disponibles:`);
  
  if (!data.models || data.models.length === 0) {
    console.log(`      ${colors.yellow}⚠ No hay modelos instalados${colors.reset}`);
    console.log(`\n${colors.yellow}Instalar un modelo:${colors.reset}`);
    console.log(`      ${colors.cyan}ollama pull llama3.1:8b${colors.reset}`);
    process.exit(1);
  }
  
  data.models.forEach((model, index) => {
    const sizeGB = (model.size / 1024 / 1024 / 1024).toFixed(2);
    console.log(`      ${index + 1}. ${colors.green}${model.name}${colors.reset} (${sizeGB} GB)`);
  });
  
  return data.models[0].name; // Retornar primer modelo para prueba
}

async function testGeneration(modelName) {
  console.log(`\n${colors.blue}[3/5]${colors.reset} Probando generación de texto...`);
  console.log(`      Modelo: ${colors.cyan}${modelName}${colors.reset}`);
  console.log(`      Prompt: "¿Qué es la programación?"`);
  
  const startTime = Date.now();
  
  try {
    const response = await axios.post(
      `${BASE_URL}/api/generate`,
      {
        model: modelName,
        prompt: '¿Qué es la programación? Responde brevemente en español.',
        stream: false,
        options: {
          temperature: 0.7,
          num_predict: 50
        }
      },
      { timeout: 30000 }
    );
    
    const duration = Date.now() - startTime;
    const text = response.data.response.trim();
    const tokens = response.data.eval_count || 0;
    
    console.log(`\n      ${colors.green}✓ Respuesta generada:${colors.reset}`);
    console.log(`      "${text}"`);
    console.log(`\n      📊 Estadísticas:`);
    console.log(`         • Tokens: ${tokens}`);
    console.log(`         • Tiempo: ${duration}ms`);
    console.log(`         • Velocidad: ${(tokens / (duration / 1000)).toFixed(2)} tokens/seg`);
    
    return true;
    
  } catch (error) {
    console.log(`      ${colors.red}✗ Error generando respuesta: ${error.message}${colors.reset}`);
    return false;
  }
}

async function testBackend() {
  console.log(`\n${colors.blue}[4/5]${colors.reset} Probando backend Express (opcional)...`);
  
  const backendUrl = 'http://localhost:3000';
  
  try {
    const response = await axios.get(`${backendUrl}/health`, { timeout: 3000 });
    console.log(`      ${colors.green}✓ Backend funcionando en ${backendUrl}${colors.reset}`);
    
    // Probar endpoint de IA
    try {
      const iaHealth = await axios.get(`${backendUrl}/api/ia/health`, { timeout: 3000 });
      console.log(`      ${colors.green}✓ Endpoint de IA funcionando${colors.reset}`);
      console.log(`        Modelo configurado: ${iaHealth.data.modelo_configurado}`);
    } catch {
      console.log(`      ${colors.yellow}⚠ Endpoint /api/ia/health no disponible${colors.reset}`);
    }
    
  } catch (error) {
    console.log(`      ${colors.yellow}⚠ Backend no está corriendo${colors.reset}`);
    console.log(`        Iniciar con: ${colors.cyan}node backend-express-minimo.js${colors.reset}`);
  }
}

async function showSummary() {
  console.log(`\n${colors.blue}[5/5]${colors.reset} Resumen:`);
  console.log(`
  ${colors.green}✓ Ollama está funcionando correctamente${colors.reset}
  
  📚 Próximos pasos:
  
  1. Usar el cliente Node.js:
     ${colors.cyan}node cliente-ollama-nodejs.js${colors.reset}
  
  2. Iniciar el backend:
     ${colors.cyan}node backend-express-minimo.js${colors.reset}
  
  3. Abrir la interfaz web:
     ${colors.cyan}frontend-html-minimo.html${colors.reset}
  
  4. Integrar en tu proyecto:
     ${colors.cyan}Ver GUIA_INTEGRACION_IA.md${colors.reset}
  `);
}

// Ejecutar pruebas
(async () => {
  try {
    const data = await testConnection();
    const modelName = await listModels(data);
    await testGeneration(modelName);
    await testBackend();
    await showSummary();
    
    console.log(`${colors.green}
╔═══════════════════════════════════════════════════════╗
║  ✓ Todas las pruebas completadas exitosamente       ║
╚═══════════════════════════════════════════════════════╝
${colors.reset}\n`);
    
  } catch (error) {
    console.error(`\n${colors.red}Error inesperado:${colors.reset}`, error.message);
    process.exit(1);
  }
})();
