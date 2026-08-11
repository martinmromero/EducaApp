# ✅ Integración Completa: Document Processor en EducaApp

## 📋 Resumen Ejecutivo

**Fecha original de esta integración:** 29 octubre 2025
**Estado:** ✅ **EN PRODUCCIÓN** (evolucionado bastante desde la integración original — ver notas más abajo)

> **Nota de vigencia:** este documento describe la integración inicial de
> `document_processor.py` en EducaApp. Desde entonces se agregaron citas de
> página real por pregunta (commit `ab3c916`), un router multi-proveedor de
> IA (`material/ai_router.py` — Groq/Gemini como fallback compartido de demo,
> BYOK, e **Ollama local solo como respaldo offline**, no como backend
> principal), extracción de imágenes para modelos con visión, streaming SSE
> de preguntas y varios endpoints nuevos. Las secciones de abajo fueron
> actualizadas para reflejar el estado actual del código; donde queda texto
> histórico sin verificar se indica explícitamente.

Se ha integrado exitosamente el módulo de **Document Processor** en EducaApp con las siguientes mejoras:

### ✅ Cambios Realizados

1. **Migración de PyPDF2 → PyMuPDF**
   - ✅ `material/ia_processor.py` actualizado
   - ✅ PyPDF2 desinstalado
   - ✅ Funciones existentes mantienen retrocompatibilidad
   - ✅ Nuevas funciones añadidas para capacidades avanzadas

2. **Nuevas Vistas y Endpoints**
   - ✅ `material/views_document_processor.py` creado
   - ✅ 14 endpoints REST bajo `/doc-processor/` (ver tabla completa más abajo)
   - ✅ Dashboard interactivo con interfaz web

3. **URLs Configuradas**
   - ✅ `material/urls.py` actualizado
   - ✅ Rutas bajo `/doc-processor/`

4. **Templates HTML**
   - ✅ Dashboard de un solo flujo guiado (Documento → selección de páginas/capítulos → generación IA),
     con una pestaña adicional "Modelos Locales" que solo aparece cuando el backend activo es Ollama
   - ✅ AJAX para procesamiento en tiempo real

5. **Servidor Django**
   - ✅ Sin errores
   - ✅ Corre en Render (producción) y localmente en http://127.0.0.1:8000/

---

## 🔗 URLs Disponibles

### Dashboard Principal
```
http://127.0.0.1:8000/doc-processor/
```
El dashboard es un flujo guiado de un solo paso a paso (no un set de tabs
independientes como en la integración original):
1. Subir o elegir un documento ya guardado (Mis Contenidos)
2. Elegir qué páginas/capítulos/slides procesar, con vista previa
3. Configurar tipos de pregunta y generar con IA (síncrono o streaming SSE)

Además, si el backend de IA activo del usuario es Ollama local, aparece una
pestaña extra "Modelos Locales" para elegir el modelo Ollama activo — no se
muestra con los demás backends (Groq/Gemini compartido, BYOK).

### API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/doc-processor/` | GET | Dashboard interactivo |
| `/doc-processor/upload/` | POST | Subir y procesar documento (guarda como `Contenido`, deduplica por hash) |
| `/doc-processor/split-chunks/` | POST | Dividir texto en chunks por límite de tokens |
| `/doc-processor/local-ai/status/` | GET | Estado del backend de IA configurado para el usuario (Ollama, fallback Groq/Gemini o BYOK) |
| `/doc-processor/local-ai/models/` | GET | Listar modelos disponibles en el servidor Ollama local |
| `/doc-processor/local-ai/set-model/` | POST | Cambiar el modelo Ollama activo |
| `/doc-processor/generate-questions/` | POST | Generar preguntas con IA desde capítulos (modo directo o `stream_mode` para SSE) |
| `/doc-processor/generate-questions/stream/<job_id>/` | GET | Stream SSE de preguntas a medida que se generan |
| `/doc-processor/save-questions/` | POST | Guardar preguntas aprobadas/rechazadas en la BD |
| `/doc-processor/topics-by-subject/<subject_id>/` | GET | Temas/subtemas de una materia (usado por el modal de guardado) |
| `/doc-processor/process-contenido/<contenido_id>/` | GET | Reprocesar un `Contenido` ya guardado y preseleccionarlo en el dashboard |
| `/doc-processor/page-preview/` | GET | Metadata del documento en sesión para el visor de páginas (PDF.js / DOCX / PPTX) |
| `/doc-processor/pages-text/` | POST | Extraer texto de páginas/slides/secciones puntuales elegidas por el usuario |
| `/doc-processor/serve-file/` | GET | Sirve el archivo original en sesión (necesario en Render, donde `/media/` no se sirve con `DEBUG=False`) |

No existe un endpoint `/doc-processor/count-tokens/` independiente en el código actual — el conteo de tokens
se muestra como parte de la respuesta de `/doc-processor/upload/` y `/doc-processor/process-contenido/<id>/`.

---

## 📖 Funciones Nuevas en `ia_processor.py`

### Funciones Originales (Actualizadas)
```python
# Mantienen compatibilidad, ahora usan PyMuPDF internamente
extract_text_from_file(file_path)
split_text_into_chapters(text)
generate_questions_from_text(text, num_questions)  # Requiere transformers
```

### Funciones Nuevas Avanzadas
```python
# Extracción con limpieza de headers/footers
extract_text_advanced(file_path, remove_headers=True, remove_footers=True)
# Retorna: {'metadata': {...}, 'chapters': [...], 'stats': {...}}

# Conteo de tokens
count_tokens(text)
count_tokens_file(file_path)

# División inteligente
split_text_by_tokens(text, max_tokens=4000)

# Optimización
optimize_text_for_ai(text, remove_extra_whitespace=True)
```

---

## 💻 Ejemplos de Uso

### 1. En Vistas Django (Backend)

```python
from material.ia_processor import extract_text_advanced, count_tokens

# En una vista
def mi_vista(request):
    if request.FILES.get('documento'):
        # Guardar archivo temporalmente
        archivo = request.FILES['documento']
        
        # Procesar con detección de estructura
        result = extract_text_advanced(archivo.temporary_file_path())
        
        # Acceder a capítulos
        for capitulo in result['chapters']:
            print(f"{capitulo['title']}: {capitulo['tokens']} tokens")
        
        # Contar tokens totales
        total = result['stats']['total_tokens']
```

### 2. Desde JavaScript (Frontend)

```javascript
// Procesar documento
const formData = new FormData();
formData.append('documento', fileInput.files[0]);

fetch('/doc-processor/upload/', {
    method: 'POST',
    body: formData,
    headers: {'X-CSRFToken': csrfToken}
})
.then(res => res.json())
.then(data => {
    console.log('Tokens totales:', data.stats.total_tokens);
    console.log('Capítulos:', data.chapters);
    console.log('Presupuesto de tokens:', data.token_budget);
});
```

> No existe un endpoint separado solo para contar tokens — el conteo (`stats.total_tokens`)
> y el presupuesto (`token_budget`) vienen incluidos en la respuesta de `/doc-processor/upload/`
> y de `/doc-processor/process-contenido/<id>/`.

### 3. Uso Directo del DocumentProcessor

```python
# Si necesitás funcionalidad más avanzada
from document_processor import DocumentProcessor

processor = DocumentProcessor()

# Procesar PDF con todas las opciones
result = processor.process_pdf(
    'documento.pdf',
    remove_headers=True,
    remove_footers=True,
    extract_toc=True
)

# Ver estadísticas
print(processor.get_stats_summary(result))

# Exportar a JSON
processor.export_to_json(result, 'resultado.json')

# Dividir por tokens
chunks = processor.split_by_token_limit(result['chapters'][0]['content'], max_tokens=2000)
```

---

## 🎨 Interfaz Web

### Dashboard Principal

El dashboard original de 3 tabs (Procesar / Tokens / Optimizador) fue
rediseñado a un **flujo guiado de un solo paso a paso** (`doc-flow` en el
template), porque el "Contador de tokens" y el "Optimizador" sueltos no
tenían suficiente uso propio fuera del flujo real de generación de preguntas
y terminaron fusionados dentro del paso "Documento":

1. **Documento**: subir un archivo nuevo (PDF/DOCX/PPTX/TXT) o elegir uno ya
   guardado en Mis Contenidos. Muestra metadata, total de tokens y presupuesto
   disponible. Cada paso ya resuelto se colapsa a un renglón con un check y
   botón "Cambiar" en vez de quedar como tabs numerados.
2. **Selección de contenido**: vista previa por página (PDF, vía PDF.js),
   por sección (DOCX) o por slide (PPTX), con checkboxes para elegir qué
   procesar — o los capítulos/bloques detectados automáticamente por TOC.
3. **Generación**: elegir tipos de pregunta, cantidad total deseada, si
   incluir imágenes (modelos con visión) y generar — en modo directo o con
   barra de progreso en tiempo real vía streaming SSE.

Además, **solo si el backend de IA activo del usuario es Ollama local**,
aparece una pestaña extra "Modelos Locales" para listar y cambiar el modelo
Ollama activo. Con cualquier otro backend (fallback compartido Groq/Gemini,
o BYOK) esa pestaña no se muestra — ver la nota sobre Ollama como respaldo,
no backend principal, más abajo y en `LOCAL_AI_SETUP_SUMMARY.md`.

---

## 🚀 Cómo Acceder

### Paso 1: Asegurate de que el servidor esté corriendo

```powershell
# Si no está corriendo:
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

### Paso 2: Acceder al Dashboard

Abrí tu navegador en:
```
http://127.0.0.1:8000/doc-processor/
```

### Paso 3: Probar

1. Subí un PDF/DOCX/PPTX
2. Activá las opciones de limpieza
3. Click en "Procesar Documento"
4. Revisá los resultados

---

## 📊 Mejoras vs Versión Anterior

| Aspecto | Antes (PyPDF2) | Ahora (PyMuPDF + Processor) |
|---------|----------------|----------------------------|
| **Extracción PDF** | Básica | Avanzada con TOC |
| **Headers/Footers** | ❌ No | ✅ Detección automática |
| **Conteo de Tokens** | ❌ No | ✅ tiktoken integrado |
| **Estructura** | ❌ Manual | ✅ Automática (capítulos) |
| **Optimización** | ❌ No | ✅ Ahorro 30-40% tokens |
| **Dashboard Web** | ❌ No | ✅ Interface completa |
| **API REST** | ❌ No | ✅ 14 endpoints (ver tabla arriba) |
| **Costo Estimado** | ❌ No | ✅ Presupuesto de tokens por tanda/documento |

---

## 🔧 Archivos Modificados/Creados

### Archivos del Core
- ✅ `document_processor.py` (nuevo, 600+ líneas)
- ✅ `example_document_processor.py` (nuevo, ejemplos)
- ✅ `requirements.txt` (actualizado)

### Integración Django
- ✅ `material/ia_processor.py` (migrado a PyMuPDF)
- ✅ `material/views_document_processor.py` (14 vistas a la fecha; ver tabla de endpoints arriba)
- ✅ `material/ai_router.py` (router de backends de IA: fallback Groq/Gemini, BYOK, Ollama local)
- ✅ `material/urls.py` (añadidas rutas)
- ✅ `material/templates/material/document_processor_dashboard.html` (nuevo)

### Documentación
- ✅ `DOCUMENT_PROCESSING_ANALYSIS.md`
- ✅ `DOCUMENT_PROCESSOR_GUIDE.md`
- ✅ `EDUCAAPP_INTEGRATION.md` (este archivo)

---

## 📝 Notas para Desarrollo Futuro

### Posibles Extensiones

1. **Guardar Resultados en Base de Datos**
   ```python
   # Crear modelo para almacenar procesamiento
   class DocumentProcessResult(models.Model):
       user = models.ForeignKey(User, on_delete=models.CASCADE)
       filename = models.CharField(max_length=255)
       total_tokens = models.IntegerField()
       chapters_json = models.JSONField()
       processed_at = models.DateTimeField(auto_now_add=True)
   ```

2. **Integración con Generación de Preguntas**
   ```python
   # En una vista
   result = extract_text_advanced('documento.pdf')
   
   # Por cada capítulo, generar preguntas
   for capitulo in result['chapters']:
       if capitulo['tokens'] < 4000:  # Límite GPT-4
           preguntas = generar_preguntas_ia(capitulo['content'])
           # Guardar en BD...
   ```

3. **Procesamiento Asíncrono**
   ```python
   # Para documentos grandes, usar Celery
   @shared_task
   def process_document_async(file_path):
       result = extract_text_advanced(file_path)
       # Notificar usuario cuando termine
   ```

4. **Historial de Procesamiento**
   - Ver documentos procesados anteriormente
   - Reutilizar resultados sin reprocesar
   - Estadísticas de uso de tokens

---

## ⚡ Performance

### Benchmarks Aproximados

| Tipo Documento | Tamaño | Tiempo Procesamiento |
|----------------|--------|---------------------|
| PDF simple (10 pág) | 500KB | ~2 segundos |
| PDF con TOC (50 pág) | 2MB | ~5 segundos |
| DOCX (20 pág) | 1MB | ~1 segundo |
| PPTX (30 slides) | 3MB | ~3 segundos |

### Optimizaciones Aplicadas

✅ Instancia única de `DocumentProcessor` (no recrear por request)  
✅ Archivos temporales eliminados automáticamente  
✅ Procesamiento en memoria (no disco)  
✅ Detección de headers/footers samplea primeras 10 páginas (no todas)

---

## 🆘 Troubleshooting

### Error: "No module named 'fitz'"
```powershell
pip uninstall PyMuPDF -y
pip install PyMuPDF
```

### Error: Template no encontrado
Verificar que exista:
```
material/templates/material/document_processor_dashboard.html
```

### Error: CSRF token missing
Asegurate de que el template incluya:
```html
{% csrf_token %}
```

### Dashboard no carga resultados
Verificar en consola del navegador (F12) si hay errores de JavaScript.
Revisar que las URLs en el fetch coincidan con las configuradas.

---

## ✅ Checklist de Validación

- [x] Servidor Django arranca sin errores
- [x] Dashboard accesible en `/doc-processor/`
- [x] Puede subir y procesar PDFs
- [x] Puede subir y procesar DOCX
- [x] Puede subir y procesar PPTX
- [x] Conteo de tokens funciona (integrado en la respuesta de `/upload/`, ya no como pantalla propia)
- [x] Limpieza/optimización de texto funciona (automática dentro del flujo, ya no como pantalla propia)
- [x] Resultados se muestran correctamente
- [x] `ia_processor.py` no da errores de import
- [x] Funciones originales mantienen compatibilidad

---

## 🎯 Próximos Pasos Sugeridos

1. **Probar con tus documentos reales**
   - Subir PDFs de tus materias
   - Verificar que detecta capítulos correctamente
   - Validar conteo de tokens

2. **Generación de preguntas con IA** — ✅ IMPLEMENTADO
   - Endpoint activo: `POST /doc-processor/generate-questions/`
   - Stream en tiempo real: `GET /doc-processor/generate-questions/stream/<job_id>/`
   - Guardado en BD: `POST /doc-processor/save-questions/`
   - El backend real lo resuelve `material/ai_router.py` por usuario: el default
     es el fallback compartido de demo (Groq para texto, Gemini para
     imágenes/respaldo de cupo), con BYOK como alternativa configurable en
     "Proveedor de IA". **Ollama local es un plan de respaldo para escenarios
     sin internet, no el backend principal** — ver `LOCAL_AI_SETUP_SUMMARY.md`
     y `SOLUCION_ERROR_IA.md` para su configuración específica.

3. **Agregar almacenamiento**
   - Guardar resultados en BD
   - Crear historial de procesamiento

4. **Extender funcionalidad**
   - Exportar capítulos individuales
   - Comparar versiones de documentos
   - Estadísticas de uso

---

## 📚 Recursos de Referencia

- **DocumentProcessor API**: Ver `document_processor.py`
- **Ejemplos Completos**: Ver `example_document_processor.py`
- **Guía de Usuario**: Ver `DOCUMENT_PROCESSOR_GUIDE.md`
- **Análisis Técnico**: Ver `DOCUMENT_PROCESSING_ANALYSIS.md`

---

**Estado Final:** ✅ **LISTO PARA USAR**

El módulo está completamente integrado en EducaApp y funcionando. El servidor está corriendo sin errores y todas las funcionalidades están disponibles.
