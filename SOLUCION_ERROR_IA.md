# ERROR: Servidor IA no disponible

> **⚠️ Esta guía aplica solo si tenés "Ollama local" seleccionado como
> proveedor de IA.** Ollama es el **plan de respaldo offline**, no el backend
> principal de EducaApp — la mayoría de los usuarios usan el fallback
> compartido de demo (Groq/Gemini, sin configuración propia) o su propia API
> key (BYOK) en "Proveedor de IA", ninguno de los cuales depende de la VPN
> descrita acá. Si tu error NO menciona `192.168.12.236:11434`, esta guía no
> aplica: revisá el mensaje de error tal cual lo muestra el dashboard (suele
> indicar si es un problema de API key, cupo agotado, o del proveedor
> externo) o `/herramientas/groq-monitor/` para el estado del fallback
> compartido.

## 🔴 Problema
El error que estás viendo:
```
HTTPConnectionPool(host='192.168.12.236', port=11434): Read timed out. (read timeout=60)
```

Significa que **no puedes conectarte al servidor Ollama** en la intranet — esto solo
puede pasar si elegiste Ollama local como tu proveedor de IA (ver nota arriba).

## ✅ Solución

### 1. Conectar a VPN
**DEBES estar conectado a la VPN de la intranet** para acceder al servidor:
- Servidor: `192.168.12.236:11434`
- Puerto: `11434`
- Requiere: VPN activa

### 2. Verificar Conexión
Ejecuta este comando para verificar:
```bash
python test_connection_now.py
```

Deberías ver:
```
✓ Conectado: True
✓ URL: http://192.168.12.236:11434
✓ Modelos disponibles: 21
✓ Modelo seleccionado: llama3.1:8b
```

Si ves `✓ Conectado: False`, entonces:
1. ❌ VPN no está conectada
2. ❌ Servidor está apagado
3. ❌ Problemas de red

## 🛠️ Mejoras Implementadas

### 1. **Timeout Extendido**
- Antes: 60 segundos
- Ahora: **120 segundos** (2 minutos)
- Para generaciones complejas con múltiples capítulos

### 2. **Validación Previa**
- El sistema ahora verifica la conexión ANTES de intentar generar
- Si no hay conexión, muestra alerta inmediatamente (sin esperar 60s)

### 3. **Mensajes Mejorados**
- Errores más claros indicando la causa
- Muestra el servidor exacto (192.168.12.236:11434)
- Instrucciones de qué hacer

### 4. **Advertencias de Rendimiento**
- Si seleccionas >5 capítulos, te pregunta si quieres continuar
- Muestra tiempo estimado (30s-2min)
- Indicador de progreso durante la generación

### 5. **Límite de Texto**
- Reducido de 8000 a **5000 caracteres** por generación
- Evita sobrecarga del modelo
- Genera respuestas más rápidas y precisas

### 6. **Logs Mejorados**
- El sistema ahora registra:
  - Número de capítulos procesados
  - Longitud total del texto
  - Éxito/fallo de la generación

## 📋 Checklist para Generar Preguntas

Antes de hacer clic en "Generar Preguntas con IA":

- [ ] ✅ Conectado a VPN
- [ ] ✅ Servidor respondiendo (luz verde en dashboard)
- [ ] ✅ Modelo seleccionado (llama3.1:8b por defecto)
- [ ] ✅ Capítulos seleccionados (recomendado: 1-3 capítulos)
- [ ] ✅ Esperar pacientemente (30s-2min)

## 🔄 Próximos Pasos

1. **Conectar VPN**
2. **Verificar conexión** con `python test_connection_now.py`
3. **Recargar dashboard** en http://127.0.0.1:8000/doc-processor/
4. **Verificar luz verde** en "Estado IA Local"
5. **Intentar generar nuevamente**

## 💡 Tips

- **Selecciona pocos capítulos** la primera vez (1-2)
- **Espera pacientemente** - la IA necesita tiempo
- **Si falla**, revisa VPN primero
- **Guarda todas las preguntas** (aprobadas y rechazadas) para análisis

---

**Última actualización:** 2026-02-08
**Sistema:** EducaApp - Generación automática de preguntas con IA
**Alcance:** Solo para usuarios con "Ollama local" seleccionado en Proveedor de IA — el
backend por defecto (Groq/Gemini compartido) y BYOK no dependen de la VPN ni del servidor
descrito en esta guía.
