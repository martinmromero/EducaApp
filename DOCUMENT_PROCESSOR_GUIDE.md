# 📚 Document Processor - Guía de Uso

## ✅ Instalación Completada

Se ha instalado exitosamente el **Stack Completo** de procesamiento de documentos:

- ✅ **PyMuPDF** 1.26.5 (reemplaza a PyPDF2)
- ✅ **pdfplumber** 0.11.7
- ✅ **tiktoken** 0.12.0
- ✅ **markdownify** 1.2.0
- ✅ **python-docx** 0.8.11
- ✅ **python-pptx** 0.6.23

**PyPDF2** ha sido desinstalado y reemplazado por PyMuPDF (superior en todos los aspectos).

---

## 🎯 Archivos del Módulo

| Archivo | Descripción |
|---------|-------------|
| `document_processor.py` | Módulo principal con clase `DocumentProcessor` |
| `example_document_processor.py` | Ejemplos completos de uso |
| `requirements.txt` | Dependencias del proyecto (incluye stack completo) |

---

## 🚀 Inicio Rápido

### 1. Importar el módulo

```python
from document_processor import DocumentProcessor, process_document

# Crear procesador
processor = DocumentProcessor()
```

### 2. Procesar un PDF

```python
# Automático (detecta TOC, limpia headers/footers)
result = processor.process_pdf("mi_documento.pdf")

# Ver resumen
print(processor.get_stats_summary(result))

# Acceder a capítulos
for chapter in result['chapters']:
    print(f"{chapter['title']}: {chapter['tokens']} tokens")
```

### 3. Contar tokens (ESENCIAL para IA)

```python
# Contar tokens de un texto
tokens = processor.count_tokens("Tu texto aquí")
print(f"Tokens (GPT-4): {tokens}")

# Contar tokens de todo un documento
tokens_totales = quick_token_count("documento.pdf")
```

### 4. Dividir por límite de tokens

```python
# Dividir texto largo para enviar a IA
texto_largo = "..." # Tu texto
chunks = processor.split_by_token_limit(texto_largo, max_tokens=4000)

# Cada chunk tiene máximo 4000 tokens
for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}: {processor.count_tokens(chunk)} tokens")
```

---

## 📖 Funcionalidades Principales

### A) Procesamiento de PDFs

```python
result = processor.process_pdf(
    file_path="documento.pdf",
    remove_headers=True,      # Elimina headers repetitivos
    remove_footers=True,      # Elimina footers y números de página
    extract_toc=True          # Extrae tabla de contenidos si existe
)

# Estructura del resultado:
# {
#     'metadata': {'title': str, 'author': str, 'total_pages': int},
#     'toc': [{'level': int, 'title': str, 'page': int}],
#     'chapters': [{'title': str, 'content': str, 'tokens': int, 'pages': [int]}],
#     'stats': {'total_tokens': int, 'removed_headers': int, ...}
# }
```

**Ventajas de PyMuPDF:**
- ✅ Extrae TOC (tabla de contenidos) directamente
- ✅ Detecta estructura jerárquica automáticamente
- ✅ Mejor manejo de PDFs complejos (multi-columna, tablas)
- ✅ Más rápido que PyPDF2

### B) Procesamiento de DOCX

```python
result = processor.process_docx("documento.docx")

# Detecta automáticamente:
# - Headings (Título 1, 2, 3...)
# - Organiza por capítulos según estilos
# - Cuenta tokens por sección
```

### C) Procesamiento de PPTX

```python
result = processor.process_pptx("presentacion.pptx")

# Extrae:
# - Texto de cada slide
# - Títulos de slides
# - Tokens por slide
```

### D) Detección y Limpieza de Texto Repetitivo

```python
# Automático en PDFs:
# - Detecta headers que se repiten en >70% de páginas
# - Elimina footers repetitivos
# - Quita números de página solitarios

# Manual para cualquier texto:
texto_limpio = processor.optimize_for_ai(
    text=texto_sucio,
    remove_extra_whitespace=True,  # Elimina espacios/saltos extras
    remove_urls=True,              # Quita URLs
    remove_emails=True             # Quita emails
)
```

### E) Conteo de Tokens (CRÍTICO para IA)

```python
# Usa tiktoken para conteo exacto (GPT-4 encoding)
tokens = processor.count_tokens("Tu texto")

# División inteligente por límite
chunks = processor.split_by_token_limit(
    text=texto_largo,
    max_tokens=4000  # Límite de contexto de la IA
)
```

### F) Exportar Resultados

```python
# Guardar como JSON
processor.export_to_json(result, "documento_procesado.json")

# Ver resumen en consola
print(processor.get_stats_summary(result))
```

---

## 💡 Casos de Uso

### 1. Preparar documento para GPT-4

```python
# Flujo completo
processor = DocumentProcessor()

# 1. Procesar
result = processor.process_pdf("tesis.pdf")

# 2. Seleccionar capítulo relevante
capitulo = result['chapters'][0]

# 3. Verificar límite
LIMITE_GPT4 = 8000
if capitulo['tokens'] > LIMITE_GPT4:
    # Dividir en chunks
    chunks = processor.split_by_token_limit(capitulo['content'], LIMITE_GPT4)
else:
    chunks = [capitulo['content']]

# 4. Optimizar
for chunk in chunks:
    chunk_optimizado = processor.optimize_for_ai(chunk)
    # Enviar a API de OpenAI...
```

### 2. Analizar múltiples documentos

```python
import os

archivos = ["doc1.pdf", "doc2.docx", "doc3.pptx"]
total_tokens = 0

for archivo in archivos:
    result = process_document(archivo)  # Detecta formato automáticamente
    tokens = result['stats']['total_tokens']
    total_tokens += tokens
    print(f"{archivo}: {tokens} tokens")

print(f"Total: {total_tokens} tokens")
```

### 3. Extraer solo capítulos específicos

```python
result = processor.process_pdf("libro.pdf")

# Filtrar capítulos por palabra clave
capitulos_relevantes = [
    ch for ch in result['chapters']
    if 'metodología' in ch['title'].lower()
]

for ch in capitulos_relevantes:
    print(f"{ch['title']}: {ch['tokens']} tokens")
    print(ch['content'][:200])  # Preview
```

### 4. Calcular costo de procesamiento con IA

```python
# GPT-4: $0.03 por 1K tokens (input)
tokens = quick_token_count("documento_grande.pdf")
costo_usd = (tokens / 1000) * 0.03

print(f"Tokens: {tokens:,}")
print(f"Costo estimado (GPT-4): ${costo_usd:.2f}")
```

---

## 🧪 Probar el Módulo

Ejecutá el ejemplo completo:

```powershell
# Activar entorno
.\.venv\Scripts\Activate.ps1

# Ejecutar demostración
python example_document_processor.py
```

Esto:
1. ✅ Crea un PDF de prueba
2. ✅ Procesa con detección de TOC
3. ✅ Demuestra conteo de tokens
4. ✅ Muestra división por límite
5. ✅ Optimiza texto
6. ✅ Simula flujo para IA

Archivos generados:
- `ejemplo_documento.pdf`
- `ejemplo_resultado.json`

---

## 📊 Comparación: Antes vs Después

| Aspecto | PyPDF2 (Antes) | PyMuPDF (Ahora) |
|---------|---------------|-----------------|
| Extracción TOC | ❌ No | ✅ Sí, nativo |
| Detección de estructura | ❌ Manual | ✅ Automática |
| Headers/Footers | ❌ No detecta | ✅ Detecta con pdfplumber |
| PDFs complejos | ⚠️ Problemas | ✅ Excelente |
| Velocidad | ⚠️ Lento | ✅ Rápido |
| Conteo de tokens | ❌ No | ✅ tiktoken integrado |

---

## 🔧 Integración con Django (EducaApp)

El módulo está integrado en EducaApp mediante `material/ia_processor.py`, que importa `DocumentProcessor` desde el raíz del proyecto. Las vistas REST están en `material/views_document_processor.py`.

### Cómo está integrado en `material/ia_processor.py`

```python
# En material/ia_processor.py
from document_processor import DocumentProcessor

class IAProcessor:
    def __init__(self):
        self.doc_processor = DocumentProcessor()
    
    def procesar_contenido_documento(self, archivo_path):
        """Procesa documento subido por usuario."""
        result = self.doc_processor.process_pdf(archivo_path)
        
        # Guardar en BD o retornar para análisis
        return {
            'capitulos': result['chapters'],
            'tokens_totales': result['stats']['total_tokens']
        }
```

### Cómo está integrado en `material/views_document_processor.py`

```python
# En material/views.py
from document_processor import process_document
from django.http import JsonResponse

def procesar_documento_view(request):
    if request.method == 'POST' and request.FILES.get('documento'):
        archivo = request.FILES['documento']
        
        # Guardar temporalmente
        file_path = f'/tmp/{archivo.name}'
        with open(file_path, 'wb') as f:
            for chunk in archivo.chunks():
                f.write(chunk)
        
        # Procesar
        result = process_document(file_path)
        
        return JsonResponse({
            'success': True,
            'metadata': result['metadata'],
            'capitulos': len(result['chapters']),
            'tokens': result['stats']['total_tokens']
        })
```

---

## ⚙️ Configuración Avanzada

### Cambiar encoding de tokens

```python
# Por defecto: cl100k_base (GPT-4)
processor = DocumentProcessor(encoding_name="cl100k_base")

# Otros encodings:
# - "p50k_base" (GPT-3, Codex)
# - "r50k_base" (GPT-3 legacy)
```

### Ajustar detección de headers/footers

```python
# Umbral: % de páginas donde debe aparecer para ser "repetitivo"
# Por defecto: 0.7 (70%)

# Modificar en _detect_repetitive_text():
headers, footers = self._detect_repetitive_text(
    file_path,
    threshold=0.8  # Más estricto: solo si aparece en 80%+
)
```

---

## 📚 Recursos

- **PyMuPDF Docs**: https://pymupdf.readthedocs.io/
- **pdfplumber**: https://github.com/jsvine/pdfplumber
- **tiktoken**: https://github.com/openai/tiktoken
- **OpenAI Pricing**: https://openai.com/pricing

---

## 🆘 Troubleshooting

### Error: "No module named 'fitz'"
```powershell
pip uninstall PyMuPDF -y
pip install PyMuPDF
```

### Error: PDFs sin TOC
```python
# Si el PDF no tiene TOC, el procesador automáticamente:
# - Extrae todo el texto limpio
# - Lo devuelve como un solo "capítulo"
result = processor.process_pdf("sin_toc.pdf")
print(result['chapters'][0]['title'])  # "Documento completo"
```

### Optimizar velocidad
```python
# Para PDFs muy grandes, samplear menos páginas en detección:
# Modificar en _detect_repetitive_text():
for page in pdf.pages[:5]:  # Solo primeras 5 en vez de 10
    ...
```

---

## ✅ Checklist de Uso

- [x] Instalación completada (Stack Completo)
- [x] PyPDF2 desinstalado
- [x] `requirements.txt` actualizado
- [x] Módulo `document_processor.py` creado
- [x] Ejemplos ejecutados exitosamente
- [x] Integrado en EducaApp (`material/ia_processor.py` + vistas REST) ✅
- [ ] Probado con tus propios documentos

---

## 🎯 Próximos Pasos Sugeridos

1. **Probar con tus propios PDFs**
   ```python
   result = process_document("tu_documento.pdf")
   print(processor.get_stats_summary(result))
   ```

2. **Optimizar para la IA local (Ollama)**
   - Siempre contar tokens antes de enviar al modelo
   - Dividir documentos grandes en chunks por límite de contexto
   - Limpiar texto repetitivo para mejorar calidad de respuestas

3. **Ver también**
   - `EDUCAAPP_INTEGRATION.md` — Referencia de endpoints REST disponibles
   - `LOCAL_AI_SETUP_SUMMARY.md` — Configuración del servidor Ollama

---

**¿Dudas o necesitás ayuda?**
- Revisá `example_document_processor.py` para ver todos los casos de uso
- Ejecutá los ejemplos paso a paso

**Listo para usar** ✅
