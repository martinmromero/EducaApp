# 📄 Document Processing Module - Análisis de Entorno

**Fecha:** 29 octubre 2025  
**Python:** 3.12.10 (venv: `.venv`)

---

## ✅ Estado Actual del Entorno

### Librerías YA instaladas (relevantes para document processing):

| Librería | Versión | Propósito Actual | Estado |
|----------|---------|------------------|--------|
| **PyPDF2** | 3.0.0 | Extracción básica de texto de PDFs | ✅ Instalada |
| **python-docx** | 0.8.11 | Lectura de archivos DOCX | ✅ Instalada |
| **python-pptx** | 0.6.23 | Lectura de archivos PPTX | ✅ Instalada |
| **lxml** | 6.0.2 | Parser XML (usado por python-docx) | ✅ Instalada |
| **nltk** | 3.9.2 | NLP - tokenización, detección de oraciones | ✅ Instalada |
| **spacy** | 3.8.7 | NLP avanzado - detección de estructura | ✅ Instalada |
| **regex** | 2025.10.22 | Expresiones regulares avanzadas | ✅ Instalada |

### Librerías adicionales detectadas (útiles):
- **numpy** 2.3.4 → manipulación de datos numéricos
- **requests** 2.32.5 → descarga de documentos remotos
- **Pillow** 12.0.0 → procesamiento de imágenes embebidas
- **rich** 14.2.0 → output de consola con formato (útil para debug)

---

## 🎯 Recomendaciones para el Módulo de Document Interpreter

### 🔴 Problemas identificados con el stack actual:

1. **PyPDF2 3.0.0** es limitado:
   - ❌ No detecta bien estructura jerárquica (capítulos, secciones)
   - ❌ Problemas con PDFs complejos (tablas, multi-columna)
   - ❌ No extrae metadatos avanzados de páginas
   - ❌ Dificultad con PDFs escaneados (no tiene OCR)

2. **python-docx** y **python-pptx** son buenas pero:
   - ✅ Funcionan bien para estructura básica
   - ⚠️ Requieren post-procesamiento para limpiar headers/footers repetitivos

3. **nltk** y **spacy** ya instaladas:
   - ✅ spacy es más moderna y rápida
   - ⚠️ Ocupan espacio pero pueden ayudar con detección de estructura semántica

---

## 💡 Stack Recomendado (Optimizado para IA + Tokens)

### Opción A: **Stack Completo** (máxima precisión)

| Librería | Versión | Propósito | Justificación |
|----------|---------|-----------|---------------|
| **PyMuPDF (fitz)** | 1.25.1+ | PDF avanzado | ⭐ **MEJOR que PyPDF2**: extrae TOC, metadatos, detección de headers/footers, mejor con layouts complejos |
| **python-docx** | 0.8.11 | DOCX | ✅ **Mantener**: ya instalada y funcional |
| **python-pptx** | 0.6.23 | PPTX | ✅ **Mantener**: ya instalada y funcional |
| **pdfplumber** | 0.11.0+ | Análisis estructural de PDFs | ⭐ Complementa PyMuPDF para tablas y layouts complejos |
| **markdownify** | 0.13.1 | Conversión HTML→Markdown | 🆕 Útil para limpiar formato y reducir tokens |
| **tiktoken** | 0.9.0+ | Conteo exacto de tokens OpenAI | 🆕 **CRÍTICO**: mide tokens antes de enviar a IA |
| **regex** | (instalada) | Detección de patrones | ✅ Ya está |

**Ventajas:**
- PyMuPDF extrae TOC (tabla de contenidos) directamente de PDFs
- pdfplumber detecta headers/footers repetitivos para eliminarlos
- tiktoken te dice EXACTAMENTE cuántos tokens consume cada sección
- markdownify limpia HTML si extraés de fuentes web

**Desventajas:**
- PyMuPDF tiene dependencias binarias (puede ser grande: ~30MB)
- Más complejidad de código

---

### Opción B: **Stack Minimalista** (lo que ya tenés + 2 mejoras clave)

| Librería | Versión | Propósito | Justificación |
|----------|---------|-----------|---------------|
| **PyPDF2** | 3.0.0 | PDF básico | ⚠️ Mantener solo si PyMuPDF da problemas |
| **PyMuPDF (fitz)** | 1.25.1+ | PDF avanzado | ⭐ Reemplaza a PyPDF2 |
| **python-docx** | 0.8.11 | DOCX | ✅ Mantener |
| **python-pptx** | 0.6.23 | PPTX | ✅ Mantener |
| **tiktoken** | 0.9.0+ | Conteo de tokens | 🆕 **ESENCIAL** para optimización |
| **regex** | (instalada) | Patrones | ✅ Ya está |

**Ventajas:**
- Cambio mínimo
- tiktoken te da control sobre tokens
- PyMuPDF resuelve las limitaciones de PyPDF2

**Desventajas:**
- Seguís necesitando lógica manual para detectar headers/footers repetitivos

---

## 🚀 Mi Recomendación FINAL: **Opción A (Stack Completo)**

### ¿Por qué?
1. **PyMuPDF** es MUCHO mejor que PyPDF2 para:
   - Extraer tabla de contenidos (TOC) → identificás capítulos automáticamente
   - Detectar headers/footers por posición en página
   - Mejor rendimiento con PDFs complejos

2. **tiktoken** es OBLIGATORIO si vas a mandar texto a OpenAI/Claude/etc:
   - Te dice exactamente cuántos tokens tiene cada sección
   - Evitás sorpresas de costos
   - Podés fragmentar inteligentemente antes de enviar

3. **pdfplumber** como complemento:
   - Si PyMuPDF no detecta bien tablas, pdfplumber las extrae limpias
   - Útil para documentos académicos/técnicos

4. **markdownify** (opcional pero útil):
   - Si extraés HTML (ej: de PDFs con formato rico), lo convertís a Markdown limpio
   - Markdown consume menos tokens que HTML

---

## 📦 Librerías a EVITAR (y por qué)

| Librería | Razón para NO usarla |
|----------|---------------------|
| **textract** | Obsoleta, muchas dependencias binarias, no mantenida |
| **pdfminer.six** | Más lento que PyMuPDF, API compleja |
| **Apache Tika** | Requiere Java, overhead innecesario |
| **transformers (Hugging Face)** | Demasiado pesado si solo querés limpiar texto (>500MB) |
| **langchain** | Abstracción útil pero añade complejidad si solo querés parsear |

---

## 🛠️ Comandos de Instalación Recomendados

### Stack Completo (Opción A):
```powershell
# Activar entorno
.\.venv\Scripts\Activate.ps1

# Instalar nuevas librerías
pip install PyMuPDF==1.25.1 pdfplumber==0.11.0 tiktoken==0.9.0 markdownify==0.13.1

# Verificar instalación
python -c "import fitz; import pdfplumber; import tiktoken; print('✅ Todo instalado')"
```

### Stack Minimalista (Opción B):
```powershell
# Activar entorno
.\.venv\Scripts\Activate.ps1

# Solo lo esencial
pip install PyMuPDF==1.25.1 tiktoken==0.9.0

# Verificar
python -c "import fitz; import tiktoken; print('✅ Instalado')"
```

---

## 📋 Siguiente Paso: Actualizar requirements.txt

Elegí una opción y actualizamos `requirements.txt` con las versiones exactas.

**¿Tu elección?**
- Opción A (completo, recomendado) → `requirements_document_processing.txt`
- Opción B (minimalista) → actualización directa de `requirements.txt`

---

## 🧪 Ejemplo de Uso (con PyMuPDF + tiktoken)

```python
import fitz  # PyMuPDF
import tiktoken

# Leer PDF y extraer TOC
doc = fitz.open("documento.pdf")
toc = doc.get_toc()  # [(nivel, titulo, pagina), ...]

# Extraer texto por capítulo
capitulos = {}
for nivel, titulo, pagina in toc:
    if nivel == 1:  # Solo capítulos principales
        # Extraer texto de páginas del capítulo
        texto = ""
        for p in range(pagina - 1, doc.page_count):
            texto += doc[p].get_text()
            # Detectar fin de capítulo (siguiente TOC entry)
            # ...
        capitulos[titulo] = texto

# Contar tokens
encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4
for titulo, texto in capitulos.items():
    tokens = len(encoding.encode(texto))
    print(f"{titulo}: {tokens} tokens")

doc.close()
```

---

## 🎯 Resumen Ejecutivo

| Aspecto | Estado |
|---------|--------|
| **Librerías base (DOCX/PPTX)** | ✅ Ya tenés todo |
| **PDF (PyPDF2)** | ⚠️ Reemplazar por PyMuPDF |
| **Conteo de tokens** | ❌ Falta tiktoken (CRÍTICO) |
| **Limpieza avanzada** | ⚠️ pdfplumber opcional pero útil |
| **NLP (spacy/nltk)** | ✅ Ya tenés (usar con cuidado, pesadas) |

**Acción inmediata:** Instalar PyMuPDF + tiktoken (mínimo) o stack completo (recomendado).
