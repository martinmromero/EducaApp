# 🎓 EducaApp - Sistema de Gestión Educativa

[![Django](https://img.shields.io/badge/Django-4.2.20-092E20?style=flat&logo=django&logoColor=white)](https://djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.0-7952B3?style=flat&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)](https://sqlite.org/)

## 📖 Descripción

EducaApp es un sistema integral de gestión educativa desarrollado en Django que permite a instituciones educativas administrar materias, resultados de aprendizaje, preguntas de examen, y generar cuestionarios tanto escritos como orales de manera eficiente.

## ✨ Características Principales

### 🏫 Gestión Institucional
- **Instituciones V2**: Sistema completo de gestión de instituciones educativas con logos
- **Campus y Facultades**: Organización jerárquica de la estructura institucional
- **Carreras**: Gestión de carreras académicas con asociaciones multi-nivel
- **Sistema de Favoritos**: Marcado de instituciones frecuentes por usuario
- **Auditoría**: Logs completos de cambios en instituciones
- **Relaciones Avanzadas**: Asociación Institución-Carrera-Materia con metadatos (semestre, carga horaria, optatividad)

### 📚 Gestión Académica
- **Materias**: CRUD completo de materias/asignaturas con asociaciones institucionales
- **Resultados de Aprendizaje**: Sistema integrado por materia con funcionalidades completas de edición
- **Temas y Subtemas**: Organización temática jerárquica del contenido educativo
- **Preguntas**: Banco de preguntas con filtros cascada (materia → tema → subtema)
- **Contenidos Educativos**: Gestión de materiales con metadata automática (libros, PDFs, documentos)
- **Trazabilidad de Preguntas**: Cada pregunta guarda el documento de origen (Contenido), sea cargada manualmente o generada por IA
- **Deduplicación de Archivos**: Hash SHA-256 por usuario; rechaza duplicados activos y restaura archivos expirados automáticamente
- **Expiración por Sesión**: Los archivos físicos se eliminan al cerrar sesión (logout o restart de la app); metadatos y preguntas se conservan siempre

### � Sistema de Rúbricas
- **Biblioteca personal de rúbricas**: Creación, edición y eliminación de rúbricas propias
- **Editor de grilla estructurada**: Diseño matricial de criterios (filas) × niveles de desempeño (columnas), similar a RubiStar
- **Asociación a exámenes**: Cada rúbrica puede asociarse a uno o más exámenes de forma independiente
- **Visibilidad configurable**: Toggle para mostrar u ocultar cada rúbrica en la vista del examen (ojo/ojo-tachado)
- **Vista previa integrada**: Las rúbricas se muestran como tabla dentro de la vista de examen y al imprimir
- **Menú dedicado**: Acceso desde el sidebar → Rúbricas (Nueva Rúbrica / Mis Rúbricas)

### �📝 Sistema de Exámenes
- **Plantillas de Examen**: Creación y reutilización de plantillas personalizables con configuración completa
- **Exámenes Escritos**: Generación automática con selección de preguntas por temas
- **Cuestionarios Orales**: Sistema avanzado de evaluación oral con algoritmos inteligentes
- **Evaluación en Tiempo Real**: Sistema de calificación para exámenes orales (Bien/Regular/Mal)
- **Gestión de Estudiantes**: Asignación de nombres, intercambio de preguntas y seguimiento de progreso
- **Cálculo Automático**: Porcentajes de progreso y puntuación por estudiante
- **Vista Previa e Impresión**: Formatos optimizados para diferentes tipos de evaluación

### 🔧 Funcionalidades Técnicas
- **Carga Masiva**: Importación de preguntas via CSV/TXT
- **Procesamiento Avanzado de Documentos**: Dashboard completo con soporte para PDF, DOCX, PPTX
- **Extracción Automática de Metadata**: Pre-llenado de formularios desde PDFs (ISBN, edición, páginas, editorial, año)
- **Análisis de Tokens**: Contador de tokens y división inteligente en chunks
- **IA Local con Ollama**: Generación automática de preguntas via servidor Ollama (`llama3.1:8b`) en intranet
- **Curación de Preguntas IA**: Flujo de revisión, aprobación y clasificación de preguntas generadas
- **Interfaz Responsiva**: Design moderno con Bootstrap 5
- **Sidebar Colapsable**: Navegación optimizada
- **Filtros Dinámicos**: Sistema de filtros cascada con AJAX
- **Sistema de Mensajes**: Notificaciones contextuales por módulo
- **Gestión de Usuarios**: CRUD completo con sistema de roles (Admin/Usuario)
- **Sistema de Favoritos**: Marcado de instituciones favoritas por usuario

## 🚀 Instalación

### Prerrequisitos
- Python 3.13+
- pip (gestor de paquetes de Python)
- Git

### Clonar el Repositorio
```bash
git clone https://github.com/martinmromero/EducaApp.git
cd EducaApp
```

### Configurar Entorno Virtual

> **Importante — proyecto en OneDrive con múltiples equipos:**
> El entorno virtual **no es portable** entre máquinas (contiene rutas absolutas al Python local).
> Debe crearse una vez en cada equipo y **no sincronizarse via OneDrive**.
> En OneDrive → click derecho sobre la carpeta `venv_local` → "No sincronizar este elemento".
> El código, `requirements.txt` y `db.sqlite3` sí se sincronizan normalmente.

```bash
# Crear entorno virtual (solo la primera vez en cada equipo)
python -m venv venv_local

# Activar entorno virtual — Windows:
venv_local\Scripts\activate
```

### Instalar Dependencias
```bash
# Primera vez en cada equipo, o cuando requirements.txt cambie:
pip install -r requirements.txt
```

### Configurar Base de Datos
```bash
# Aplicar migraciones (necesario cuando llegan migraciones nuevas desde git/OneDrive)
python manage.py migrate
```

### Ejecutar el Servidor
```bash
python manage.py runserver
```

La aplicación estará disponible en `http://127.0.0.1:8000/`

### Resumen del workflow multi-equipo

| Acción | Frecuencia |
|---|---|
| `python -m venv venv_local` + `pip install -r requirements.txt` | **Una sola vez** por equipo nuevo |
| `pip install -r requirements.txt` | Solo si alguien agregó una dependencia a `requirements.txt` |
| `python manage.py migrate` | Cada vez que llegan migraciones nuevas vía git/OneDrive |
| `python manage.py runserver` | Cada vez que querés levantar el servidor |

## 📦 Dependencias Principales

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| Django | 4.2.20 | Framework web principal |
| PyMuPDF | 1.26.5 | Procesamiento avanzado de archivos PDF |
| pdfplumber | 0.11.7 | Extracción de datos de PDFs |
| tiktoken | 0.12.0 | Contador de tokens para IA |
| markdownify | 1.2.0 | Conversión de HTML a Markdown |
| python-docx | 0.8.11 | Procesamiento de archivos Word |
| python-pptx | 0.6.23 | Procesamiento de archivos PowerPoint |
| django-crispy-forms | 2.4 | Formularios mejorados |
| crispy-bootstrap5 | - | Integración Bootstrap 5 |
| djangorestframework | 3.16.0 | APIs REST |
| django-debug-toolbar | 4.2.0 | Herramientas de desarrollo |
| django-extensions | 3.2.3 | Utilidades adicionales para Django |

## 🏗️ Estructura del Proyecto

```
educaapp/
├── educaapp/                   # Configuración principal del proyecto
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── material/                   # Aplicación principal
│   ├── models.py              # Modelos de datos
│   ├── views.py               # Vistas y lógica de negocio
│   ├── views_document_processor.py  # Vistas de procesamiento de documentos
│   ├── forms.py               # Formularios
│   ├── urls.py                # URLs de la aplicación
│   ├── admin.py               # Configuración del admin
│   ├── templates/             # Plantillas HTML
│   │   └── material/
│   │       ├── subjects/      # Templates de materias
│   │       ├── questions/     # Templates de preguntas
│   │       ├── exams/         # Templates de exámenes
│   │       ├── oral_exams/    # Templates de exámenes orales
│   │       ├── careers/       # Templates de carreras
│   │       ├── institutions_v2/ # Templates de instituciones
│   │       └── learningoutcomes/ # Templates de resultados
│   ├── static/                # Archivos estáticos
│   └── migrations/            # Migraciones de BD
├── exams/                     # Aplicación de exámenes
├── static/                    # Archivos estáticos globales
├── media/                     # Archivos subidos por usuarios
├── requirements.txt           # Dependencias del proyecto
└── manage.py                  # Script de gestión de Django
```

## 🎯 Casos de Uso Principales

### Para Docentes
1. **Gestión de Contenido**: Crear y organizar materias con sus resultados de aprendizaje
2. **Banco de Preguntas**: Cargar y categorizar preguntas por temas con dificultad y metadata
3. **Creación de Exámenes**: Generar exámenes personalizados usando plantillas reutilizables
4. **Evaluaciones Orales**: Crear cuestionarios orales con distribución automática y evaluación en tiempo real
5. **Procesamiento de Documentos**: Subir PDFs y extraer automáticamente metadata e información
6. **Análisis de Contenido**: Analizar tokens y dividir documentos en chunks para procesamiento con IA
7. **Seguimiento de Estudiantes**: Evaluar, asignar nombres y calcular puntuaciones automáticamente

### Para Instituciones
1. **Gestión Organizacional**: Administrar campus, facultades y carreras con estructura jerárquica
2. **Estandarización**: Usar plantillas para mantener consistencia en evaluaciones
3. **Reportes**: Generar vistas previas e imprimir exámenes en formatos estándar
4. **Auditoría**: Rastrear todos los cambios realizados en instituciones mediante logs
5. **Gestión de Usuarios**: Administrar roles y permisos de usuarios del sistema
6. **Asociaciones Flexibles**: Configurar relaciones entre instituciones, carreras y materias
7. **Favoritos**: Marcar y acceder rápidamente a instituciones frecuentes

## 🔧 Configuración Avanzada

### Variables de Entorno
El proyecto usa configuración directa en `settings.py`. Para producción, considere usar django-environ para variables de entorno.

### Base de Datos
Por defecto usa SQLite. Para producción, configure PostgreSQL o MySQL en `settings.py`.

### Archivos Estáticos
```bash
# Recolectar archivos estáticos para producción
python manage.py collectstatic
```

## 🧪 Testing

```bash
# Ejecutar tests
python manage.py test

# Ejecutar tests específicos
python manage.py test material.tests
```

## 📈 Funcionalidades Destacadas

### Sistema de Filtros Cascada
- Filtrado dinámico: Materia → Tema → Subtema
- Implementación con AJAX para mejor UX
- Actualización en tiempo real sin recargar página

### Cuestionarios Orales Inteligentes
- Algoritmo de distribución equitativa de preguntas
- Gestión de grupos y estudiantes
- Sistema de intercambio de preguntas entre estudiantes
- Evaluación y seguimiento en tiempo real
- Sistema de calificación: Bien (100%), Regular (50%), Mal (0%)
- Cálculo automático de progreso y puntuación

### Carga Masiva de Contenido
- Importación CSV/TXT con validaciones robustas
- Procesamiento de documentos (PDF, DOCX, PPTX)
- Sistema de preview antes de confirmar importación

### Imágenes en Preguntas — Almacenamiento Base64 Persistente
- **Sin dependencia del filesystem**: Las imágenes se codifican en Base64 y se guardan directamente en la BD como `TextField`
- **Compatible con Render + Neon**: No se pierden al reiniciar dynos ni al rotar workers; funciona idéntico en SQLite local y PostgreSQL en producción
- **Campos dedicados**: `question_image_b64` y `answer_image_b64` en el modelo `Question`
- **Editor visual**: Preview inline de la imagen existente, botón "Eliminar imagen", botón "Cambiar imagen" y preview live al seleccionar un archivo nuevo
- **Vista de examen**: Las imágenes de preguntas se muestran automáticamente en la vista previa e impresión
- **Migration 0026**: `AddField question_image_b64` y `answer_image_b64` — depende de ambas hojas del árbol de migraciones

### Procesamiento Avanzado de Documentos
- **Dashboard de Procesamiento**: Interface completa para análisis de documentos
- **Extracción de Metadata**: Obtención automática de ISBN, edición, páginas, editorial y año
- **Análisis de Tokens**: Contador de tokens compatible con modelos de IA
- **División Inteligente**: Segmentación de texto en chunks optimizados
- **Optimización de Texto**: Conversión y limpieza de contenido para procesamiento

### Gestión del Ciclo de Vida de Archivos
- **Trazabilidad**: `Question.contenido` FK opcional — guarda el documento de origen en preguntas manuales y generadas por IA
- **Deduplicación SHA-256**: `Contenido.file_hash` previene subidas duplicadas por usuario; restaura archivos expirados si se re-sube el mismo documento
- **Expiración por Sesión**: Archivos eliminados en logout (`user_logged_out` signal) y al reiniciar si no hay sesión activa (`cleanup_files_for_inactive_sessions()` en `AppConfig.ready()`)
- **Cloud-compatible**: Toda eliminación usa `default_storage.delete()` con fallback a `os.remove()` para almacenamiento local
- **Metadatos preservados**: `file_deleted_at`, `file_hash`, título, ISBN, etc. se conservan aunque el archivo físico sea eliminado

### Gestión Institucional Avanzada
- **Relaciones Multi-nivel**: Instituciones, Facultades, Campus, Carreras y Materias
- **Sistema de Logs**: Auditoría completa de cambios en instituciones
- **Favoritos**: Marcado rápido de instituciones frecuentes
- **Asociaciones Flexibles**: Materias por carrera con semestre, carga horaria y optatividad

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Changelog

### [2026-05-24]
- ✅ **Feature**: Almacenamiento de imágenes de preguntas/respuestas como Base64 en `TextField` — sin filesystem, compatible con Render + Neon PostgreSQL
- ✅ **Model**: Nuevos campos `Question.question_image_b64` y `Question.answer_image_b64` (TextField nullable)
- ✅ **Migration**: `0026_question_image_b64` con dependencias duales (0025_useraiconfig_ollama_url + 0024_contenido_file_hash)
- ✅ **Form**: `QuestionForm.save()` convierte uploads a data-URI y nunca escribe al disco; nuevos campos `clear_question_image` / `clear_answer_image`
- ✅ **UI**: Editor de preguntas rediseñado (dos columnas) — preview Base64 inline, botones "Eliminar" / "Cambiar", preview live al seleccionar archivo
- ✅ **Feature**: Imágenes de preguntas visibles en vista previa del examen (`base_exam_preview.html`)
- ✅ **Fix**: Race condition "No hay documento en sesión" resuelto — fallback a `contenido_id` como query param cuando `SESSION_SAVE_EVERY_REQUEST` sobreescribe la sesión
- ✅ **Fix**: "Error cargando temas" en selector de materia — URL hardcodeada reemplazada con etiqueta `{% url %}` de Django
- ✅ **Improvement**: `QuestionForm` incluye `question_type`, `difficulty` y `options_json` en `Meta.fields`; queryset de `contenido` usa `Q` para mostrar siempre el contenido asignado

### [2026-05-23]
- ✅ **Feature**: Trazabilidad de documentos — cada pregunta almacena el `Contenido` de origen, tanto en carga manual como en generación por IA
- ✅ **Feature**: Deduplicación de archivos con SHA-256 (`Contenido.file_hash`); bloquea re-subidas activas y restaura archivos expirados
- ✅ **Feature**: Expiración de archivos por sesión — eliminación inmediata al logout via señal `user_logged_out` y al arranque via `cleanup_files_for_inactive_sessions()`
- ✅ **Feature**: `material/cleanup.py` — módulo centralizado con `compute_file_hash()`, `cleanup_files_for_user()` y `cleanup_files_for_inactive_sessions()`
- ✅ **Migration**: `0023_contenido_file_expiry` — campo `file` nullable + `file_deleted_at`
- ✅ **Migration**: `0024_contenido_file_hash` — campo `file_hash` indexado
- ✅ **Improvement**: `Mis Contenidos` muestra estado de archivo ("Se elimina al cerrar sesión" / "Eliminado el dd/mm/aaaa")
- ✅ **Improvement**: Mensajes de alerta actualizados en templates de subida de contenido

### [2026-03-24]
- ✅ **Cleanup**: Limpieza de archivos obsoletos, backups y documentos de instalación históricos
- ✅ **Backup**: Nuevo backup de base de datos `db_backup_20260324.sqlite3`

### [2026-02-08]
- ✅ **Feature**: Integración completa con servidor IA local Ollama (`192.168.12.236:11434`)
- ✅ **Feature**: Generación de preguntas desde capítulos via `llama3.1:8b`
- ✅ **Feature**: Dashboard de modelos con selector y estado de conexión en tiempo real
- ✅ **Feature**: Endpoints REST para gestión de IA local (`/doc-processor/local-ai/*`)
- ✅ **Feature**: Stream de generación de preguntas por capítulos
- ✅ **Improvement**: Timeout extendido a 120s, validación previa de conexión
- ✅ **Improvement**: Round Robin como modo por defecto en exámenes orales + persistencia en localStorage

### [2026-01-24]
- ✅ **Feature**: Sistema completo de procesamiento avanzado de documentos
- ✅ **Feature**: Extracción automática de metadata de PDFs
- ✅ **Feature**: Análisis de tokens y división en chunks para IA
- ✅ **Feature**: Sistema de evaluación en tiempo real para exámenes orales
- ✅ **Feature**: Gestión completa de usuarios con roles
- ✅ **Feature**: Sistema de favoritos para instituciones
- ✅ **Feature**: Relaciones avanzadas Institución-Carrera-Materia
- ✅ **Feature**: Sistema de logs para auditoría institucional
- ✅ **Improvement**: Cálculo automático de progreso y puntuación en exámenes orales
- ✅ **Improvement**: Intercambio de preguntas entre estudiantes

### [2025-09-27]
- ✅ **Fix**: Corregidos botones de editar/eliminar Learning Outcomes
- ✅ **Feature**: Sistema de filtros cascada en lista de preguntas
- ✅ **Improvement**: Sidebar colapsable para mejor UX
- ✅ **Cleanup**: Eliminación de sistema de instituciones obsoleto
- ✅ **Optimization**: Limpieza de dependencias no utilizadas

### Versiones Anteriores
- Implementación de cuestionarios orales
- Sistema de gestión de carreras e instituciones V2
- Integración de resultados de aprendizaje por materia
- Sistema base de gestión de preguntas y exámenes

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 👨‍💻 Autor

**Martín Romero**
- GitHub: [@martinmromero](https://github.com/martinmromero)

## 🙏 Agradecimientos

- Django Framework por la base sólida
- Bootstrap por los componentes UI
- Comunidad open source por las librerías utilizadas

---

📧 **¿Necesitas ayuda?** Abre un [issue](https://github.com/martinmromero/EducaApp/issues) en GitHub

⭐ **¿Te gusta el proyecto?** ¡Dale una estrella en GitHub!