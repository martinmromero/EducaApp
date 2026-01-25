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

### 📝 Sistema de Exámenes
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
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate
```

### Instalar Dependencias
```bash
pip install -r requirements.txt
```

### Configurar Base de Datos
```bash
# Aplicar migraciones
python manage.py migrate

# Crear superusuario (opcional)
python manage.py createsuperuser
```

### Ejecutar el Servidor
```bash
python manage.py runserver
```

La aplicación estará disponible en `http://127.0.0.1:8000/`

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

### Procesamiento Avanzado de Documentos
- **Dashboard de Procesamiento**: Interface completa para análisis de documentos
- **Extracción de Metadata**: Obtención automática de ISBN, edición, páginas, editorial y año
- **Análisis de Tokens**: Contador de tokens compatible con modelos de IA
- **División Inteligente**: Segmentación de texto en chunks optimizados
- **Optimización de Texto**: Conversión y limpieza de contenido para procesamiento

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

### [Actual] - 2026-01-24
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