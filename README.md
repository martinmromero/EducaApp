# 🎓 EducaApp - Sistema de Gestión Educativa

[![Django](https://img.shields.io/badge/Django-4.2.20-092E20?style=flat&logo=django&logoColor=white)](https://djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.0-7952B3?style=flat&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)](https://sqlite.org/)

## 📖 Descripción

EducaApp es un sistema integral de gestión educativa desarrollado en Django que permite a instituciones educativas administrar materias, resultados de aprendizaje, preguntas de examen, y generar cuestionarios tanto escritos como orales de manera eficiente.

## ✨ Características Principales

### 🏫 Gestión Institucional
- **Instituciones V2**: Sistema completo de gestión de instituciones educativas
- **Campus y Facultades**: Organización jerárquica de la estructura institucional
- **Carreras**: Gestión de carreras académicas con asociaciones institucionales

### 📚 Gestión Académica
- **Materias**: CRUD completo de materias/asignaturas
- **Resultados de Aprendizaje**: Sistema integrado por materia con funcionalidades completas
- **Temas y Subtemas**: Organización temática del contenido educativo
- **Preguntas**: Banco de preguntas con filtros cascada (materia → tema → subtema)

### 📝 Sistema de Exámenes
- **Plantillas de Examen**: Creación y reutilización de plantillas personalizables
- **Exámenes Escritos**: Generación automática con selección de preguntas
- **Cuestionarios Orales**: Sistema avanzado de evaluación oral con algoritmos inteligentes
- **Vista Previa e Impresión**: Formatos optimizados para diferentes tipos de evaluación

### 🔧 Funcionalidades Técnicas
- **Carga Masiva**: Importación de preguntas via CSV/TXT
- **Procesamiento de Archivos**: Soporte para PDF, DOCX, PPTX
- **Interfaz Responsiva**: Design moderno con Bootstrap 5
- **Sidebar Colapsable**: Navegación optimizada
- **Filtros Dinámicos**: Sistema de filtros cascada con AJAX
- **Sistema de Mensajes**: Notificaciones contextuales por módulo

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
| PyPDF2 | 3.0.0 | Procesamiento de archivos PDF |
| python-docx | 0.8.11 | Procesamiento de archivos Word |
| python-pptx | 0.6.23 | Procesamiento de archivos PowerPoint |
| django-crispy-forms | 2.4 | Formularios mejorados |
| djangorestframework | 3.16.0 | APIs REST |
| django-debug-toolbar | 4.2.0 | Herramientas de desarrollo |
| crispy-bootstrap5 | - | Integración Bootstrap 5 |

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
2. **Banco de Preguntas**: Cargar y categorizar preguntas por temas
3. **Creación de Exámenes**: Generar exámenes personalizados usando plantillas
4. **Evaluaciones Orales**: Crear cuestionarios orales con distribución automática

### Para Instituciones
1. **Gestión Organizacional**: Administrar campus, facultades y carreras
2. **Estandarización**: Usar plantillas para mantener consistencia en evaluaciones
3. **Reportes**: Generar vistas previas e imprimir exámenes en formatos estándar

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
- Sistema de intercambio de preguntas
- Evaluación y seguimiento en tiempo real

### Carga Masiva de Contenido
- Importación CSV/TXT con validaciones
- Procesamiento de documentos (PDF, DOCX, PPTX)
- Sistema de preview antes de confirmar importación

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Changelog

### [Última Versión] - 2025-09-27
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